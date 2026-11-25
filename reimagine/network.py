"""Stage `network`: the folktale network as a modelling choice, and what the network is.

  sweep        edges by density (5%, 10%, 15%) and by k nearest neighbours (k = 5, 10, 20, symmetrised), for
               TF-IDF and embeddings: communities, modularity against degree-preserving shuffles, NMI between
               Louvain seeds, NMI and assortativity of tale type, region and source collection against label
               shuffles, the type and region tests again against shuffles *within* source collection, and NMI of
               each partition with the main one (10% density, seed 42)
  backbone     disparity filter (alpha 0.05 and 0.01) on the 10% graph and on the complete similarity graph.
               For drawing only, the communities always come from the full 10% graph
  structure    degree and strength distributions against random graphs, clustering against degree-preserving
               shuffles, and the PageRank-central ("archetypal") tales from Part A
  communities  one table: name (for the nine large TF-IDF communities), size, top words, LDA topic, dominant
               tale types, regions and source collections
  collection   coverage of the collection and translator labels, and the main map and a map built from texts
               with names and fixed phrases masked, both against both nulls
"""
from __future__ import annotations

import hashlib
import itertools
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from scipy.stats import skew, spearmanr

from .core.common import stable_hash
from .core.metrics import codes, label_agreement, nmi
from .core.networks import disparity_backbone, double_edge_swaps, louvain, modularity, select_edges, structure, to_graph

from .common import Ctx, permute_within, summarise_null, write_csv, write_json
from .corpus import load_corpus
from .part_a import degree_null, major_communities
from .reps import Masker, build_space

LABELS = (("atu_type", "atu_id"), ("region", "region"), ("source_collection", "source_collection"))


# ----------------------------------------------------------------- pure functions
def knn_edges(S: np.ndarray, k: int) -> dict:
    """Symmetrised k-nearest-neighbour graph: i-j is an edge if j is among the k most similar tales of i or i of j
    (ties: lower index first, only positive similarities). Same output keys as `select_edges`."""
    n = S.shape[0]
    M = np.round(S, 12).astype(float)
    np.fill_diagonal(M, -np.inf)
    nb = np.argsort(-M, axis=1, kind="stable")[:, :k]
    a = np.repeat(np.arange(n), k)
    b = nb.ravel()
    ok = S[a, b] > 0
    lo, hi = np.minimum(a[ok], b[ok]), np.maximum(a[ok], b[ok])
    pairs = np.unique(lo.astype(np.int64) * n + hi)
    i, j = (pairs // n).astype(np.int32), (pairs % n).astype(np.int32)
    w = S[i, j]
    return dict(i=i, j=j, w=w, m=len(w), n=n, threshold=float(w.min()) if len(w) else None,
                density_achieved=len(w) / (n * (n - 1) / 2))


def clustering(n: int, i: np.ndarray, j: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    """Local clustering per node (dense matrices). Unweighted, or Onnela's weighted version (geometric mean of the
    triangle's weights, normalised by the largest weight), as `networkx.clustering`. Nodes with degree < 2 get 0."""
    A = np.zeros((n, n))
    A[i, j] = A[j, i] = 1.0 if w is None else np.cbrt(w / w.max())
    k = np.bincount(np.concatenate([i, j]), minlength=n).astype(float)
    tri = np.einsum("ij,ji->i", A @ A, A)                            # (A^3)_ii
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(k > 1, tri / (k * (k - 1)), 0.0)


def gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum())) if x.sum() > 0 else 0.0


def stratified_perms(strata: np.ndarray, n_perm: int, seed: int) -> np.ndarray:
    """`n_perm` index permutations that move items only within their stratum (rows of a permutation matrix)."""
    rng = np.random.default_rng(seed)
    return np.stack([permute_within(strata, rng) for _ in range(n_perm)]).astype(np.int32)


def plain_perms(n: int, n_perm: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.stack([rng.permutation(n) for _ in range(n_perm)]).astype(np.int32)


def label_tests(part: np.ndarray, e: dict, folk: pd.DataFrame, nodes: np.ndarray, n_perm: int, seed: int,
                keep_null: bool = False) -> list[dict]:
    """NMI and assortativity of each label against plain label shuffles, and of type and region against shuffles
    within source collection, on the node subset `nodes` (and the edges among them)."""
    n = len(folk)
    remap = -np.ones(n, dtype=np.int64)
    remap[nodes] = np.arange(len(nodes))
    keep = (remap[e["i"]] >= 0) & (remap[e["j"]] >= 0)
    ei, ej = remap[e["i"][keep]], remap[e["j"][keep]]
    p, _ = codes(part[nodes].tolist())
    strata = folk["source_collection"].to_numpy(dtype=object)[nodes]
    nulls = {"label shuffle": plain_perms(len(nodes), n_perm, seed),
             "within-collection shuffle": stratified_perms(strata, n_perm, seed + 1)}
    out = []
    for label, col in LABELS:
        y, cats = codes(folk[col].to_numpy(dtype=object)[nodes].tolist())
        for null_name, perms in nulls.items():
            if label == "source_collection" and null_name != "label shuffle":
                continue                                     # shuffling collection within collection changes nothing
            r = label_agreement(p, y, ei, ej, perms, keep_null=keep_null)
            for measure in ("nmi", "assortativity"):
                v = r[measure]
                row = dict(label=label, null=null_name, measure=measure, n=len(nodes), edges=int(len(ei)), categories=len(cats),
                           observed=v["observed"], null_mean=v["null_mean"], null_sd=v["null_sd"], null_max=v["null_max"],
                           excess=v["excess"], z=v["z"], p_upper=v["p_upper"], shuffles=len(perms))
                if keep_null:
                    vals = np.array(r["null_values"][measure])
                    row.update(null_min=float(vals.min()), null_q025=float(np.quantile(vals, 0.025)), null_q975=float(np.quantile(vals, 0.975)))
                out.append(row)
    return out


def flatten(tests: list[dict]) -> dict:
    """One row per graph: `<label>_<measure>` (observed) and its null mean, z and p for each null."""
    out = {}
    for t in tests:
        base = f"{t['label']}_{t['measure']}"
        sfx = "" if t["null"] == "label shuffle" else "_within_collection"
        if not sfx:
            out[base] = t["observed"]
        out.update({f"{base}{sfx}_null_mean": t["null_mean"], f"{base}{sfx}_z": t["z"], f"{base}{sfx}_p": t["p_upper"]})
    return out


# ----------------------------------------------------------------- degree-preserving null for clustering
def _clust_one(args):
    """Shuffle k of the Part A null (same seed and stream: identical rewired graph and weights), then clustering."""
    edges, weights, n, swaps_per_edge, seed, k = args
    rng = np.random.default_rng([seed, k])
    m = len(edges)
    e = double_edge_swaps(edges, n, swaps_per_edge * m, rng, max_tries=max(swaps_per_edge * m * 50, 10_000))
    w = rng.permutation(weights)
    s = np.bincount(np.concatenate([e[:, 0], e[:, 1]]), weights=np.concatenate([w, w]), minlength=n)
    deg = np.bincount(e.ravel(), minlength=n)
    return (clustering(n, e[:, 0], e[:, 1]).mean(), clustering(n, e[:, 0], e[:, 1], w).mean(),
            float(spearmanr(deg, s)[0]), float(np.std(s / np.maximum(deg, 1)) / np.mean(s / np.maximum(deg, 1))))


def clustering_null(e: dict, shuffles: int, swaps_per_edge: int, seed: int, cache_dir) -> np.ndarray:
    edges = np.stack([e["i"], e["j"]], axis=1).astype(np.int64)
    sig = stable_hash(dict(edges=hashlib.sha256(edges.tobytes()).hexdigest(), w=hashlib.sha256(e["w"].tobytes()).hexdigest(),
                           n=e["n"], shuffles=shuffles, swaps=swaps_per_edge, seed=seed, method="clust-v1"), 16)
    path = cache_dir / f"clustering_null_{sig}.npy"
    if path.exists():
        return np.load(path)
    jobs = [(edges, e["w"], e["n"], swaps_per_edge, seed, k) for k in range(shuffles)]
    workers = int(os.environ.get("REIMAGINE_WORKERS", max(1, min(16, (os.cpu_count() or 2) - 2))))
    if workers == 1 or shuffles < 4 or len(edges) < 5000:
        out = [_clust_one(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            out = list(pool.map(_clust_one, jobs))
    arr = np.array(out)
    np.save(path, arr)
    return arr


# ----------------------------------------------------------------- backbones (drawing only)
def backbone_path(ctx: Ctx, rep: str, filtered: str, alpha: float):
    key = "complete" if filtered.startswith("complete") else "threshold"
    return ctx.work / f"backbone_{rep}_{key}_{alpha:g}.npz"


def backbones(ctx: Ctx, rep: str, S: np.ndarray, canon_e: dict, canon_labels: np.ndarray) -> list[dict]:
    """Disparity filter (week 4) at every alpha of analysis.yaml, on the thresholded 10% graph and on the complete
    similarity graph. Each kept edge set is saved for drawing. Communities never come from a backbone."""
    nc = ctx.analysis["network"]
    n = S.shape[0]
    iu, ju = np.triu_indices(n, 1)
    wu = S[iu, ju]
    pos = wu > 0
    full = dict(i=iu[pos].astype(np.int32), j=ju[pos].astype(np.int32), w=wu[pos])
    rows = []
    for base_name, base in (("10% graph", canon_e), ("complete similarity graph", full)):
        for alpha in nc["backbone_alphas"]:
            keep = disparity_backbone(n, base["i"], base["j"], base["w"], alpha)
            nodes = np.unique(np.concatenate([base["i"][keep], base["j"][keep]]))
            same = float((canon_labels[base["i"][keep]] == canon_labels[base["j"][keep]]).mean()) if keep.any() else np.nan
            rows.append(dict(rep=rep, filtered=base_name, alpha=alpha, edges_in=int(len(base["w"])), edges_kept=int(keep.sum()),
                             nodes_with_an_edge=int(len(nodes)), nodes=n, share_of_kept_edges_within_a_community=same,
                             drawn=bool(base_name == nc["backbone_drawn_from"] and alpha == nc["backbone_drawn_alpha"])))
            np.savez_compressed(backbone_path(ctx, rep, base_name, alpha), i=base["i"][keep], j=base["j"][keep], w=base["w"][keep])
    return rows


# ----------------------------------------------------------------- the stage
def graph_specs(ctx: Ctx) -> list[tuple[str, float | int]]:
    nc = ctx.analysis["network"]
    return [("density", d) for d in ctx.cfg["graphs"]["densities"]] + [("knn", k) for k in nc["knn"]]


def build_edges(S: np.ndarray, kind: str, value) -> dict:
    return select_edges(S, value) if kind == "density" else knn_edges(S, int(value))


def run(ctx: Ctx) -> dict:
    nc, g, mp = ctx.analysis["network"], ctx.cfg["graphs"], ctx.analysis["map"]
    corpus = load_corpus(ctx)
    folk = corpus.folk
    n = len(folk)
    seeds, prim_seed, res = g["seeds"], g["primary_seed"], g["louvain_resolution"]
    n_perm = ctx.shuffles(mp["label_shuffles"])
    nseed = mp["label_shuffle_seed"]
    labelled = np.flatnonzero((folk["atu_id"].notna() & folk["region"].notna() & folk["source_collection"].notna()).to_numpy())

    # ---- metadata coverage (step 6.1)
    meta = dict(folktales=n, with_source_collection=int(folk["source_collection"].notna().sum()),
                missing_source_collection=int(folk["source_collection"].isna().sum()),
                source_collections=int(folk["source_collection"].nunique()),
                collections_with_5_or_more_tales=int((folk["source_collection"].value_counts() >= 5).sum()),
                tales_in_collections_with_5_or_more=int(folk["source_collection"].value_counts().loc[lambda s: s >= 5].sum()),
                single_tale_collections=int((folk["source_collection"].value_counts() == 1).sum()),
                with_translator=int(folk["translator"].notna().sum()), missing_translator=int(folk["translator"].isna().sum()),
                translators=int(folk["translator"].nunique()),
                with_type_region_and_collection=int(len(labelled)),
                largest_collections=folk["source_collection"].value_counts().head(10).to_dict())
    write_json(ctx.results / "collection_metadata.json", meta)
    print(f"    source collection known for {meta['with_source_collection']} of {n} tales ({meta['source_collections']} collections); "
          f"translator stated for {meta['with_translator']}; {len(labelled)} tales carry type, region and collection")

    canon = {}
    for rep in ctx.reps:
        z = np.load(ctx.work / f"map_{rep}.npz", allow_pickle=False)
        assert z["ids"].tolist() == folk["id"].tolist(), "run partA first"
        canon[rep] = z
    primary_labels = canon[ctx.primary]["labels"]

    rob_rows, conf_rows, back_rows, struct_rows, comm_rows = [], [], [], [], []
    for rep in ctx.reps:
        space = build_space(rep, folk["text"].tolist(), ctx.cfg)
        S = space.folk_sim()
        canon_labels = canon[rep]["labels"]
        partitions = {}
        for kind, value in graph_specs(ctx):
            e = build_edges(S, kind, value)
            G = to_graph(n, e["i"], e["j"], e["w"])
            parts = {s: louvain(G, s, res) for s in seeds}
            is_canon = kind == "density" and value == g["primary_density"]
            if kind == "density":                                       # same settings as Part A: the cache is reused
                nshuf = ctx.shuffles(mp["modularity_null"]["shuffles" if is_canon else "shuffles_other_densities"], cap=10)
            else:
                nshuf = ctx.shuffles(nc["knn_modularity_shuffles"], cap=10)
            q_obs = modularity(G, parts[prim_seed])
            q_null, _ = degree_null(G, nshuf, mp["modularity_null"]["swaps_per_edge"], mp["modularity_null"]["seed"], prim_seed, res,
                                    want_pagerank=is_canon, cache_dir=ctx.work)
            qs = summarise_null(q_obs, q_null)
            part = parts[prim_seed]
            st = structure(G)
            tests = label_tests(part, e, folk, labelled, n_perm, nseed, keep_null=is_canon)
            row = dict(rep=rep, edges_by=kind, value=value, canonical=is_canon, n=n, m=e["m"], similarity_threshold=e["threshold"],
                       mean_degree=2 * e["m"] / n, isolates=len(st["isolates"]), components=st["components"],
                       communities=int(part.max() + 1), communities_major=int(len(major_communities(part))),
                       modularity=q_obs, modularity_null_mean=qs["null_mean"], modularity_null_sd=qs["null_sd"], modularity_z=qs["z"],
                       modularity_shuffles=nshuf,
                       seed_nmi_min=min(nmi(parts[a], parts[b]) for a, b in itertools.combinations(seeds, 2)),
                       seed_nmi_max=max(nmi(parts[a], parts[b]) for a, b in itertools.combinations(seeds, 2)),
                       nmi_with_canonical=nmi(*(codes(x.tolist())[0] for x in (part, canon_labels))),
                       nmi_with_primary_canonical=nmi(*(codes(x.tolist())[0] for x in (part, primary_labels))),
                       label_nodes=len(labelled), label_shuffles=n_perm, **flatten(tests))
            rob_rows.append(row)
            partitions[f"{kind}_{value:g}"] = part
            if is_canon:
                conf_rows += [dict(rep=rep, map="canonical (10% density, seed 42)", **t) for t in tests]
                canon_e = e
            print(f"    {rep} {kind}={value}: m={e['m']:,}, {row['communities_major']} major communities, Q={q_obs:.3f} (z={qs['z']:.0f}), "
                  f"NMI type {row['atu_type_nmi']:.3f} / region {row['region_nmi']:.3f} / collection {row['source_collection_nmi']:.3f}; "
                  f"NMI with canonical {row['nmi_with_canonical']:.2f}", flush=True)

        np.savez_compressed(ctx.work / f"partitions_{rep}.npz", ids=folk["id"].to_numpy(dtype=str), **partitions)

        # ---- backbone (drawing only): disparity filter on the 10% graph and on the complete similarity graph
        back_rows += backbones(ctx, rep, S, canon_e, canon_labels)
        iu, ju = np.triu_indices(n, 1)

        # ---- structure of the canonical graph against random graphs
        e = canon_e
        deg = np.bincount(np.concatenate([e["i"], e["j"]]), minlength=n)
        strength = np.bincount(np.concatenate([e["i"], e["j"]]), weights=np.concatenate([e["w"], e["w"]]), minlength=n)
        rng = np.random.default_rng(nc["structure_seed"])
        n_pairs = n * (n - 1) // 2
        er = []
        for _ in range(ctx.shuffles(nc["random_graphs"], cap=10)):
            pick = rng.choice(n_pairs, size=e["m"], replace=False)          # G(n, m): m distinct pairs at random
            d = np.bincount(np.concatenate([iu[pick], ju[pick]]), minlength=n)
            er.append((d.std() / d.mean(), d.max(), gini(d), skew(d)))
        er = np.array(er)
        cl_null = clustering_null(e, ctx.shuffles(nc["clustering_shuffles"], cap=10), mp["modularity_null"]["swaps_per_edge"],
                                  mp["modularity_null"]["seed"], ctx.work)
        c_obs, cw_obs = clustering(n, e["i"], e["j"]).mean(), clustering(n, e["i"], e["j"], e["w"]).mean()
        per_w = strength / np.maximum(deg, 1)
        for measure, obs, null, null_name in (
                ("degree: coefficient of variation", deg.std() / deg.mean(), er[:, 0], "random graph G(n, m)"),
                ("degree: largest", float(deg.max()), er[:, 1], "random graph G(n, m)"),
                ("degree: Gini", gini(deg), er[:, 2], "random graph G(n, m)"),
                ("degree: skewness", float(skew(deg)), er[:, 3], "random graph G(n, m)"),
                ("clustering (unweighted, mean over tales)", c_obs, cl_null[:, 0], "degree-preserving shuffles"),
                ("clustering (weighted, Onnela)", cw_obs, cl_null[:, 1], "degree-preserving shuffles, weights reassigned"),
                ("strength against degree (Spearman)", float(spearmanr(deg, strength)[0]), cl_null[:, 2], "degree-preserving shuffles, weights reassigned"),
                ("mean edge weight per tale: coefficient of variation", float(per_w.std() / per_w.mean()), cl_null[:, 3],
                 "degree-preserving shuffles, weights reassigned")):
            s = summarise_null(obs, null)
            struct_rows.append(dict(rep=rep, measure=measure, observed=obs, null=null_name, null_mean=s["null_mean"], null_sd=s["null_sd"],
                                    null_max=float(np.max(null)), z=s["z"], shuffles=len(null)))
        struct_rows.append(dict(rep=rep, measure="clustering expected in G(n, m) (= density)", observed=e["m"] / n_pairs, null="", null_mean=np.nan,
                                null_sd=np.nan, null_max=np.nan, z=np.nan, shuffles=0))
        struct_rows.append(dict(rep=rep, measure="degree: mean", observed=float(deg.mean()), null="", null_mean=np.nan, null_sd=np.nan,
                                null_max=np.nan, z=np.nan, shuffles=0))
        np.save(ctx.work / f"degrees_{rep}.npy", np.stack([deg, strength]))

        # ---- the community table
        comm = pd.read_csv(ctx.results / "partA_communities.csv")
        comm = comm[comm["rep"] == rep].set_index("community")
        member = pd.read_csv(ctx.results / "partA_membership.csv").set_index("id").loc[folk["id"]]
        topics = pd.read_csv(ctx.results / "partA_lda_topics.csv")
        topics = topics[topics["rep"] == rep].set_index("topic")
        cc = member[f"community_{rep}"].to_numpy()
        names = folk.dropna(subset=["atu_id"]).drop_duplicates("atu_id").set_index("atu_id")["atu_name"].to_dict()
        # the names of the nine large communities of the main network, each checked against its first top word
        given = ctx.analysis.get("community_names", {}) if rep == ctx.primary else {}
        assert set(given) <= set(comm.index), f"community_names lists communities the {rep} map does not have"
        for c in comm.index:
            m = cc == c
            f = folk[m]
            t = pd.Series(member[f"lda_topic_{rep}"].to_numpy()[m]).value_counts()
            coll = f["source_collection"].value_counts()
            first = str(comm.at[c, "top_words"]).split()[0]
            if c in given:
                assert given[c]["first_word"] == first, (
                    f"{c} of the {rep} map now starts with '{first}', not '{given[c]['first_word']}'. The partition changed, "
                    "so check community_names in analysis.yaml")
            comm_rows.append(dict(rep=rep, community=c, name=given[c]["name"] if c in given else "", size=int(m.sum()), share=float(m.mean()),
                                  top_words=", ".join(str(comm.at[c, "top_words"]).split()[:8]),
                                  lda_topic=int(t.index[0]), lda_topic_share=float(t.iloc[0] / m.sum()),
                                  lda_topic_words=", ".join(str(topics.at[t.index[0], "top_words"]).split()[:6]),
                                  dominant_atu_types="; ".join(f"{a} {names.get(a, '')} ({k})" for a, k in f["atu_id"].value_counts().head(3).items()),
                                  atu_types=int(f["atu_id"].nunique()),
                                  dominant_regions="; ".join(f"{r} ({k})" for r, k in f["region"].value_counts().head(3).items()),
                                  dominant_source_collections="; ".join(f"{s} ({k})" for s, k in coll.head(3).items()),
                                  top_collection_share=float(coll.iloc[0] / f["source_collection"].notna().sum()) if len(coll) else np.nan,
                                  source_collections=int(f["source_collection"].nunique())))

    # ---- step 6.4: a map built from texts with names and collection/translator formulae masked
    queries = corpus.queries(ctx)
    masker = Masker(folk["text"].tolist() + queries["text"].tolist(), ctx.analysis["masking"])
    masked = [masker.mask(t) for t in folk["text"]]
    for rep in ctx.reps:
        S = build_space(rep, masked, ctx.cfg).folk_sim()
        e = select_edges(S, g["primary_density"])
        G = to_graph(n, e["i"], e["j"], e["w"])
        part = louvain(G, prim_seed, res)
        tests = label_tests(part, e, folk, labelled, n_perm, nseed)
        conf_rows += [dict(rep=rep, map="names and collection/translator formulae masked (10% density, seed 42)", **t) for t in tests]
        rob_rows.append(dict(rep=rep, edges_by="density, masked texts", value=g["primary_density"], canonical=False, n=n, m=e["m"],
                             similarity_threshold=e["threshold"], mean_degree=2 * e["m"] / n,
                             communities=int(part.max() + 1), communities_major=int(len(major_communities(part))),
                             modularity=modularity(G, part),
                             nmi_with_canonical=nmi(*(codes(x.tolist())[0] for x in (part, canon[rep]["labels"]))),
                             nmi_with_primary_canonical=nmi(*(codes(x.tolist())[0] for x in (part, primary_labels))),
                             label_nodes=len(labelled), label_shuffles=n_perm, **flatten(tests)))
        print(f"    {rep} masked map: NMI with the unmasked map {rob_rows[-1]['nmi_with_canonical']:.2f}; NMI type "
              f"{rob_rows[-1]['atu_type_nmi']:.3f} (within-collection null {rob_rows[-1]['atu_type_nmi_within_collection_null_mean']:.3f})")

    # ---- archetypal tales: PageRank against the degree-preserving shuffles (Part A)
    pr = pd.read_csv(ctx.results / "partA_pagerank_top10.csv")
    meta_cols = folk.set_index("id")[["atu_name", "region", "source_collection", "n_tokens"]]
    arche = pr.join(meta_cols, on="id")

    write_csv(pd.DataFrame(rob_rows), ctx.results / "network_robustness.csv")
    write_csv(pd.DataFrame(conf_rows), ctx.results / "collection_confound.csv")
    write_csv(pd.DataFrame(back_rows), ctx.results / "network_backbone.csv")
    write_csv(pd.DataFrame(struct_rows), ctx.results / "network_structure.csv")
    write_csv(pd.DataFrame(comm_rows), ctx.results / "community_table.csv")
    write_csv(arche, ctx.results / "network_archetypes.csv")
    return dict(graphs=len(rob_rows))
