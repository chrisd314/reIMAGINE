"""Stage `site`: the website's data, built from the pipeline's results and cached arrays.

    python -m reimagine.run --stage site      (or python -m reimagine.site)

Writes three files to data/site/ (committed), so that each page loads only what it needs:
  story.json    every result the pages show, for both representations, and every parable, baseline passage
                and held-out retelling with its nearest folktales
  network.json  the folktale networks of both representations: layout, communities, degrees at each threshold,
                the three Louvain seeds, the partitions of every edge construction, PageRank and its shuffles,
                and the tales and partition of the label tests (for shuffles in the browser)
  near.json     the ten nearest folktales of every folktale, the words behind each match, and the openings
Only titles, labels, words and openings of at most 40 words are included, never full texts; every tale links to
the page of D. L. Ashliman's Folktexts it was taken from. Then the site is built with `npm run build` when Node
is available (`web/scripts/copy-data.mjs` copies data/site/ into the build). No number on the site is typed by hand.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import date
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from .common import PARABLES_CSV, ROOT, TRADITIONS, Ctx, read_json
from .core.metrics import codes, nmi
from .core.networks import select_edges
from .corpus import load_corpus
from .folktexts import type_pages
from .reps import build_space
from .vocab import drivers

SITE = ROOT / "data" / "site"
WEB = ROOT / "web"
OPENING_WORDS = 40
NEAR_K = 10                 # nearest folktales listed per tale or text
WORDS_FOR = 5               # ... of which the first five get the words behind the match
TYPE_OPTIONS = 3            # answer options per round of the tale-type game
ARCHETYPE_NULLS = 10        # central tales whose PageRank shuffles are shipped


def r(x, d=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


def rl(xs, d=4) -> list:
    return [r(x, d) for x in xs]


def opening(text: str, n: int = OPENING_WORDS) -> str:
    w = str(text).split()
    return " ".join(w[:n]) + (" …" if len(w) > n else "")


def records(df: pd.DataFrame, cols: dict[str, str]) -> list[dict]:
    """JSON-safe rows with renamed keys: floats rounded, NaN -> None, numpy scalars -> Python."""
    out = []
    for row in df[list(cols)].to_dict("records"):
        clean = {}
        for k, v in row.items():
            if isinstance(v, (bool, np.bool_)):
                v = bool(v)
            elif isinstance(v, (int, np.integer)):
                v = int(v)
            elif isinstance(v, (float, np.floating)):
                v = None if np.isnan(v) else round(float(v), 5)
            clean[cols[k]] = v
        out.append(clean)
    return out


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


# ================================================================= network.json
def community_rows(R, rep: str) -> list[dict]:
    ct = pd.read_csv(R / "community_table.csv")
    ct = ct[ct["rep"] == rep]
    words = pd.read_csv(R / "partA_communities.csv")
    words = words[words["rep"] == rep].set_index("community")["top_words_course_tfidf"]
    ct = ct.assign(course_words=ct["community"].map(words).fillna(""))
    return records(ct, {"community": "name", "size": "size", "share": "share", "top_words": "words", "course_words": "courseWords",
                        "lda_topic_words": "lda", "dominant_atu_types": "types", "dominant_regions": "regions",
                        "dominant_source_collections": "collections"})


def pagerank_nulls(ctx: Ctx, nodes: list[int], null_means: list[float]) -> dict[int, list[float]]:
    """PageRank of the given tales in the degree-preserving shuffles of the main graph. The shuffles are cached by
    content hash, so the file of this representation is the one whose means match the stage's reported null means."""
    for f in sorted(ctx.work.glob("degree_null_*.npz")):
        z = np.load(f, allow_pickle=False)
        if "pr" not in z or not nodes:
            continue
        pr = z["pr"]
        if np.allclose(pr[:, nodes].mean(axis=0), null_means, rtol=1e-3):
            return {n: pr[:, n].tolist() for n in nodes}
    return {}


def one_map(ctx: Ctx, rep: str, folk: pd.DataFrame, fidx: dict, S: np.ndarray) -> dict:
    from scipy.stats import spearmanr
    R = ctx.results
    z = np.load(ctx.work / f"map_{rep}.npz", allow_pickle=False)
    n = len(folk)
    assert len(z["group"]) == n and z["ids"].tolist() == folk["id"].tolist()
    nr = pd.read_csv(R / "network_robustness.csv")
    g = nr[(nr["rep"] == rep) & nr["canonical"].astype(bool)].iloc[0]
    pg = pd.read_csv(R / "partA_graphs.csv")
    pg = pg[pg["rep"] == rep]
    cc = pd.read_csv(R / "collection_confound.csv")
    cc = cc[(cc["rep"] == rep) & cc["map"].str.startswith("canonical")]
    ns = pd.read_csv(R / "network_structure.csv")
    nb = pd.read_csv(R / "network_backbone.csv")
    arch = pd.read_csv(R / "network_archetypes.csv", dtype={"atu_id": str})
    arch = arch[arch["rep"] == rep].sort_values("rank")
    parts = np.load(ctx.work / f"partitions_{rep}.npz", allow_pickle=False)
    assert parts["ids"].tolist() == folk["id"].tolist()
    deg = np.bincount(np.concatenate([z["i"], z["j"]]), minlength=n)
    tok = folk["n_tokens"].to_numpy()
    hubs = np.argsort(-deg, kind="stable")[:20]

    # degrees at every density of Part A (the same edge rule, recomputed from the similarities)
    density_degrees, density_stats = {}, []
    for _, row in pg.sort_values("density").iterrows():
        e = select_edges(S, float(row["density"]))
        assert e["m"] == int(row["m"]), "edge rule changed since Part A"
        density_degrees[f"{row['density']:g}"] = np.bincount(np.concatenate([e["i"], e["j"]]), minlength=n).astype(int).tolist()
        density_stats.append(dict(density=float(row["density"]), edges=int(row["m"]), threshold=r(row["similarity_threshold"]),
                                  components=int(row["components"]), largest=int(row["largest_component"]), isolates=int(row["isolates"]),
                                  communities=int(row["communities"]), major=int(row["communities_major"]), modularity=r(row["modularity"]),
                                  nullMean=r(row["null_mean"]), z=r(row["z"], 1)))
    # the tales and the partition of the label tests (stage `network`), for shuffles in the browser
    labelled = np.flatnonzero((folk["atu_id"].notna() & folk["region"].notna() & folk["source_collection"].notna()).to_numpy())
    part = codes(parts[f"density_{g['value']:g}"][labelled].tolist())[0]
    seeds = {s: z[f"seed{s}"].astype(int).tolist() for s in (42, 7, 19)}
    top = arch.head(ARCHETYPE_NULLS)
    nulls = pagerank_nulls(ctx, [fidx[i] for i in top["id"]], top["null_mean"].tolist())
    bb = z["backbone"]
    return dict(
        x=rl(z["xy"][:, 0], 3), y=rl(z["xy"][:, 1], 3), group=z["group"].astype(int).tolist(), degree=deg.astype(int).tolist(),
        pagerank=rl(z["pagerank"] * n, 3), pagerankZ=rl(z["pagerank_z"], 2),
        edges=np.stack([z["i"][bb], z["j"][bb]], axis=1).astype(int).ravel().tolist(),
        communities=community_rows(R, rep),
        stats=dict(n=int(g["n"]), edges=int(g["m"]), threshold=r(g["similarity_threshold"]), modularity=r(g["modularity"]),
                   nullMean=r(g["modularity_null_mean"]), z=r(g["modularity_z"], 1), major=int(g["communities_major"]),
                   communities=int(g["communities"]), components=int(g["components"]), isolates=int(g["isolates"]),
                   largest=int(pg[pg["primary"].astype(bool)]["largest_component"].iloc[0]), shuffles=int(g["modularity_shuffles"]),
                   seedNmiMin=r(g["seed_nmi_min"], 2), seedNmiMax=r(g["seed_nmi_max"], 2), density=float(g["value"])),
        densities=dict(stats=density_stats, degrees=density_degrees),
        seeds=dict(partitions={str(s): v for s, v in seeds.items()},
                   nmi={f"{a}-{b}": r(nmi(*(codes(seeds[x])[0] for x in (a, b))), 3) for a, b in combinations((42, 7, 19), 2)}),
        partitions={k: parts[k].astype(int).tolist() for k in parts.files if k != "ids"},
        structure=records(ns[ns["rep"] == rep], {"measure": "measure", "observed": "observed", "null": "null", "null_mean": "nullMean",
                                                 "z": "z", "shuffles": "shuffles"}),
        organise=records(cc, {"label": "label", "null": "null", "measure": "measure", "observed": "observed", "null_mean": "nullMean",
                              "null_q025": "nullLow", "null_q975": "nullHigh", "excess": "excess", "z": "z", "p_upper": "p", "n": "n"}),
        labelTest=dict(nodes=labelled.astype(int).tolist(), part=part.astype(int).tolist()),
        backbone=records(nb[nb["rep"] == rep], {"filtered": "filtered", "alpha": "alpha", "edges_in": "edgesIn", "edges_kept": "kept",
                                                "nodes_with_an_edge": "nodes", "share_of_kept_edges_within_a_community": "within"}),
        archetypes=[dict(node=fidx[x["id"]], title=x["title"], atu=x["atu_id"] if isinstance(x["atu_id"], str) else "",
                         community=x["community"], degree=int(x["degree"]), pagerank=r(x["pagerank"] * n, 3), nullMean=r(x["null_mean"] * n, 3),
                         z=r(x["z"], 1), null=[r(v * n, 3) for v in nulls.get(fidx[x["id"]], [])])
                    for _, x in top.iterrows()],
        degreeLength=dict(spearman=r(spearmanr(deg, tok).statistic, 2), hubTokens=int(np.median(tok[hubs])),
                          medianTokens=int(np.median(tok))))


def network_payload(ctx: Ctx, folk: pd.DataFrame, fidx: dict, sims: dict) -> dict:
    nr = pd.read_csv(ctx.results / "network_robustness.csv")
    sweep = nr[~nr["edges_by"].str.contains("masked")]

    def excess(row, label, within=False):
        null = row[f"{label}_nmi_within_collection_null_mean" if within else f"{label}_nmi_null_mean"]
        return row[f"{label}_nmi"] - null

    rows = [dict(rep=x["rep"], by=x["edges_by"], value=r(x["value"], 3), key=f"{x['edges_by']}_{x['value']:g}", canonical=bool(x["canonical"]),
                 edges=int(x["m"]), communities=int(x["communities_major"]), modularity=r(x["modularity"]),
                 nmiCanonical=r(x["nmi_with_canonical"], 3), type=r(excess(x, "atu_type")), region=r(excess(x, "region")),
                 collection=r(excess(x, "source_collection")), typeWithin=r(excess(x, "atu_type", True)),
                 regionWithin=r(excess(x, "region", True)))
            for _, x in sweep.iterrows()]
    return dict(built=date.today().isoformat(), reps=ctx.reps, primary=ctx.primary,
                maps={rep: one_map(ctx, rep, folk, fidx, sims[rep]) for rep in ctx.reps},
                sweep=dict(graphs=len(rows), typeBeatsRegion=int(sum(x["type"] > x["region"] for x in rows)), rows=rows))


# ================================================================= near.json
def near_payload(ctx: Ctx, folk: pd.DataFrame, queries: pd.DataFrame, sims: dict, tfidf, qrows) -> dict:
    """Ten nearest folktales of every folktale (self excluded) and of every text, with the TF-IDF words that carry
    each of the first five matches, and the openings of every folktale and retelling."""
    vocab = tfidf.vocab
    out: dict = {"folk": {}, "texts": {}}
    for rep, S in sims.items():
        S = S.copy()
        np.fill_diagonal(S, -np.inf)
        idx = np.argsort(-S, axis=1, kind="stable")[:, :NEAR_K]
        out["folk"][rep] = dict(
            idx=idx.astype(int).tolist(),
            cos=[rl(S[i, idx[i]], 3) for i in range(len(folk))],
            words=[[" ".join(w for w, _ in drivers(tfidf.F[i], tfidf.F[j], vocab, 3)) for j in idx[i, :WORDS_FOR]] for i in range(len(folk))])
        z = np.load(ctx.work / f"partB_{rep}.npz", allow_pickle=False)
        qpos = {k: i for i, k in enumerate(z["query_ids"])}
        out["texts"][rep] = {qid: [" ".join(w for w, _ in drivers(qrows[k], tfidf.F[j], vocab, 5)) for j in z["idx"][qpos[qid], :WORDS_FOR]]
                             for k, qid in enumerate(queries["id"]) if qid in qpos}
    out["opening"] = [opening(t) for t in folk["text"]]
    cal = queries[queries["kind"] == "calibration"]
    out["calibrationOpening"] = dict(zip(cal["id"], [opening(t) for t in cal["text"]]))
    return out


# ================================================================= story.json
def calibration(ctx: Ctx, corpus, atu_names: dict, nearest: dict) -> dict:
    """Recall of the held-out retellings, and each retelling for the tale-type game, with its nearest folktales."""
    R, prim = ctx.results, ctx.primary
    cal = pd.read_csv(R / "calibration.csv").set_index("representation")
    cq = pd.read_csv(R / "calibration_queries.csv", dtype={"atu_id": str, f"vote_{prim}": str})
    calib = corpus.calib.set_index("id")
    items = []
    for x in cq.to_dict("records"):
        c = calib.loc[x["id"]]
        vote = str(x[f"vote_{prim}"])
        items.append(dict(id=x["id"], title=x["title"], tradition=x["tradition"], collection=c["collection"], atu=x["atu_id"],
                          atuName=c["atu_name"] or atu_names.get(x["atu_id"], ""), opening=opening(c["text"]),
                          rank=int(x[f"rank_{prim}"]), vote=vote, voteName=atu_names.get(vote, ""), sameType=int(x["same_type_folktales"]),
                          ranks={rep: int(x[f"rank_{rep}"]) for rep in ctx.reps}, near={rep: nearest[rep][x["id"]] for rep in ctx.reps}))
    p = cal.loc[prim]
    return dict(queries=int(p["queries"]), hits=int(p["hits"]), recall=r(p["recall_at_k"], 3), low=r(p["ci_low"], 3),
                high=r(p["ci_high"], 3), chance=r(p["chance_at_k"], 3), vote=r(p["vote_accuracy"], 3), voteChance=r(p["vote_chance"], 4),
                k=int(ctx.paper["checks"]["recall_k"]),
                byRep={rep: dict(recall=r(cal.at[rep, "recall_at_k"], 3), low=r(cal.at[rep, "ci_low"], 3), high=r(cal.at[rep, "ci_high"], 3),
                                 vote=r(cal.at[rep, "vote_accuracy"], 3)) for rep in cal.index},
                other={rep: r(cal.at[rep, "recall_at_k"], 3) for rep in cal.index if rep != prim},
                options=TYPE_OPTIONS, items=items,
                maxCosine=r(read_json(R / "calibration_exclusion.json")["per_representation"][prim]["max_cosine"], 3))


def rep_results(ctx: Ctx, rep: str) -> dict:
    """The headline tables of one representation (the variant of the same name)."""
    R = ctx.results
    hb = pd.read_csv(R / "headline_by_tradition.csv")
    cells = pd.read_csv(R / "headline_community_excess.csv")
    types = pd.read_csv(R / "headline_atu_by_tradition.csv", dtype={"atu_id": str})
    fb = pd.read_csv(R / "partB_folktale_baseline.csv")
    fb = fb[(fb["rep"] == rep) & (fb["candidates"] == "all other folktales")].iloc[0]
    lc = pd.read_csv(R / "length_control.csv")
    return dict(
        headline=records(hb[hb["variant"] == rep], {
            "tradition": "tradition", "n_parables": "nPar", "n_baseline": "nBase", "parable_median": "par", "baseline_median": "base",
            "diff": "diff", "diff_ci_low": "low", "diff_ci_high": "high", "diff_p_upper": "p", "closer_than_baseline": "closer",
            "jsd_bits": "jsd", "jsd_null_mean": "jsdNull", "jsd_p_upper": "jsdP", "profile_differs": "differs",
            "top_excess_community": "topCommunity", "top_excess": "topExcess", "top_excess_significant_bonferroni": "topSig",
            "top_source_collection": "topCollection", "top_source_collection_share": "topCollectionShare"}),
        cells=records(cells[cells["variant"] == rep], {
            "tradition": "tradition", "community": "community", "community_words": "words", "map_share": "map",
            "parable_share": "par", "baseline_share": "base", "excess": "excess", "p_two_sided": "p", "significant_bonferroni": "sig"}),
        types=records(types[types["variant"] == rep], {"tradition": "tradition", "kind": "kind", "rank": "rank", "atu_id": "atu",
                                                       "atu_name": "name", "share": "share"}),
        folkBand=dict(q25=r(fb["q25"]), q50=r(fb["q50"]), q75=r(fb["q75"])),
        lengthControl=records(lc[(lc["kind"] == "parable") & (lc["rep"] == rep)], {
            "tradition": "tradition", "diff_median": "diff", "diff_ci_low": "low", "diff_ci_high": "high", "share_above_own_excerpts": "above"}))


def texts(ctx: Ctx, fidx: dict) -> list[dict]:
    """Every parable and baseline passage: opening, and per representation its folk-closeness, ten nearest
    folktales, the community they vote for most and the tale type they vote for."""
    R = ctx.results
    par = pd.read_csv(PARABLES_CSV, dtype=str, keep_default_na=False).set_index("id")
    rk = pd.read_csv(R / "partB_ranking.csv", dtype={"nearest_10_ids": str})
    rk = rk[rk["kind"].isin(["parable", "baseline"])]
    ht = pd.read_csv(R / "headline_texts.csv", dtype={"voted_atu": str}).set_index(["variant", "id"])
    out: dict = {}
    for rep in ctx.reps:
        for pid, row in rk[rk["rep"] == rep].set_index("id").sort_index().iterrows():
            t = out.setdefault(pid, dict(id=pid, kind=row["kind"], tradition=row["tradition"], title=row["title"], tokens=int(row["n_tokens"]),
                                         source=par.at[pid, "source"], year=par.at[pid, "year"], url=par.at[pid, "url"],
                                         opening=opening(par.at[pid, "text"]), rep={}))
            v = ht.loc[(rep, pid)] if (rep, pid) in ht.index else None
            t["rep"][rep] = dict(closeness=r(row["folk_closeness"]),
                                 nearest=[fidx[i] for i in str(row["nearest_10_ids"]).split(";")[:NEAR_K]],
                                 cos=[r(float(c), 3) for c in str(row["nearest_10_cosines"]).split(";")[:NEAR_K]],
                                 community=None if v is None else v["modal_community"],
                                 voted=None if v is None or pd.isna(v["voted_atu"]) else v["voted_atu"])
    return [out[k] for k in sorted(out)]


def story_payload(ctx: Ctx, corpus, folk: pd.DataFrame, fidx: dict) -> dict:
    R, prim = ctx.results, ctx.primary
    atu_names = dict(zip(folk["atu_id"].dropna(), folk.loc[folk["atu_id"].notna(), "atu_name"]))
    rk = pd.read_csv(R / "partB_ranking.csv", dtype={"nearest_10_ids": str})
    cal_near = {rep: {x["id"]: dict(idx=[fidx[i] for i in str(x["nearest_10_ids"]).split(";")],
                                    cos=[r(float(c), 3) for c in str(x["nearest_10_cosines"]).split(";")])
                      for x in rk[(rk["rep"] == rep) & (rk["kind"] == "calibration")].to_dict("records")} for rep in ctx.reps}
    txt = texts(ctx, fidx)
    summary = read_json(R / "corpus_summary.json")
    rc = summary["region_counts"]
    meta = read_json(R / "collection_metadata.json")
    lm = pd.read_csv(R / "length_matching.csv")
    reg = pd.read_csv(R / "length_regression.csv")
    md = pd.read_csv(R / "match_drivers_by_tradition.csv")
    rob = pd.read_csv(R / "robustness_headline.csv")
    t1 = pd.read_csv(R / "table1_robustness.csv")
    ps = pd.read_csv(R / "parables_summary.csv")
    sm = pd.read_csv(R / "checks_second_method.csv")
    slope = reg[(reg["rep"] == prim) & reg["model"].str.startswith("parables") & (reg["term"] == "log(words)")].iloc[0]

    return dict(
        built=date.today().isoformat(), commit=git_commit(), primary=prim, reps=ctx.reps, traditions=TRADITIONS,
        settings=dict(permutations=ctx.paper["headline"]["permutations"], closenessK=ctx.paper["partB"]["closeness_k"],
                      attachK=ctx.paper["partB"]["attach_k"], labelShuffles=ctx.paper["map"]["label_shuffles"],
                      openingWords=OPENING_WORDS, nearK=NEAR_K),
        corpus=dict(folktales=summary["folktales"], calibration=summary["calibration"], typed=summary["folktales_with_one_atu_type"],
                    types=summary["atu_types"], withRegion=summary["folktales_with_region"], regions=summary["regions"],
                    europeShare=round(sum(v for k, v in rc.items() if "Europe" in k) / max(sum(rc.values()), 1), 3),
                    collectionKnown=meta["with_source_collection"], collections=meta["source_collections"],
                    translatorKnown=meta["with_translator"], regionCounts={k: int(v) for k, v in rc.items()},
                    parables=sum(t["kind"] == "parable" for t in txt), baseline=sum(t["kind"] == "baseline" for t in txt)),
        sources=records(ps, {"tradition": "tradition", "kind": "kind", "n": "n", "tokens_median": "tokens", "sources": "sources"}),
        folktales=dict(id=folk["id"].tolist(), title=folk["title"].tolist(), atu=folk["atu_id"].fillna("").tolist(),
                       atuName=folk["atu_name"].fillna("").tolist(), region=folk["region"].fillna("").tolist(),
                       collection=folk["source_collection"].fillna("").tolist(), tokens=folk["n_tokens"].astype(int).tolist()),
        links=dict(typePages=type_pages(), index="https://sites.pitt.edu/~dash/folktexts.html",
                   dataset="https://github.com/j-hagedorn/trilogy/tree/" + ctx.cfg["sources"]["trilogy_commit"]),
        calibration=calibration(ctx, corpus, atu_names, cal_near),
        texts=txt,
        byRep={rep: rep_results(ctx, rep) for rep in ctx.reps},
        length=dict(matching=records(lm, {"tradition": "tradition", "parable_tokens_median": "par", "baseline_tokens_median": "base",
                                          "mann_whitney_p": "p", "matched": "matched"}),
                    slope=r(slope["estimate"]), slopeP=r(slope["p"], 6), orderRaw=slope["order_raw"], orderEqual=slope["order_at_equal_length"]),
        drivers=records(md, {"tradition": "tradition", "kind": "kind", "top_driver_terms": "terms",
                             "noun_share_of_cosine_median": "nounShare", "percentile_among_folktales": "percentile",
                             "percentile_among_folktales_nouns_masked": "percentileMasked"}),
        secondMethod=records(sm, {"scope": "scope", "n": "n", "spearman_folk_closeness": "spearman", "mean_jaccard_top10": "jaccard",
                                  "same_nearest_folktale": "sameNearest"}),
        robust=records(rob, {"variant": "variant", "tradition": "tradition", "closer": "closer", "closer_p": "p", "diff": "diff"}),
        table1=records(t1, {"check": "check", "variant": "variant", "holds": "holds", "agreement": "agreement", "key_number": "key"}))


# ================================================================= build
def node_bin() -> Path | None:
    found = shutil.which("npm")
    if found:
        return Path(found).parent
    tools = sorted((ROOT / ".tools").glob("node-*"))
    return tools[-1] if tools else None


def build_site() -> str:
    nb = node_bin()
    if nb is None or not (WEB / "node_modules").exists():
        return "Node or web/node_modules not found, so the site was not built (cd web && npm ci && npm run build)"
    env = dict(os.environ, PATH=str(nb) + os.pathsep + os.environ.get("PATH", ""))
    npm = shutil.which("npm", path=env["PATH"]) or "npm"
    res = subprocess.run([npm, "run", "build"], cwd=WEB, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("npm run build failed:\n" + res.stdout[-3000:] + res.stderr[-3000:])
    return "site built into web/dist"


def write(name: str, data: dict) -> None:
    path = SITE / name
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    print(f"  data/site/{name} {path.stat().st_size / 1e6:.2f} MB")


def build(ctx: Ctx | None = None, build_web: bool = True) -> dict:
    ctx = ctx or Ctx()
    SITE.mkdir(parents=True, exist_ok=True)
    corpus = load_corpus(ctx)
    folk = corpus.folk.reset_index(drop=True)
    fidx = {k: i for i, k in enumerate(folk["id"])}
    queries = corpus.queries(ctx).reset_index(drop=True)
    spaces = {rep: build_space(rep, folk["text"].tolist(), ctx.cfg) for rep in ctx.reps}
    sims = {rep: spaces[rep].folk_sim() for rep in ctx.reps}
    tfidf = spaces["tfidf"]
    qrows = tfidf.transform(queries["text"].tolist())
    write("story.json", story_payload(ctx, corpus, folk, fidx))
    write("network.json", network_payload(ctx, folk, fidx, sims))
    write("near.json", near_payload(ctx, folk, queries, sims, tfidf, qrows))
    if build_web:
        print(f"  {build_site()}")
    return dict(files=3)


def run(ctx: Ctx) -> dict:
    if ctx.sample:
        print("  site: skipped in a development run (the site shows full-data results only)")
        return {}
    return build(ctx)


if __name__ == "__main__":
    build()
