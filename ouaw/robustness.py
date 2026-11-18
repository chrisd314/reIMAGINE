"""Stage `robustness`: Table 1, does the headline survive each modelling choice? (feedback update, step 7)

The headline, per tradition and in the primary representation, is two findings:
  closer  the parables are closer to folktales than the non-story text of the same translation
          (one-sided within-tradition permutation p < 0.05)
  where   the parables' community profile differs from the baseline's (Jensen-Shannon divergence, permutation
          p < 0.05); the community with the largest positive excess is reported next to it
A check is compared verdict by verdict with the headline: "yes" when every comparable verdict agrees, "partly"
when at least 60% agree, "no" otherwise. The rule was fixed before the table was first computed (DECISIONS.md).

Checks: edge construction (other densities and kNN graphs: the profile on their partitions), representation
(embeddings), length (regression at equal length; length-matched folktale excerpts), noun masking, source
collection (within-collection null; collection share of the parables' links), names and collection/translator
formulae masked, hubs removed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import TRADITIONS, Ctx, read_json, write_csv
from .corpus import load_corpus
from .headline import community_counts, headline_tests
from .part_b import nearest
from .reps import Masker, build_space

YES_SHARE = 0.6
REP_NAME = {"tfidf": "TF-IDF", "embedding": "embeddings"}


def verdict(agree: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return "yes" if agree == total else ("partly" if agree >= YES_SHARE * total else "no")


def compare(base: dict, other: dict, keys=("closer", "where")) -> tuple[int, int]:
    """Agreements and comparisons between two {tradition: {closer: bool, where: bool}} verdict sets."""
    agree = total = 0
    for t, b in base.items():
        if t not in other:
            continue
        for k in keys:
            if k in b and k in other[t] and other[t][k] is not None:
                total += 1
                agree += bool(b[k]) == bool(other[t][k])
    return agree, total


def verdicts_from(res: dict, names: list[str]) -> dict:
    return {t: dict(closer=r["diff_p_upper"] < 0.05, where=r["jsd_p_upper"] < 0.05, closer_p=r["diff_p_upper"],
                    where_p=r["jsd_p_upper"], diff=r["diff"], top=names[int(np.argmax(r["excess"]))])
            for t, r in res.items()}


def names_of(lst) -> str:
    return ", ".join(lst) if lst else "none"


def run(ctx: Ctx) -> dict:
    corpus = load_corpus(ctx)
    folk, queries = corpus.folk, corpus.queries(ctx)
    rep = ctx.primary
    sel = queries["kind"].isin(["parable", "baseline"]).to_numpy()
    q = queries[sel].reset_index(drop=True)
    is_par = (q["kind"] == "parable").to_numpy()
    trad = q["tradition"].to_numpy()
    n_perm = ctx.shuffles(ctx.paper["headline"]["permutations"])
    n_boot = ctx.shuffles(ctx.paper["partB"]["bootstrap"], cap=1000)
    seed = ctx.paper["headline"]["seed"]
    k = ctx.paper["partB"]
    R = ctx.results

    hb = pd.read_csv(R / "headline_by_tradition.csv")

    def from_table(variant: str) -> dict:
        t = hb[hb["variant"] == variant]
        return {r["tradition"]: dict(closer=bool(r["closer_than_baseline"]), where=bool(r["profile_differs"]), closer_p=r["diff_p_upper"],
                                     where_p=r["jsd_p_upper"], diff=r["diff"], top=r["top_excess_community"]) for _, r in t.iterrows()}

    base = from_table(rep)
    group = np.load(ctx.work / f"map_{rep}.npz", allow_pickle=False)["group"]
    z = np.load(ctx.work / f"partB_{rep}.npz", allow_pickle=False)
    assert z["query_ids"].tolist() == queries["id"].tolist(), "rerun partB"
    idx0, x0 = z["idx"][sel], z["closeness"][sel]

    detail, rows = [], []

    def record(variant: str, v: dict):
        for t, d in v.items():
            detail.append(dict(variant=variant, tradition=t, closer=d.get("closer"), closer_p=d.get("closer_p"), where=d.get("where"),
                               where_p=d.get("where_p"), diff=d.get("diff"), top_excess_community=d.get("top")))

    record(f"{rep} (headline)", base)
    closer_base = [t for t in TRADITIONS if t in base and base[t]["closer"]]
    where_base = [t for t in TRADITIONS if t in base and base[t]["where"]]

    # ---- 1. edge construction: the profile on the partitions of the other graphs (closeness needs no graph)
    parts = np.load(ctx.work / f"partitions_{rep}.npz", allow_pickle=False)
    assert parts["ids"].tolist() == folk["id"].tolist(), "rerun the network stage"
    nr = pd.read_csv(R / "network_robustness.csv")
    ag = tot = 0
    for key in [k_ for k_ in parts.files if k_ != "ids"]:
        if key == f"density_{ctx.cfg['graphs']['primary_density']:g}":
            continue
        lab = parts[key]
        sizes = np.bincount(lab)
        grp = np.where(sizes[lab] >= max(2, 0.01 * len(lab)), lab, -1)
        C, names = community_counts(idx0, grp)
        v = verdicts_from(headline_tests(x0, C, is_par, trad, n_perm, n_boot, seed), names)
        record(f"{rep}, communities of {key}", v)
        a, t_ = compare(base, v, keys=("where",))
        ag, tot = ag + a, tot + t_
    graphs = nr[~nr["edges_by"].str.contains("masked")]
    type_above = int((graphs["atu_type_nmi_p"] < 0.05).sum())
    type_over_region = int((graphs["atu_type_nmi"] - graphs["atu_type_nmi_null_mean"] > graphs["region_nmi"] - graphs["region_nmi_null_mean"]).sum())
    g_rep = graphs[graphs["rep"] == rep]
    rows.append(dict(check="Edge construction", variant="densities 5% and 15%; kNN graphs, k = 5, 10, 20 (communities recomputed)",
                     holds=verdict(ag, tot), agreement=f"{ag} of {tot}",
                     key_number=(f"profile verdicts agree in {ag} of {tot} tradition × partition cases; partitions share NMI "
                                 f"{g_rep[~g_rep['canonical']]['nmi_with_canonical'].min():.2f}–{g_rep[~g_rep['canonical']]['nmi_with_canonical'].max():.2f} "
                                 f"with the canonical one; tale type beats its label shuffles in {type_above} of {len(graphs)} graphs and beats region "
                                 f"in excess NMI in {type_over_region} of {len(graphs)}"),
                     source="results/robustness_headline.csv; results/network_robustness.csv"))

    # ---- 2. representation
    other = [r for r in ctx.reps if r != rep]
    for o in other:
        v = from_table(o)
        record(o, v)
        a, t_ = compare(base, v)
        both = [t for t in TRADITIONS if base.get(t, {}).get("closer") and v.get(t, {}).get("closer")]
        sm = pd.read_csv(R / "checks_second_method.csv")
        rho = float(sm.loc[sm["scope"] == "all parables", "spearman_folk_closeness"].iloc[0])
        rows.append(dict(check="Representation", variant=f"{REP_NAME.get(o, o)} instead of {REP_NAME.get(rep, rep)}", holds=verdict(a, t_),
                         agreement=f"{a} of {t_}",
                         key_number=(f"closer than baseline with {REP_NAME.get(o, o)}: {names_of([t for t in TRADITIONS if v.get(t, {}).get('closer')])} "
                                     f"(headline: {names_of(closer_base)}); closer under both: {names_of(both)}; Spearman of folk-closeness {rho:.2f}"),
                         source="results/headline_by_tradition.csv; results/checks_second_method.csv"))

    # ---- 3. length
    reg = pd.read_csv(R / "length_regression.csv")
    lc = pd.read_csv(R / "length_control.csv")
    r_ = reg[(reg["rep"] == rep) & reg["term"].str.endswith("parables minus baseline at equal length")]
    v = {row["term"].split(":")[0]: dict(closer=bool(row["estimate"] > 0 and row["p"] / 2 < 0.05), closer_p=row["p"] / 2, diff=row["estimate"])
         for _, row in r_.iterrows()}
    record(f"{rep}, regression at equal length", v)
    a, t_ = compare(base, v, keys=("closer",))
    ex = lc[(lc["rep"] == rep) & (lc["kind"] == "parable")]
    lm = pd.read_csv(R / "length_matching.csv")
    rows.append(dict(check="Length", variant="parables against baseline at equal length (OLS on log words); length-matched folktale excerpts",
                     holds=verdict(a, t_), agreement=f"{a} of {t_}",
                     key_number=(f"at equal length closer than baseline: {names_of([t for t in TRADITIONS if v.get(t, {}).get('closer')])}; parables minus "
                                 f"length-matched folktale excerpts {ex['diff_median'].min():+.3f} to {ex['diff_median'].max():+.3f} (all below); "
                                 f"baselines length-matched in {int(lm['matched'].sum())} of {len(lm)} traditions"),
                     source="results/length_regression.csv; results/length_control.csv; results/length_matching.csv"))

    # ---- 4. noun masking
    if (hb["variant"] == "tfidf_nouns_masked").any():
        v = from_table("tfidf_nouns_masked")
        record("tfidf_nouns_masked", v)
        a, t_ = compare(base, v)
        cal = pd.read_csv(R / "calibration.csv").set_index("representation")
        rows.append(dict(check="Noun masking", variant="nouns and proper nouns masked (spaCy), TF-IDF refitted", holds=verdict(a, t_),
                         agreement=f"{a} of {t_}",
                         key_number=(f"closer than baseline: {names_of([t for t in TRADITIONS if v.get(t, {}).get('closer')])} (headline: {names_of(closer_base)}); "
                                     f"recall@10 {cal.at['tfidf_nouns_masked', 'recall_at_k']:.2f} against {cal.at['tfidf', 'recall_at_k']:.2f} unmasked "
                                     f"(chance {cal.at['tfidf', 'chance_at_k']:.3f})"),
                         source="results/headline_by_tradition.csv; results/calibration.csv"))

    # ---- 5. source collection
    cc = pd.read_csv(R / "collection_confound.csv")
    c0 = cc[(cc["rep"] == rep) & cc["map"].str.startswith("canonical") & (cc["measure"] == "nmi")].set_index(["label", "null"])
    tw = c0.loc[("atu_type", "within-collection shuffle")]
    rw = c0.loc[("region", "within-collection shuffle")]
    hp = hb[hb["variant"] == rep]
    max_share = float(hp["top_source_collection_share"].max())
    checks_ok = [bool(tw["p_upper"] < 0.05), max_share < ctx.paper["robustness"]["collection_dominance"]]
    p_txt = "p < 0.001" if tw["p_upper"] < 0.001 else f"p = {tw['p_upper']:.3f}"
    rows.append(dict(check="Source collection", variant="type and region shuffled within source collection; collections of the parables' neighbours",
                     holds={2: "yes", 1: "partly", 0: "no"}[sum(checks_ok)], agreement=f"{sum(checks_ok)} of 2",
                     key_number=(f"type NMI {tw['observed']:.3f} against {tw['null_mean']:.3f} within collections ({p_txt}); "
                                 f"region {rw['observed']:.3f} against {rw['null_mean']:.3f}; at most {max_share:.0%} of a tradition's links go to one collection"),
                     source="results/collection_confound.csv; results/headline_by_tradition.csv"))

    # ---- 6 and 7: names and formulae masked; hubs removed (primary representation, recomputed here)
    masker = Masker(folk["text"].tolist() + queries["text"].tolist(), ctx.paper["masking"])
    space_m = build_space(rep, [masker.mask(t) for t in folk["text"]], ctx.cfg)
    Sm = space_m.sim(space_m.transform([masker.mask(t) for t in q["text"]]))
    space = build_space(rep, folk["text"].tolist(), ctx.cfg)
    S = space.sim(space.transform(q["text"].tolist()))
    hubs_tab = pd.read_csv(R / "checks_hubs.csv")
    hub_ids = hubs_tab[hubs_tab["rep"] == rep]["folktale_id"].tolist()
    pos = {f: i for i, f in enumerate(folk["id"])}
    S[:, [pos[h] for h in hub_ids if h in pos]] = -np.inf
    for label, check, variant_text, Sx, extra in (
            ("names and formulae masked", "Names and formulae masked", "names, collection and translator formulae masked (TF-IDF refitted)", Sm,
             None),
            ("hubs removed", "Hubness", f"the {len(hub_ids)} most frequent neighbours removed from the pool", S, None)):
        idx, val = nearest(Sx, k["attach_k"])
        x = val[:, :k["closeness_k"]].mean(axis=1)
        C, names = community_counts(idx, group)
        v = verdicts_from(headline_tests(x, C, is_par, trad, n_perm, n_boot, seed), names)
        record(f"{rep}, {label}", v)
        a, t_ = compare(base, v)
        same_top = sum(v[t]["top"] == base[t]["top"] for t in base if t in v and base[t]["where"])
        rows.append(dict(check=check, variant=variant_text, holds=verdict(a, t_), agreement=f"{a} of {t_}",
                         key_number=(f"closer than baseline: {names_of([t for t in TRADITIONS if v.get(t, {}).get('closer')])} (headline: {names_of(closer_base)}); "
                                     f"same top community for {same_top} of {len(where_base)} traditions whose profile differs"),
                         source="results/robustness_headline.csv"))

    det = pd.DataFrame(detail)
    tab = pd.DataFrame(rows)
    order = ["Edge construction", "Representation", "Length", "Noun masking", "Source collection", "Names and formulae masked", "Hubness"]
    tab = tab.set_index("check").loc[[o for o in order if o in set(tab["check"])]].reset_index()
    write_csv(det, R / "robustness_headline.csv")
    write_csv(tab, R / "table1_robustness.csv")
    for _, r in tab.iterrows():
        print(f"    {r['check']}: {r['holds']} ({r['agreement']}); {r['key_number']}")
    return dict(rows=len(tab))
