"""results/RESULTS.md: every headline number next to its null or baseline, with the file it came from.

Written by the `figures` stage from the CSV and JSON files of the earlier stages; nothing is
computed here. Sentences are short so that they can be pasted into the paper.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from analysis.common import OUTPUTS

from .common import TRADITIONS, Ctx, read_json

REP = {"tfidf": "TF-IDF", "embedding": "embeddings"}


def f2(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.2f}"


def f3(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"


def pct(x, digits: int = 0) -> str:
    return f"{100 * x:.{digits}f}%"


def ordinal(x) -> str:
    n = int(round(x))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def pval(p) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def table(df: pd.DataFrame) -> list[str]:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return out


def write(ctx: Ctx) -> None:
    R = ctx.results
    rel = "results/_sample" if ctx.sample else "results"
    src = lambda name: f"(`{rel}/{name}`)"
    primary, reps = ctx.primary, [ctx.primary] + [r for r in ctx.reps if r != ctx.primary]
    L: list[str] = []
    add = L.append

    corpus = read_json(R / "corpus_summary.json")
    add("# Results")
    add("")
    add(f"Written by `python -m ouaw.run --stage figures` on {date.today().isoformat()}"
        + (f" from a development sample of {ctx.sample} folktales: these numbers are not results." if ctx.sample else ".")
        + f" Figures use the primary representation, **{REP[primary]}**; the other representation is reported next to it as the second method."
        " Every sentence ends with the file that holds its numbers. All statements describe these English translations and this corpus.")
    add("")

    # ------------------------------------------------------------- data
    add("## Data")
    add("")
    by = "; ".join(f"{v} {k}" for k, v in sorted(corpus["calibration_by_collection"].items(), key=lambda kv: -kv[1]))
    add(f"- The map is built from {corpus['folktales']:,} English folktale versions. The {corpus['calibration']} versions from religious collections "
        f"({by}) are held out as calibration queries {src('corpus_summary.json')}.")
    add(f"- {corpus['folktales_with_one_atu_type']:,} folktales carry one ATU tale type ({corpus['atu_types']} types); {corpus['folktales_with_region']:,} "
        f"have a mapped region ({corpus['regions']} regions); {corpus['folktales_with_type_and_region']:,} have both. The type-versus-region test uses those "
        f"{corpus['folktales_with_type_and_region']:,} {src('corpus_summary.json')}.")
    if (R / "parables_summary.csv").exists():
        ps = pd.read_csv(R / "parables_summary.csv")
        par, base = ps[ps["kind"] == "parable"].set_index("tradition"), ps[ps["kind"] == "baseline"].set_index("tradition")
        add(f"- {int(par['n'].sum())} parables from {len(par)} traditions and {int(base['n'].sum())} non-story baseline passages from the same translations "
            f"{src('parables_summary.csv')}; full texts in `data/processed/parables.csv`:")
        add("")
        rows = [dict(Tradition=t, Parables=int(par.at[t, "n"]), **{"Median tokens": int(par.at[t, "tokens_median"])},
                     **{"Baseline passages": int(base.at[t, "n"]) if t in base.index else 0},
                     **{"Baseline median tokens": int(base.at[t, "tokens_median"]) if t in base.index else "–"},
                     Sources=par.at[t, "sources"]) for t in TRADITIONS if t in par.index]
        L.extend(table(pd.DataFrame(rows)))
        add("")
        blocked = read_json(R / "blocked_sources.json")["blocked"]
        add(f"- Sources that could not be downloaded: {len(blocked)}" + ("." if not blocked else ": " + "; ".join(b["tradition"] for b in blocked) + ".")
            + f" Stories left out and why: {src('parables_skipped.csv')}.")
    add("")

    # ------------------------------------------------------------- part A
    graphs = pd.read_csv(R / "partA_graphs.csv")
    comm = pd.read_csv(R / "partA_communities.csv")
    agree = pd.read_csv(R / "partA_type_vs_region.csv")
    pa = read_json(R / "partA_summary.json")
    add("## Part A: the map of world folklore")
    add("")
    for rep in reps:
        g = graphs[graphs["rep"] == rep]
        gp = g[g["primary"]].iloc[0]
        s = pa["per_representation"][rep]
        add(f"### {REP[rep].capitalize() if rep == 'embedding' else REP[rep]}" + (" (primary)" if rep == primary else " (second method)"))
        add("")
        add(f"- Network: {int(gp['n']):,} folktales, an edge for the top {pct(gp['density'])} of pairs by cosine ({int(gp['m']):,} edges, cosine ≥ {f3(gp['similarity_threshold'])}); "
            f"{int(gp['isolates'])} tales have no edge {src('partA_graphs.csv')}.")
        add(f"- Communities: Louvain (seed 42) finds {int(gp['communities'])} communities, {int(gp['communities_major'])} of them with at least 1% of the tales "
            f"({s['tales_in_major']:,} tales; the other {s['tales_in_small']} tales sit in isolates and tiny groups) {src('partA_summary.json')}.")
        add(f"- Modularity is {f3(gp['modularity'])} against {f3(gp['null_mean'])} ± {gp['null_sd']:.4f} in {int(gp['shuffles'])} degree-preserving shuffles "
            f"(largest shuffle value {f3(gp['null_max'])}; z = {gp['z']:.0f}) {src('partA_graphs.csv')}.")
        add(f"- The three Louvain seeds agree with NMI {f2(gp['seed_nmi_min'])} to {f2(gp['seed_nmi_max'])} {src('partA_graphs.csv')}.")
        others = "; ".join(f"{pct(r['density'])} density: {f3(r['modularity'])} against {f3(r['null_mean'])} in {int(r['shuffles'])} shuffles"
                           for _, r in g[~g["primary"]].iterrows())
        add(f"- Other densities: {others} {src('partA_graphs.csv')}.")
        a = agree[(agree["rep"] == rep) & (agree["node_set"] == "type_and_region")].set_index(["label", "measure"])
        if len(a):
            n = int(a.iloc[0]["n"])
            t, r_ = a.loc[("atu_type", "nmi")], a.loc[("region", "nmi")]
            add(f"- Type or region: on the {n:,} tales with both labels, NMI between communities and ATU type is {f3(t['observed'])} "
                f"(1,000 label shuffles: mean {f3(t['null_mean'])}, largest {f3(t['null_max'])}; excess {f3(t['excess'])}). For region it is {f3(r_['observed'])} "
                f"(shuffles: mean {f3(r_['null_mean'])}, largest {f3(r_['null_max'])}; excess {f3(r_['excess'])}) {src('partA_type_vs_region.csv')}.")
            ta, ra = a.loc[("atu_type", "assortativity")], a.loc[("region", "assortativity")]
            above = [name for name, x in (("type", ta), ("region", ra)) if x["observed"] > x["null_max"]]
            verdict = {2: "both above every shuffle", 1: f"only {above[0] if above else ''} above every shuffle", 0: "neither above every shuffle"}[len(above)]
            add(f"- Attribute assortativity, which weighs every edge equally, is {f3(ta['observed'])} for tale type and {f3(ra['observed'])} for region "
                f"(shuffles: {f3(ta['null_mean'])} and {f3(ra['null_mean'])}; {verdict}) {src('partA_type_vs_region.csv')}.")
            te, re_ = a.loc[("atu_type", "same_label_edge_share")], a.loc[("region", "same_label_edge_share")]
            add(f"- Share of edges joining two tales of the same type: {pct(te['observed'], 1)} (shuffles {pct(te['null_mean'], 1)}); of the same region: "
                f"{pct(re_['observed'], 1)} (shuffles {pct(re_['null_mean'], 1)}) {src('partA_type_vs_region.csv')}.")
        add(f"- LDA with {s['lda']['k']} topics: NMI between a tale's dominant topic and its community is {f3(s['lda']['nmi']['observed'])} "
            f"(label shuffles {f3(s['lda']['nmi']['null_mean'])} ± {s['lda']['nmi']['null_sd']:.4f}); topic words in {src('partA_lda_topics.csv')}.")
        add(f"- Drawing: the disparity filter at α = {s['backbone']['alpha']} keeps {s['backbone']['disparity_edges_at_alpha']} of {int(gp['m']):,} edges. "
            f"The figure draws {s['backbone']['method']} ({s['backbone']['edges_drawn']:,} edges) {src('partA_summary.json')}.")
        add("")
        add(f"Communities of the {REP[rep]} map {src('partA_communities.csv')}:")
        add("")
        c = comm[comm["rep"] == rep]
        L.extend(table(pd.DataFrame([dict(Community=r["community"], Tales=int(r["size"]), **{"Top words (TF-IDF lift)": ", ".join(str(r["top_words"]).split()[:8])},
                                          **{"Most frequent tale types": r["top_tale_types"]}) for _, r in c.iterrows()])))
        add("")
    if pa["between_representations"]:
        add(f"- The TF-IDF and the embedding map are different partitions of the same tales: NMI between them is {f2(pa['between_representations']['nmi_between_partitions'])} "
            f"{src('partA_summary.json')}.")
    old = OUTPUTS / "metrics" / "agreement.json"
    if old.exists() and not ctx.sample:
        rows = {(r["rep"], r["label"]): r for r in read_json(old)["rows"]
                if r["graph_id"].startswith("joint-") and r["graph_id"].endswith("-d10") and r["seed"] == 42 and r["group"] == "main"}
        parts = []
        for rep, name in (("lexical", "TF-IDF"), ("semantic", "embeddings")):
            if (rep, "atu") in rows and (rep, "region") in rows:
                parts.append(f"{name}: type {f3(rows[(rep, 'atu')]['nmi']['excess'])}, region {f3(rows[(rep, 'region')]['nmi']['excess'])}")
        if parts:
            add(f"- Cross-check: the earlier network built only from the 1,133 tales with both labels (website pipeline) gives the same order of NMI excess. {'; '.join(parts)} "
                "(`outputs/metrics/agreement.json`).")
    pr = pd.read_csv(R / "partA_pagerank_top10.csv")
    for rep in reps:
        top = pr[pr["rep"] == rep].head(5)
        add(f"- Tales more central than their number of links predicts ({REP[rep]}; PageRank against the degree-preserving shuffles, among tales in the "
            "largest component with at least the median degree): "
            + "; ".join(f"“{r['title']}” (ATU {r['atu_id']}, z = {r['z']:.1f})" for _, r in top.iterrows()) + f" {src('partA_pagerank_top10.csv')}.")
    add("")

    # ------------------------------------------------------------- part B
    if not (R / "partB_traditions.csv").exists():
        (R / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
        return
    trad = pd.read_csv(R / "partB_traditions.csv")
    fb = pd.read_csv(R / "partB_folktale_baseline.csv")
    cells = pd.read_csv(R / "partB_attachment.csv")
    ent = pd.read_csv(R / "partB_attachment_entropy.csv")
    overlap = pd.read_csv(R / "partB_tradition_overlap.csv")
    words = pd.read_csv(R / "partB_distinctive_words.csv")
    add("## Part B: parables on the map")
    add("")
    add("Folk-closeness of a text is the mean cosine to its 5 nearest folktales. Intervals are 95% bootstrap intervals over parables.")
    add("")
    for rep in reps:
        t = trad[trad["rep"] == rep]
        f = fb[(fb["rep"] == rep) & (fb["candidates"] == "all other folktales")].iloc[0]
        fx = fb[(fb["rep"] == rep) & (fb["candidates"] != "all other folktales")].iloc[0]
        add(f"### {REP[rep].capitalize() if rep == 'embedding' else REP[rep]}" + (" (primary)" if rep == primary else " (second method)"))
        add("")
        add(f"- Scale: a folktale's folk-closeness to the other folktales has median {f3(f['q50'])} (middle 50%: {f3(f['q25'])} to {f3(f['q75'])}). "
            f"Leaving out tales of its own type, the median is {f3(fx['q50'])} {src('partB_folktale_baseline.csv')}.")
        add(f"- Ranking of traditions by median folk-closeness {src('partB_traditions.csv')}:")
        add("")
        rows = []
        for _, r in t.iterrows():
            row = {"Rank": int(r["rank"]), "Tradition": r["tradition"], "Parables": int(r["n_parables"]),
                   "Median [95% CI]": f"{f3(r['median'])} [{f3(r['ci_low'])}, {f3(r['ci_high'])}]",
                   "Percentile among folktales": f"{r['percentile_among_folktales']:.0f}",
                   "Same-translation baseline median": f3(r.get("baseline_median", np.nan)),
                   "Parables minus baseline [95% CI]": (f"{r['minus_baseline_median']:+.3f} [{r['minus_baseline_ci_low']:+.3f}, {r['minus_baseline_ci_high']:+.3f}]"
                                                         if pd.notna(r.get("baseline_median", np.nan)) else "n/a"),
                   "Parables above baseline 95th pct": pct(r["share_above_baseline_q95"]) if pd.notna(r.get("share_above_baseline_q95", np.nan)) else "n/a",
                   "Minus folktales of same length": f"{r['median_minus_folktales_of_same_length']:+.3f}"}
            rows.append(row)
        L.extend(table(pd.DataFrame(rows)))
        add("")
        top, bot = t.iloc[0], t.iloc[-1]
        add(f"- Most folktale-like tradition: {top['tradition']} (median {f3(top['median'])}); least: {bot['tradition']} ({f3(bot['median'])}). "
            f"The folktale median is {f3(f['q50'])}, so the tradition medians sit at the "
            + ", ".join(ordinal(r["percentile_among_folktales"]) for _, r in t.iterrows()) + f" percentile of folktales, in rank order {src('partB_traditions.csv')}.")
        above = t[t["minus_baseline_ci_low"] > 0]["tradition"].tolist() if "minus_baseline_ci_low" in t else []
        not_above = [x for x in t["tradition"] if x not in above]
        add(f"- Above the style baseline (interval of parables minus same-translation non-story text excludes 0): "
            + (", ".join(above) if above else "none") + ". Not above: " + (", ".join(not_above) if not_above else "none") + f" {src('partB_traditions.csv')}.")
        e = ent[ent["rep"] == rep]
        c = cells[cells["rep"] == rep]
        add(f"- Placement: each parable is linked to its 10 nearest folktales. Entropy of a tradition's links over the communities, against 1,000 shuffles of the community labels "
            f"{src('partB_attachment_entropy.csv')}: "
            + "; ".join(f"{r['tradition']} {f2(r['entropy_bits'])} bits (shuffles {f2(r['null_mean'])} ± {f2(r['null_sd'])}, {pval(r['p_lower'])}); top community {r['top_community']} with {pct(r['top_share'])} of links"
                        for _, r in e.iterrows()) + ".")
        sig = c[c["significant_bonferroni"]]
        if len(sig):
            parts = []
            for trad_name in [x for x in t["tradition"] if x in set(sig["tradition"])]:
                s_ = sig[sig["tradition"] == trad_name].sort_values("share_minus_expected", ascending=False)
                parts.append(f"{trad_name}: " + ", ".join(f"{r['community']} {100 * r['share_minus_expected']:+.0f} points (share {pct(r['share'])}, expected {pct(r['expected_share'])})"
                                                           for _, r in s_.iterrows()))
            add(f"- Cells that differ from the shuffle expectation after Bonferroni correction over {len(c)} cells {src('partB_attachment.csv')}: " + "; ".join(parts) + ".")
        else:
            add(f"- No tradition-by-community cell differs from the shuffle expectation after Bonferroni correction over {len(c)} cells {src('partB_attachment.csv')}.")
        o = overlap[overlap["rep"] == rep]
        if len(o):
            mean = o[o["tradition_a"].str.startswith("all pairs")].iloc[0]
            pairs = o[~o["tradition_a"].str.startswith("all pairs")].sort_values("jsd_bits")
            lo, hi = pairs.iloc[0], pairs.iloc[-1]
            add(f"- Do traditions land in the same communities? Mean Jensen-Shannon divergence between two traditions' link distributions is {f3(mean['jsd_bits'])} bits; "
                f"shuffling tradition labels over parables gives {f3(mean['null_mean'])} ± {f3(mean['null_sd'])} ({pval(mean['p_upper'])}). "
                f"Closest pair: {lo['tradition_a']} and {lo['tradition_b']} ({f3(lo['jsd_bits'])}); farthest: {hi['tradition_a']} and {hi['tradition_b']} ({f3(hi['jsd_bits'])}) "
                f"{src('partB_tradition_overlap.csv')}.")
        w = words[words["rep"] == rep]
        if len(w):
            add(f"- Distinctive words of the closest against the farthest quarter of each tradition's parables (log-odds) {src('partB_distinctive_words.csv')}:")
            for _, r in w.iterrows():
                add(f"  - {r['tradition']}: closest: {', '.join(str(r['closest_quarter']).split()[:10])}. Farthest: {', '.join(str(r['farthest_quarter']).split()[:10])}.")
        add("")
    add("- Reading the placement test: the label shuffle treats the 10 links of a parable as separate draws, but the nearest folktales of one parable resemble each other, "
        "so the shuffle spread is too narrow and the z-scores in `partB_attachment.csv` are generous. The tradition-label shuffle above uses the parable as the unit.")
    add("")

    # ------------------------------------------------------------- checks
    if (R / "calibration.csv").exists():
        cal = pd.read_csv(R / "calibration.csv")
        gate = read_json(R / "gate.json")
        add("## Checks")
        add("")
        add(f"### Calibration (the 14 November gate): **{'passed' if gate['passed'] else 'failed'}**")
        add("")
        add(f"- Rule: {gate['rule']} {src('gate.json')}.")
        for _, r in cal.iterrows():
            add(f"- {r['representation']}: recall@10 = {f2(r['recall_at_k'])} (95% CI {f2(r['ci_low'])} to {f2(r['ci_high'])}; {int(r['hits'])} of {int(r['queries'])} queries) "
                f"against a chance rate of {f3(r['chance_at_k'])} ({r['expected_hits_by_chance']:.1f} hits expected; {pval(r['p_value'])}). Recall@1 = {f2(r['recall_at_1'])}, "
                f"recall@5 = {f2(r['recall_at_5'])}; the first same-type folktale is at median rank {r['median_rank_of_first_right_answer']:g} of {corpus['folktales']:,} "
                f"{src('calibration.csv')}.")
        add(f"- Per query: {src('calibration_queries.csv')}.")
        add("")
        sm = pd.read_csv(R / "checks_second_method.csv")
        a = sm[sm["scope"] == "all parables"].iloc[0]
        add("### Second method")
        add("")
        add(f"- TF-IDF against embeddings over {int(a['n'])} parables: Spearman correlation of folk-closeness {f2(a['spearman_folk_closeness'])}; mean Jaccard overlap of the two top-10 "
            f"neighbour lists {f2(a['mean_jaccard_top10'])}; {pct(a['share_with_no_shared_neighbour'])} of parables share no neighbour; {pct(a['same_nearest_folktale'])} have the same "
            f"nearest folktale {src('checks_second_method.csv')}.")
        add("- By tradition (Spearman; Jaccard): " + "; ".join(f"{r['scope']} {f2(r['spearman_folk_closeness'])}; {f2(r['mean_jaccard_top10'])}"
                                                               for _, r in sm[sm["scope"] != "all parables"].iterrows()) + f" {src('checks_second_method.csv')}.")
        add("")
        ln = pd.read_csv(R / "checks_length.csv")
        add("### Length")
        add("")
        for rep in reps:
            x = ln[ln["rep"] == rep].set_index("scope")
            parts = [f"{scope} ρ = {f2(x.at[scope, 'spearman_closeness_vs_tokens'])}" for scope in ("parables", "baseline passages", "folktales (leave-one-out)") if scope in x.index]
            add(f"- {REP[rep]}: Spearman correlation of folk-closeness with length in tokens: " + "; ".join(parts) + f" {src('checks_length.csv')}.")
        add("")
        hb, hubs = pd.read_csv(R / "checks_hubness.csv"), pd.read_csv(R / "checks_hubs.csv")
        add("### Hubness")
        add("")
        for rep in reps:
            h = hb[hb["rep"] == rep].iloc[0]
            top = hubs[hubs["rep"] == rep].iloc[0]
            add(f"- {REP[rep]}: {pct(h['folktales_never_a_neighbour'])} of folktales are in no parable's top 10; the 10 most frequent neighbours take {pct(h['share_of_links_to_top10_hubs'])} "
                f"of all links (uniform: {pct(h['expected_share_if_uniform'], 1)}); skewness of the occurrence counts {f2(h['skewness'])}. Most frequent: “{top['title']}” "
                f"({top['n_tokens']} tokens), a neighbour of {pct(top['share_of_parables'])} of parables {src('checks_hubness.csv')}, {src('checks_hubs.csv')}.")
        add("")
        rv = pd.read_csv(R / "checks_ranking_variants.csv")
        add("### Does the tradition ranking survive?")
        add("")
        add(f"Order of the traditions by median, most folktale-like first, under each variant {src('checks_ranking_variants.csv')}:")
        add("")
        rows = []
        for rep in reps:
            for variant, g in rv[rv["rep"] == rep].groupby("variant", sort=False):
                g = g.sort_values("rank")
                rows.append({"Representation": REP[rep], "Variant": variant, "Order (median)": " > ".join(f"{r['tradition']} ({f3(r['median'])})" for _, r in g.iterrows())})
        L.extend(table(pd.DataFrame(rows)))
        add("")
        mk = read_json(R / "checks_masking.json")
        mrows = ln[ln["scope"].str.startswith("parables: masked")]
        add(f"- Masking replaces {mk['name_like_words']:,} name-like words and {len(mk['formulae'])} formulae; on average {pct(mk['share_of_tokens_masked'], 1)} of a parable's tokens. "
            "Spearman correlation between masked and unmasked folk-closeness: "
            + "; ".join(f"{REP[r['rep']]} {f2(r['spearman_closeness_vs_tokens'])}" for _, r in mrows.iterrows()) + f" {src('checks_masking.json')}, {src('checks_length.csv')}.")
        add("")
        add("### Hand labels")
        add("")
        hand = read_json(R / "hand_label_agreement.json") if (R / "hand_label_agreement.json").exists() else {"status": "pending"}
        if hand.get("status") == "pending":
            add("- **Pending.** `labeling/hand_labels_template.csv` holds the top-1 pair of 100 parables (20 per tradition, seed 0). Copy it to `labeling/hand_labels.csv`, "
                "fill `coder1` and `coder2`, then run `python -m ouaw.agreement` and `python -m ouaw.run --stage figures`. No label was filled in by code.")
        else:
            add(f"- {hand['coded_by_both']} pairs coded by both coders: raw agreement {f2(hand.get('raw_agreement'))}, Cohen's κ {f2(hand.get('cohen_kappa'))} "
                f"(linear weights {f2(hand.get('cohen_kappa_linear_weights'))}). Precision, both coders agree: same plot {f2(hand['precision']['strict'].get('both_coders_agree_it_is_a_parallel'))}; "
                f"same plot or shared motif {f2(hand['precision']['lenient'].get('both_coders_agree_it_is_a_parallel'))} {src('hand_label_agreement.json')}.")
        add("")

    if (R / "top_pairs.csv").exists():
        tp = pd.read_csv(R / "top_pairs.csv")
        add("## The five closest parable-folktale pairs")
        add("")
        for rep in reps:
            t = tp[tp["rep"] == rep]
            if not len(t):
                continue
            add(f"{REP[rep].capitalize() if rep == 'embedding' else REP[rep]} {src('top_pairs.csv')}:")
            add("")
            for _, r in t.iterrows():
                add(f"- cosine {f3(r['nearest_cosine'])}: {r['tradition']}, “{r['title']}” and the folktale “{r['nearest_title']}” (ATU {r['nearest_atu']}, {r['nearest_id']}).")
                add(f"  - Parable: “{r['parable_opening']}”")
                add(f"  - Folktale: “{r['folktale_opening']}”")
            add("")
    add("## Figures")
    add("")
    fig = "figures/_sample" if ctx.sample else "figures"
    add(f"- `{fig}/fig1_map` (map and type-versus-region check), `{fig}/fig2_closeness` (folk-closeness by tradition with both baselines), "
        f"`{fig}/fig3_placement` (tradition by community), `{fig}/fig4_calibration` (recall@10 and hand-label precision). Each as PDF and PNG.")
    (R / "RESULTS.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
