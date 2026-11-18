"""Stage `site`: the website's data, built from the paper pipeline's results (feedback update, step 8).

    python -m ouaw.run --stage site      (or python -m ouaw.site)

Writes, all committed:
  data/site/paper.json      every number of the overview page (headline, map, validity, Table 1), read from results/
  data/site/parables.json   the Parables explorer (map coordinates, every parable with its nearest folktales)
  data/site/figures/*.png   web-sized copies of the paper's figures
and mirrors them into web/public/data/ (stamped with the current website run), then builds the site with
`npm run build` when Node is available. The website export (`python -m analysis export`) copies the same files,
so the deploy workflow publishes them without rerunning the paper pipeline. Only titles, ATU types and openings
of at most 40 words are included, never full texts. No number on the site is typed by hand.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .common import PARABLES_CSV, ROOT, TRADITIONS, Ctx, read_json
from .corpus import load_corpus

SITE = ROOT / "data" / "site"
OUT = SITE / "parables.json"
WEB = ROOT / "web"
REPS = ["tfidf", "embedding"]
OPENING_WORDS = 40
FIGURES = ["fig1_map", "fig2_headline", "fig3_validity", "figS1_labels", "figS2_headline_embedding"]
WEB_FIGURE_WIDTH = 1800                     # pixels; the paper's PNGs are 300 dpi


def r(x, d=6):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


def opening(text: str, n: int = OPENING_WORDS) -> str:
    w = str(text).split()
    return " ".join(w[:n]) + (" …" if len(w) > n else "")


def payload(ctx: Ctx) -> dict:
    R, W = ctx.results, ctx.work
    corpus = load_corpus(ctx)
    folk = corpus.folk.reset_index(drop=True)
    fidx = {k: i for i, k in enumerate(folk["id"])}
    member = pd.read_csv(R / "partA_membership.csv").set_index("id").loc[folk["id"]]

    # ---- folktales (titles and labels only)
    folktales = dict(id=folk["id"].tolist(), title=folk["title"].tolist(),
                     atu=folk["atu_id"].fillna("").tolist(), atuName=folk["atu_name"].fillna("").tolist(),
                     region=folk["region"].fillna("").tolist())

    # ---- map per representation
    comm = pd.read_csv(R / "partA_communities.csv")
    graphs = pd.read_csv(R / "partA_graphs.csv")
    agree = pd.read_csv(R / "partA_type_vs_region.csv")
    maps = {}
    for rep in REPS:
        z = np.load(W / f"map_{rep}.npz", allow_pickle=False)
        nulls = read_json(W / f"map_{rep}_nulls.json")
        bb = z["backbone"]
        c = comm[comm["rep"] == rep]
        g = graphs[(graphs["rep"] == rep) & graphs["primary"]].iloc[0]
        a = agree[(agree["rep"] == rep) & (agree["node_set"] == "type_and_region")]
        tvr = {}
        for label in ("atu_type", "region"):
            row = a[(a["label"] == label) & (a["measure"] == "nmi")].iloc[0]
            null = np.array(nulls[f"type_and_region|{label}"]["nmi"])
            tvr[label] = dict(observed=r(row["observed"]), nullMean=r(null.mean()), nullMin=r(null.min()), nullMax=r(null.max()),
                              assort=r(a[(a["label"] == label) & (a["measure"] == "assortativity")]["observed"].iloc[0]))
        deg = np.bincount(np.concatenate([z["i"], z["j"]]), minlength=len(folk))
        maps[rep] = dict(
            x=[r(v, 4) for v in z["xy"][:, 0]], y=[r(v, 4) for v in z["xy"][:, 1]], group=z["group"].astype(int).tolist(),
            linked=(deg > 0).astype(int).tolist(),
            edges=np.stack([z["i"][bb], z["j"][bb]], axis=1).astype(int).ravel().tolist(),
            communities=[dict(name=x["community"], size=int(x["size"]), words=str(x["top_words"]).split()[:6],
                              types=str(x["top_tale_types"]), regions=str(x["top_regions"])) for _, x in c.iterrows()],
            stats=dict(edges=int(g["m"]), threshold=r(g["similarity_threshold"]), modularity=r(g["modularity"]),
                       nullMean=r(g["null_mean"]), nullSd=r(g["null_sd"], 5), shuffles=int(g["shuffles"]),
                       communities=int(g["communities"]), major=int(g["communities_major"]),
                       seedNmiMin=r(g["seed_nmi_min"], 2), seedNmiMax=r(g["seed_nmi_max"], 2), n=int(a["n"].iloc[0])),
            typeVsRegion=tvr)

    # ---- parables and baseline passages
    par = pd.read_csv(PARABLES_CSV, dtype=str, keep_default_na=False).set_index("id")
    ranking = pd.read_csv(R / "partB_ranking.csv", dtype={"nearest_10_ids": str})
    texts = {}
    for rep in REPS:
        rk = ranking[(ranking["rep"] == rep) & ranking["kind"].isin(["parable", "baseline"])].set_index("id")
        for pid, row in rk.iterrows():
            t = texts.setdefault(pid, dict(id=pid, kind=row["kind"], tradition=row["tradition"], title=row["title"],
                                           tokens=int(row["n_tokens"]), source=par.at[pid, "source"],
                                           translator=par.at[pid, "translator"], year=par.at[pid, "year"],
                                           url=par.at[pid, "url"], opening=opening(par.at[pid, "text"]),
                                           note=par.at[pid, "segment_note"], closeness={}, rank={}, nearest={}, cos={}))
            t["closeness"][rep] = r(row["folk_closeness"])
            t["rank"][rep] = None if pd.isna(row["rank_among_parables"]) else int(row["rank_among_parables"])
            ids = str(row["nearest_10_ids"]).split(";")[:5]
            t["nearest"][rep] = [fidx[i] for i in ids]
            t["cos"][rep] = [r(float(v), 3) for v in str(row["nearest_10_cosines"]).split(";")[:5]]

    trad = pd.read_csv(R / "partB_traditions.csv")
    fb = pd.read_csv(R / "partB_folktale_baseline.csv")
    att = pd.read_csv(R / "partB_attachment.csv")
    variants = pd.read_csv(R / "checks_ranking_variants.csv")
    per_rep = {}
    for rep in REPS:
        f = fb[(fb["rep"] == rep) & (fb["candidates"] == "all other folktales")].iloc[0]
        per_rep[rep] = dict(
            traditions=[{k: (r(v) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (int, np.integer)) else v))
                         for k, v in x.items()} for x in trad[trad["rep"] == rep].to_dict("records")],
            folktales=dict(q05=r(f["q05"]), q25=r(f["q25"]), q50=r(f["q50"]), q75=r(f["q75"]), q95=r(f["q95"])),
            cells=[dict(tradition=x["tradition"], community=x["community"], share=r(x["share"]), expected=r(x["expected_share"]),
                        diff=r(x["share_minus_expected"]), sig=bool(x["significant_bonferroni"]), links=int(x["links"]))
                   for x in att[att["rep"] == rep].to_dict("records")],
            variants=[dict(variant=x["variant"], tradition=x["tradition"], median=r(x["median"]), rank=int(x["rank"]))
                      for x in variants[variants["rep"] == rep].to_dict("records")])

    # ---- checks
    cal = pd.read_csv(R / "calibration.csv").set_index("representation")
    cq = pd.read_csv(R / "calibration_queries.csv").merge(corpus.calib[["id", "collection"]], on="id")
    second = pd.read_csv(R / "checks_second_method.csv")
    a2 = second[second["scope"] == "all parables"].iloc[0]
    length = pd.read_csv(R / "checks_length.csv")
    hub = pd.read_csv(R / "checks_hubness.csv").set_index("rep")
    hubs = pd.read_csv(R / "checks_hubs.csv")
    top = pd.read_csv(R / "top_pairs.csv")
    gate = read_json(R / "gate.json")
    corpus_summary = read_json(R / "corpus_summary.json")
    hand = read_json(R / "hand_label_agreement.json") if (R / "hand_label_agreement.json").exists() else {"status": "pending"}
    checks = dict(
        gate=dict(passed=gate["passed"], rule=gate["rule"]),
        calibration={rep: dict(recall=r(cal.at[rep, "recall_at_k"], 3), low=r(cal.at[rep, "ci_low"], 3), high=r(cal.at[rep, "ci_high"], 3),
                               chance=r(cal.at[rep, "chance_at_k"], 3), hits=int(cal.at[rep, "hits"]), queries=int(cal.at[rep, "queries"]),
                               recall1=r(cal.at[rep, "recall_at_1"], 3))
                     for rep in cal.index},
        queries=[dict(title=x["title"], collection=x["collection"], atu=x["atu_id"], sameType=int(x["same_type_folktales"]),
                      tfidf=int(x["rank_tfidf"]), embedding=int(x["rank_embedding"])) for x in cq.to_dict("records")],
        second=dict(spearman=r(a2["spearman_folk_closeness"], 2), jaccard=r(a2["mean_jaccard_top10"], 2),
                    sameNearest=r(a2["same_nearest_folktale"], 3), noShared=r(a2["share_with_no_shared_neighbour"], 3)),
        length={rep: r(length[(length["rep"] == rep) & (length["scope"] == "parables")]["spearman_closeness_vs_tokens"].iloc[0], 2)
                for rep in REPS},
        hubs={rep: dict(top10Share=r(hub.at[rep, "share_of_links_to_top10_hubs"], 3), never=r(hub.at[rep, "folktales_never_a_neighbour"], 3),
                        first=hubs[hubs["rep"] == rep].iloc[0]["title"],
                        firstShare=r(hubs[hubs["rep"] == rep].iloc[0]["share_of_parables"], 3)) for rep in REPS},
        topPairs={rep: [dict(tradition=x["tradition"], title=x["title"], folktale=x["nearest_title"], atu=x["nearest_atu"],
                             cosine=r(x["nearest_cosine"], 3), parableOpening=x["parable_opening"], folktaleOpening=x["folktale_opening"])
                        for x in top[top["rep"] == rep].to_dict("records")] for rep in REPS},
        hand=dict(status=hand.get("status", "pending")))

    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = ""
    return dict(built=date.today().isoformat(), commit=commit, primary=ctx.primary, traditions=TRADITIONS,
                corpus=dict(folktales=corpus_summary["folktales"], calibration=corpus_summary["calibration"],
                            typed=corpus_summary["folktales_with_one_atu_type"], types=corpus_summary["atu_types"],
                            both=corpus_summary["folktales_with_type_and_region"], regions=corpus_summary["regions"],
                            parables=int(sum(t["kind"] == "parable" for t in texts.values())),
                            baseline=int(sum(t["kind"] == "baseline" for t in texts.values()))),
                folktales=folktales, maps=maps, texts=sorted(texts.values(), key=lambda t: t["id"]), perRep=per_rep, checks=checks)


def records(df: pd.DataFrame, cols: list[str] | None = None) -> list[dict]:
    """JSON-safe rows: floats rounded, NaN -> None, numpy scalars -> Python."""
    out = []
    for row in (df[cols] if cols else df).to_dict("records"):
        clean = {}
        for k, v in row.items():
            if isinstance(v, (bool, np.bool_)):
                clean[k] = bool(v)
            elif isinstance(v, (int, np.integer)):
                clean[k] = int(v)
            elif isinstance(v, (float, np.floating)):
                clean[k] = None if np.isnan(v) else round(float(v), 6)
            else:
                clean[k] = v
        out.append(clean)
    return out


def captions(path: Path) -> dict[str, dict]:
    """report/captions.md -> {"Figure 1": {"title": ..., "text": ...}, ...}."""
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\*\*((?:Supplementary )?(?:Figure|Table) [^.]+)\.\s*(.*?)\*\*\s*(.*)", line)
            if m:
                out[m.group(1)] = dict(title=m.group(2).rstrip("."), text=m.group(3))
    return out


def paper_payload(ctx: Ctx) -> dict:
    """Everything the overview page shows; each value read from a results file."""
    R = ctx.results
    corpus = read_json(R / "corpus_summary.json")
    rc = corpus["region_counts"]
    ps = pd.read_csv(R / "parables_summary.csv")
    hb = pd.read_csv(R / "headline_by_tradition.csv")
    cells = pd.read_csv(R / "headline_community_excess.csv")
    types = pd.read_csv(R / "headline_atu_by_tradition.csv")
    lc = pd.read_csv(R / "length_control.csv")
    lm = pd.read_csv(R / "length_matching.csv")
    reg = pd.read_csv(R / "length_regression.csv")
    md = pd.read_csv(R / "match_drivers_by_tradition.csv")
    cal = pd.read_csv(R / "calibration.csv")
    t1 = pd.read_csv(R / "table1_robustness.csv")
    ct = pd.read_csv(R / "community_table.csv")
    nr = pd.read_csv(R / "network_robustness.csv")
    cc = pd.read_csv(R / "collection_confound.csv")
    nb = pd.read_csv(R / "network_backbone.csv")
    ns = pd.read_csv(R / "network_structure.csv")
    arch = pd.read_csv(R / "network_archetypes.csv")
    meta = read_json(R / "collection_metadata.json")
    excl = read_json(R / "calibration_exclusion.json")
    hand = read_json(R / "hand_label_agreement.json") if (R / "hand_label_agreement.json").exists() else {"status": "pending"}
    prim = ctx.primary
    return dict(
        built=date.today().isoformat(), commit=git_commit(), primary=prim, traditions=TRADITIONS,
        settings=dict(density=ctx.cfg["graphs"]["primary_density"], permutations=ctx.paper["headline"]["permutations"],
                      closenessK=ctx.paper["partB"]["closeness_k"], attachK=ctx.paper["partB"]["attach_k"],
                      labelShuffles=ctx.paper["map"]["label_shuffles"], handLabelPairs=5 * ctx.paper["checks"]["hand_labels"]["per_tradition"]),
        corpus=dict(folktales=corpus["folktales"], calibration=corpus["calibration"], typed=corpus["folktales_with_one_atu_type"],
                    types=corpus["atu_types"], withRegion=corpus["folktales_with_region"], regions=corpus["regions"],
                    both=corpus["folktales_with_type_and_region"],
                    europeShare=round(sum(v for k, v in rc.items() if "Europe" in k) / max(sum(rc.values()), 1), 4),
                    collectionKnown=meta["with_source_collection"], collections=meta["source_collections"],
                    translatorKnown=meta["with_translator"]),
        sources=records(ps, ["tradition", "kind", "n", "tokens_median", "sources"]),
        headline=records(hb[["variant", "tradition", "n_parables", "n_baseline", "parable_median", "baseline_median", "diff", "diff_ci_low",
                             "diff_ci_high", "diff_p_upper", "closer_than_baseline", "inside_share", "inside_null_mean", "inside_p_upper",
                             "jsd_bits", "jsd_null_mean", "jsd_p_upper", "profile_differs", "top_excess_community", "top_excess_community_words",
                             "top_excess", "top_excess_p", "top_excess_significant_bonferroni", "top_source_collection",
                             "top_source_collection_share"]]),
        cells=records(cells[cells["variant"] == prim], ["tradition", "community", "community_words", "map_share", "parable_share",
                                                        "baseline_share", "excess", "p_two_sided", "significant_bonferroni"]),
        types=records(types[types["variant"] == prim], ["tradition", "kind", "rank", "atu_id", "atu_name", "share", "n_texts"]),
        length=dict(control=records(lc[lc["kind"] == "parable"], ["rep", "tradition", "diff_median", "diff_ci_low", "diff_ci_high",
                                                                    "share_above_own_excerpts"]),
                    matching=records(lm), regression=records(reg[reg["model"].str.startswith("parables") & (reg["term"] == "log(words)")],
                                                             ["rep", "estimate", "p", "order_raw", "order_at_equal_length", "kendall_tau"])),
        drivers=records(md[md["kind"] == "parable"], ["tradition", "top_driver_terms", "noun_share_of_cosine_median"]),
        calibration=records(cal, ["representation", "queries", "hits", "recall_at_k", "ci_low", "ci_high", "chance_at_k", "vote_accuracy",
                                  "vote_hits", "vote_chance", "vote_chance_high"]),
        exclusion={r: round(excl["per_representation"][r]["max_cosine"], 4) for r in excl["per_representation"]},
        hand=dict(status=hand.get("status", "pending"), kappa=hand.get("cohen_kappa")),
        table1=records(t1, ["check", "variant", "holds", "agreement", "key_number"]),
        communities=records(ct[ct["rep"] == prim], ["community", "size", "top_words", "lda_topic_words", "dominant_atu_types",
                                                    "dominant_regions", "dominant_source_collections"]),
        map=dict(graph=records(nr[(nr["rep"] == prim) & nr["canonical"].astype(bool)], ["m", "similarity_threshold", "communities_major",
                                                                                     "modularity", "modularity_null_mean", "modularity_z",
                                                                                     "seed_nmi_min", "seed_nmi_max"])[0],
                 labels=records(cc[(cc["rep"] == prim) & cc["map"].str.startswith("canonical")],
                                ["label", "null", "measure", "observed", "null_mean", "null_q025", "null_q975", "p_upper"]),
                 sweep=records(nr, ["rep", "edges_by", "value", "communities_major", "nmi_with_canonical", "atu_type_nmi", "region_nmi",
                                    "source_collection_nmi"]),
                 backbone=records(nb[nb["rep"] == prim], ["filtered", "alpha", "edges_kept", "nodes_with_an_edge", "drawn"]),
                 structure=records(ns[ns["rep"] == prim], ["measure", "observed", "null", "null_mean", "z"]),
                 archetypes=records(arch[arch["rep"] == prim].head(5), ["title", "atu_id", "atu_name", "z"])),
        figures={f: f"figures/{f}.png" for f in FIGURES if (ctx.figures / f"{f}.png").exists()},
        captions=captions(ctx.report / "captions.md"))


def headline_for_explorer(ctx: Ctx) -> dict:
    """Parable/baseline community excess per representation, for the Parables page."""
    cells = pd.read_csv(ctx.results / "headline_community_excess.csv")
    hb = pd.read_csv(ctx.results / "headline_by_tradition.csv")
    return {rep: dict(cells=[dict(tradition=x["tradition"], community=x["community"], par=r(x["parable_share"]), base=r(x["baseline_share"]),
                                  diff=r(x["excess"]), sig=bool(x["significant_bonferroni"]))
                             for x in cells[cells["variant"] == rep].to_dict("records")],
                      traditions=[dict(tradition=x["tradition"], diff=r(x["diff"]), low=r(x["diff_ci_low"]), high=r(x["diff_ci_high"]),
                                       p=r(x["diff_p_upper"]), closer=bool(x["closer_than_baseline"]), differs=bool(x["profile_differs"]),
                                       jsdP=r(x["jsd_p_upper"]))
                                  for x in hb[hb["variant"] == rep].to_dict("records")])
                for rep in REPS}


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def web_figures(ctx: Ctx) -> list[str]:
    """Web-sized copies of the paper's PNG figures in data/site/figures/."""
    from PIL import Image
    out_dir = SITE / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    done = []
    for f in FIGURES:
        src = ctx.figures / f"{f}.png"
        if not src.exists():
            continue
        with Image.open(src) as im:
            im = im.convert("RGB")
            if im.width > WEB_FIGURE_WIDTH:
                im = im.resize((WEB_FIGURE_WIDTH, round(im.height * WEB_FIGURE_WIDTH / im.width)), Image.LANCZOS)
            im.save(out_dir / f"{f}.png", optimize=True)
        done.append(f)
    return done


def node_bin() -> Path | None:
    found = shutil.which("npm")
    if found:
        return Path(found).parent
    tools = sorted((ROOT / ".tools").glob("node-*"))
    return tools[-1] if tools else None


def mirror_and_build(build_web: bool = True) -> str:
    """Copy the site files into web/public/data (stamped like the website export) and build the site."""
    data = WEB / "public" / "data"
    if not (data / "manifest.json").exists():
        return "web/public/data has no manifest: run the website pipeline (`python -m analysis all`) once, then this stage"
    stamp_keys = ("run_id", "schema_version", "content_hash")
    manifest = read_json(data / "manifest.json")
    stamp = {k: manifest[k] for k in stamp_keys if k in manifest}
    for name in ("parables.json", "paper.json"):
        payload = json.loads((SITE / name).read_text(encoding="utf-8"))
        (data / name).write_text(json.dumps({**payload, **stamp}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    (data / "figures").mkdir(exist_ok=True)
    for png in (SITE / "figures").glob("*.png"):
        shutil.copyfile(png, data / "figures" / png.name)
    if not build_web:
        return "site data mirrored into web/public/data (build skipped)"
    nb = node_bin()
    if nb is None or not (WEB / "node_modules").exists():
        return "site data mirrored; Node or web/node_modules not found, so the site was not built (cd web && npm ci && npm run build)"
    env = dict(os.environ, PATH=str(nb) + os.pathsep + os.environ.get("PATH", ""))
    npm = shutil.which("npm", path=env["PATH"]) or "npm"
    res = subprocess.run([npm, "run", "build"], cwd=WEB, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("npm run build failed:\n" + res.stdout[-3000:] + res.stderr[-3000:])
    return "site data mirrored and the site built into web/dist"


def build(ctx: Ctx | None = None, build_web: bool = True) -> dict:
    ctx = ctx or Ctx()
    SITE.mkdir(parents=True, exist_ok=True)
    data = payload(ctx)
    data["headline"] = headline_for_explorer(ctx)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    figs = web_figures(ctx)
    paper = paper_payload(ctx)
    (SITE / "paper.json").write_text(json.dumps(paper, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    print(f"  data/site: parables.json {OUT.stat().st_size / 1e6:.2f} MB, paper.json {(SITE / 'paper.json').stat().st_size / 1e3:.0f} kB, "
          f"{len(figs)} figures")
    msg = mirror_and_build(build_web)
    print(f"  {msg}")
    return dict(figures=figs)


def run(ctx: Ctx) -> dict:
    if ctx.sample:
        print("  site: skipped in a development run (the site shows full-data results only)")
        return {}
    return build(ctx)


if __name__ == "__main__":
    build()
