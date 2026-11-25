"""Stage `partA`: the folktale network, built from the folktales alone.

For each text representation:
  1. cosine graph at fixed density (5%, 10% main, 15%), with a fixed tie rule
  2. Louvain for three seeds, modularity against degree-preserving shuffles, NMI between seeds
  3. what the communities are: top words per community, LDA topics against communities
  4. PageRank against the same degree-preserving shuffles
  5. a backbone and a layout, for drawing only
The main partition (10% density, seed 42) is the one the parables are placed on. What the communities follow
(tale type, region or source book) is tested in the network stage.
"""
from __future__ import annotations

import hashlib
import itertools
import os
import warnings
from concurrent.futures import ProcessPoolExecutor

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer

from .core.lexical import name_like_words, preprocess, stopwords
from .core.metrics import codes, nmi, permutation_matrix
from .core.networks import (disparity_backbone, double_edge_swaps, louvain, modularity, select_edges,
                               strongest_per_node, structure, to_graph)

from .core.common import stable_hash

from .common import Ctx, summarise_null, write_csv, write_json
from .corpus import load_corpus
from .reps import build_space

MIN_COMMUNITY_SHARE = 0.01      # communities below 1% of the tales (isolates, pairs) are reported together as "small"


# ----------------------------------------------------------------- degree-preserving null
def pagerank_vector(G: nx.Graph) -> np.ndarray:
    pr = nx.pagerank(G, alpha=0.85, weight="weight")
    return np.array([pr[k] for k in range(G.number_of_nodes())])


def _null_one(args):
    """One degree-preserving shuffle (week 2 edge swaps, weights reassigned at random), then Louvain and PageRank."""
    edges, weights, n, swaps_per_edge, seed, k, louvain_seed, resolution, want_pagerank = args
    rng = np.random.default_rng([seed, k])          # one independent stream per shuffle: order and workers do not matter
    m = len(edges)
    e = double_edge_swaps(edges, n, swaps_per_edge * m, rng, max_tries=max(swaps_per_edge * m * 50, 10_000))
    assert (np.bincount(e.ravel(), minlength=n) == np.bincount(edges.ravel(), minlength=n)).all(), "degrees changed"
    H = to_graph(n, e[:, 0], e[:, 1], rng.permutation(weights))
    q = modularity(H, louvain(H, louvain_seed, resolution))
    return q, (pagerank_vector(H) if want_pagerank else None)


def degree_null(G: nx.Graph, shuffles: int, swaps_per_edge: int, seed: int, louvain_seed: int, resolution: float,
                want_pagerank: bool = False, workers: int | None = None, cache_dir=None):
    """Modularity (and PageRank) of `shuffles` degree-preserving rewirings of G.

    With `cache_dir`, a result is reused only for exactly this graph and these settings.
    """
    n = G.number_of_nodes()
    edges = np.array(list(G.edges()), dtype=np.int64).reshape(-1, 2)
    weights = np.array([G[u][v]["weight"] for u, v in edges])
    path = None
    if cache_dir is not None:
        sig = stable_hash(dict(edges=hashlib.sha256(edges.tobytes()).hexdigest(), weights=hashlib.sha256(weights.tobytes()).hexdigest(),
                               n=n, shuffles=shuffles, swaps=swaps_per_edge, seed=seed, louvain_seed=louvain_seed,
                               resolution=resolution, pagerank=want_pagerank, method="swap-v2"), 16)
        path = cache_dir / f"degree_null_{sig}.npz"
        if path.exists():
            with np.load(path) as z:
                return z["q"], (z["pr"] if want_pagerank else None)
    jobs = [(edges, weights, n, swaps_per_edge, seed, k, louvain_seed, resolution, want_pagerank) for k in range(shuffles)]
    workers = workers or int(os.environ.get("REIMAGINE_WORKERS", max(1, min(16, (os.cpu_count() or 2) - 2))))
    if workers == 1 or shuffles < 4 or len(edges) < 5000:
        out = [_null_one(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            out = list(pool.map(_null_one, jobs))
    q = np.array([o[0] for o in out])
    pr = np.stack([o[1] for o in out]) if want_pagerank else None
    if path is not None:
        np.savez_compressed(path, q=q, **({"pr": pr} if want_pagerank else {}))
    return q, pr


# ----------------------------------------------------------------- words and topics
def count_matrix(texts: list[str], lcfg: dict, extra_stop=(), min_df: int = 2, max_features: int | None = None):
    """Term counts with the pipeline's own preprocessing, token pattern and stopword list (negations kept)."""
    cv = CountVectorizer(lowercase=False, token_pattern=lcfg["token_pattern"], min_df=min_df, max_features=max_features,
                         stop_words=sorted(set(stopwords(lcfg)) | set(extra_stop)))
    X = cv.fit_transform([preprocess(t, lcfg) for t in texts])
    return X.tocsr(), cv.get_feature_names_out()


FRAGMENTS = {"ll", "ve", "re"}       # left over from 'll, 've, 're after tokenising


def community_words(X, vocab: np.ndarray, labels: np.ndarray, top: int) -> dict[int, list[str]]:
    """Course week 6 definition: each group is one document. TF = share of the group's tokens,
    IDF = log(K / number of groups that contain the word). Words found in every group score 0."""
    groups = np.unique(labels)
    C = np.vstack([np.asarray(X[labels == g].sum(axis=0)).ravel() for g in groups]).astype(float)
    tf = C / np.maximum(C.sum(axis=1, keepdims=True), 1)
    score = tf * np.log(len(groups) / np.maximum((C > 0).sum(axis=0), 1))
    return {int(g): [str(vocab[t]) for t in np.argsort(-score[r], kind="stable")[:top] if score[r, t] > 0]
            for r, g in enumerate(groups)}


def tfidf_lift_words(F, vocab: np.ndarray, labels: np.ndarray, top: int, exclude: set[str]) -> dict[int, list[str]]:
    """Words with the highest mean TF-IDF weight in a group, relative to the mean over all tales.

    Uses the same tale-level TF-IDF matrix as the network. It stays informative when there are only a
    handful of large groups, where almost every word occurs in every group and the IDF over groups is 0.
    """
    overall = np.asarray(F.mean(axis=0)).ravel()
    ok = np.array([w not in exclude for w in vocab])
    out = {}
    for g in np.unique(labels):
        lift = np.where(ok, np.asarray(F[labels == g].mean(axis=0)).ravel() - overall, -np.inf)
        out[int(g)] = [str(vocab[t]) for t in np.argsort(-lift, kind="stable")[:top] if lift[t] > 0]
    return out


def nmi_null(a: np.ndarray, b: np.ndarray, perms: np.ndarray) -> dict:
    a, _ = codes(a.tolist())
    b, _ = codes(b.tolist())
    return summarise_null(nmi(a, b), np.array([nmi(a, b[p]) for p in perms]))


def map_layout(e: dict, seed: int, iterations: int, cache_dir=None) -> np.ndarray:
    """Positions for drawing: ForceAtlas2 on the whole analysis graph (linear attraction), unit square.

    The layout of a thin backbone does not show the communities of these dense similarity graphs.
    The whole graph does. Positions are never used for any statistic.
    """
    path = None
    if cache_dir is not None:
        sig = stable_hash(dict(i=hashlib.sha256(e["i"].tobytes()).hexdigest(), j=hashlib.sha256(e["j"].tobytes()).hexdigest(),
                               w=hashlib.sha256(e["w"].tobytes()).hexdigest(), seed=seed, iterations=iterations, method="fa2-linear-v1"), 16)
        path = cache_dir / f"layout_{sig}.npy"
        if path.exists():
            return np.load(path)
    G = to_graph(e["n"], e["i"], e["j"], e["w"])
    with warnings.catch_warnings():         # ForceAtlas2 divides by zero for coincident points. Harmless
        warnings.simplefilter("ignore", RuntimeWarning)
        pos = nx.forceatlas2_layout(G, max_iter=iterations, scaling_ratio=2.0, gravity=1.0, linlog=False, weight="weight",
                                    seed=seed, strong_gravity=False)
    xy = np.array([pos[k] for k in range(e["n"])], dtype=float)
    xy -= xy.min(axis=0)
    span = xy.max(axis=0)
    span[span == 0] = 1
    xy = xy / span.max()
    if path is not None:
        np.save(path, xy)
    return xy


# ----------------------------------------------------------------- one representation
def major_communities(labels: np.ndarray) -> np.ndarray:
    """IDs of communities holding at least 1% of the tales (IDs are ordered by size)."""
    sizes = np.bincount(labels)
    return np.flatnonzero(sizes >= max(2, MIN_COMMUNITY_SHARE * len(labels)))


def map_one(ctx: Ctx, rep: str, folk: pd.DataFrame, names: set[str], X_counts, vocab, tfidf) -> dict:
    g, mp = ctx.cfg["graphs"], ctx.analysis["map"]
    n = len(folk)
    S = (tfidf if rep == "tfidf" else build_space(rep, folk["text"].tolist(), ctx.cfg)).folk_sim()
    seeds, prim_seed, res = g["seeds"], g["primary_seed"], g["louvain_resolution"]

    graph_rows, canon = [], None
    for d in g["densities"]:
        e = select_edges(S, d)
        G = to_graph(n, e["i"], e["j"], e["w"])
        st = structure(G)
        parts = {s: louvain(G, s, res) for s in seeds}
        primary = d == g["primary_density"]
        nshuf = ctx.shuffles(mp["modularity_null"]["shuffles" if primary else "shuffles_other_densities"], cap=10)
        q_obs = modularity(G, parts[prim_seed])
        q_null, pr_null = degree_null(G, nshuf, mp["modularity_null"]["swaps_per_edge"], mp["modularity_null"]["seed"],
                                      prim_seed, res, want_pagerank=primary, cache_dir=ctx.work)
        qs = summarise_null(q_obs, q_null)
        seed_nmi = [nmi(parts[a], parts[b]) for a, b in itertools.combinations(seeds, 2)]
        graph_rows.append(dict(
            rep=rep, density=d, primary=primary, n=n, m=e["m"], similarity_threshold=e["threshold"],
            components=st["components"], largest_component=st["largest_component"], isolates=len(st["isolates"]),
            communities=int(parts[prim_seed].max() + 1), communities_major=int(len(major_communities(parts[prim_seed]))),
            modularity=q_obs, null_mean=qs["null_mean"], null_sd=qs["null_sd"], null_max=float(q_null.max()),
            z=qs["z"], shuffles=nshuf, seed_nmi_min=min(seed_nmi), seed_nmi_max=max(seed_nmi),
            modularity_other_seeds="; ".join(f"{s}: {modularity(G, parts[s]):.4f}" for s in seeds if s != prim_seed)))
        print(f"    {rep} d={d:.2f}: m={e['m']}, isolates={len(st['isolates'])}, Q={q_obs:.3f} vs null "
              f"{qs['null_mean']:.3f}±{qs['null_sd']:.4f} ({nshuf} shuffles), seed NMI {min(seed_nmi):.2f}-{max(seed_nmi):.2f}")
        if primary:
            canon = dict(e=e, G=G, labels=parts[prim_seed], pr_null=pr_null, parts=parts)

    e, G, labels = canon["e"], canon["G"], canon["labels"]
    major = major_communities(labels)
    group = np.where(np.isin(labels, major), labels, -1)            # -1 = small communities, reported together

    # ---- what the communities are
    words = tfidf_lift_words(tfidf.F, tfidf.vocab, group, mp["top_words"], names | FRAGMENTS)
    words_course = community_words(X_counts, vocab, group, mp["top_words"])
    comm_rows = []
    for c in list(major) + [-1]:
        members = folk[group == c]
        if not len(members):
            continue
        atu = members["atu_id"].value_counts()
        reg = members["region"].value_counts()
        comm_rows.append(dict(
            rep=rep, community=f"C{c + 1}" if c >= 0 else "small", size=len(members), share=len(members) / n,
            top_words=" ".join(words.get(int(c), [])), top_words_course_tfidf=" ".join(words_course.get(int(c), [])),
            tale_types=int(members["atu_id"].nunique()),
            top_tale_types="; ".join(f"{a} {members.loc[members.atu_id == a, 'atu_name'].iloc[0]} ({k})" for a, k in atu.head(3).items()),
            top_regions="; ".join(f"{r} ({k})" for r, k in reg.head(3).items()),
            median_tokens=float(members["n_tokens"].median())))

    # ---- LDA topics against communities (major communities only, k = their number)
    in_major = group >= 0
    k = max(2, len(major))
    Xl, vl = count_matrix(folk["text"].tolist(), ctx.cfg["lexical"], extra_stop=names | FRAGMENTS, min_df=min(5, max(1, n // 50)),
                          max_features=mp["lda"]["max_features"])
    lda = LatentDirichletAllocation(n_components=k, max_iter=mp["lda"]["max_iter"], learning_method="batch",
                                    random_state=mp["lda"]["seed"])
    topic = lda.fit_transform(Xl).argmax(axis=1)
    perms = permutation_matrix(int(in_major.sum()), ctx.shuffles(mp["label_shuffles"]), mp["label_shuffle_seed"])
    lda_nmi = nmi_null(group[in_major], topic[in_major], perms)
    topic_rows = [dict(rep=rep, topic=t, tales=int((topic == t).sum()),
                       top_words=" ".join(vl[np.argsort(-lda.components_[t])[:mp["top_words"]]])) for t in range(k)]

    # ---- PageRank against the degree-preserving shuffles
    deg_all = np.bincount(np.concatenate([e["i"], e["j"]]), minlength=n)
    pr = pagerank_vector(G)
    pr_mean, pr_sd = canon["pr_null"].mean(axis=0), canon["pr_null"].std(axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        pr_z = np.where(pr_sd > 0, (pr - pr_mean) / pr_sd, np.nan)
    # Listed: tales in the largest component with at least the median degree. A tale with a handful of edges, or in
    # a component of two, has almost no spread under the shuffles, so its z-score is huge and says nothing.
    giant = np.zeros(n, dtype=bool)
    giant[list(max(nx.connected_components(G), key=len))] = True
    eligible = giant & (deg_all >= np.median(deg_all))
    order = np.argsort(-np.where(eligible, np.nan_to_num(pr_z, nan=-np.inf), -np.inf))[:mp["pagerank_top"]]
    pr_rank = (-pr).argsort().argsort() + 1
    pr_rows = [dict(rep=rep, rank=r + 1, id=folk.at[i, "id"], title=folk.at[i, "title"], atu_id=folk.at[i, "atu_id"],
                    community=f"C{labels[i] + 1}" if group[i] >= 0 else "small", degree=int(deg_all[i]),
                    pagerank=pr[i], pagerank_rank=int(pr_rank[i]), null_mean=pr_mean[i], null_sd=pr_sd[i], z=pr_z[i])
               for r, i in enumerate(order) if eligible[i]]

    # ---- backbone and layout (drawing only)
    b = mp["backbone"]
    disp = disparity_backbone(n, e["i"], e["j"], e["w"], b["alpha"])
    use_disparity = disp.sum() >= b["min_mean_degree"] * n / 2
    bb = disp if use_disparity else strongest_per_node(n, e["i"], e["j"], e["w"], b["fallback_k"])
    xy = map_layout(e, mp["layout_seed"], mp["layout_iterations"], ctx.work)
    np.savez_compressed(ctx.work / f"map_{rep}.npz", ids=folk["id"].to_numpy(dtype=str), i=e["i"], j=e["j"], w=e["w"],
                        labels=labels, group=group, backbone=bb, xy=xy, pagerank=pr, pagerank_z=pr_z, lda_topic=topic,
                        **{f"seed{s}": p for s, p in canon["parts"].items()})

    summary = dict(rep=rep, n=n, communities=int(labels.max() + 1), communities_major=int(len(major)),
                   tales_in_major=int(in_major.sum()), tales_in_small=int((~in_major).sum()),
                   lda=dict(k=k, nmi=lda_nmi, tales=int(in_major.sum())),
                   backbone=dict(method=f"disparity filter, alpha {b['alpha']}" if use_disparity
                                 else f"each tale's {b['fallback_k']} strongest edges",
                                 disparity_edges_at_alpha=int(disp.sum()), alpha=b["alpha"], edges_drawn=int(bb.sum())))
    return dict(graphs=graph_rows, communities=comm_rows, topics=topic_rows, pagerank=pr_rows,
                summary=summary, labels=labels, group=group, topic=topic)


def run(ctx: Ctx) -> dict:
    folk = load_corpus(ctx).folk
    lcfg = ctx.cfg["lexical"]
    names = name_like_words(folk["text"].tolist(), lcfg["name_masking_sensitivity"]["threshold"])
    X_counts, vocab = count_matrix(folk["text"].tolist(), lcfg, extra_stop=names | FRAGMENTS, min_df=min(5, max(1, len(folk) // 50)))
    tfidf = build_space("tfidf", folk["text"].tolist(), ctx.cfg)
    out = {rep: map_one(ctx, rep, folk, names, X_counts, vocab, tfidf) for rep in ctx.reps}

    for name in ("graphs", "communities", "topics", "pagerank"):
        file = {"graphs": "partA_graphs.csv", "communities": "partA_communities.csv", "topics": "partA_lda_topics.csv",
                "pagerank": "partA_pagerank_top10.csv"}[name]
        write_csv(pd.DataFrame([r for rep in ctx.reps for r in out[rep][name]]), ctx.results / file)
    member = folk[["id", "title", "atu_id", "region", "n_tokens"]].copy()
    for rep in ctx.reps:
        member[f"community_{rep}"] = [f"C{c + 1}" if c >= 0 else "small" for c in out[rep]["group"]]
        member[f"lda_topic_{rep}"] = out[rep]["topic"]
    write_csv(member, ctx.results / "partA_membership.csv")
    if len(ctx.reps) > 1:       # do the two maps agree?
        a, b = (out[r]["labels"] for r in ctx.reps[:2])
        cross = dict(reps=ctx.reps[:2], nmi_between_partitions=nmi(*(codes(x.tolist())[0] for x in (a, b))))
    else:
        cross = {}
    summary = dict(per_representation={rep: out[rep]["summary"] for rep in ctx.reps}, between_representations=cross,
                   name_like_words_excluded_from_word_lists=len(names))
    write_json(ctx.results / "partA_summary.json", summary)
    return summary
