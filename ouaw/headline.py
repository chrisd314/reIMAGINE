"""Stage `headline`: the main result of the paper (TA feedback, step 2).

    Do parables from different religious traditions sit inside folktale communities more than non-story
    text from the same translations does, and which folktale communities and tale types do they land in?

For each tradition and each variant (TF-IDF, embeddings, and the noun-masked TF-IDF of step 4), the
parables are compared with the baseline passages cut from the same translations. Every test shuffles the
parable/baseline label *within the tradition*, with the text as the unit (1,000 shuffles):

  closeness  median folk-closeness of the parables minus that of the baseline; one-sided permutation p
             (parables closer) and a bootstrap 95% interval over texts
  profile    where a text's 10 nearest folktales sit among the canonical Louvain communities; parable share
             minus baseline share per community (two-sided p), and the Jensen-Shannon divergence of the two
             profiles against the same shuffles
  inside     share of parables above the 95th percentile of their own baseline ("inside folklore")
  types      the ATU type voted by each text's 10 nearest folktales (largest summed cosine); the 5 most
             common per tradition, for parables and for the baseline
  collection which source collection a tradition's nearest folktales come from (step 6)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import TRADITIONS, Ctx, permute_within, write_csv
from .corpus import load_corpus
from .part_b import bootstrap_median, jsd_bits

COMMUNITY_VARIANT_MAP = {"tfidf": "tfidf", "embedding": "embedding", "tfidf_nouns_masked": "tfidf"}
VARIANT_NAME = {"tfidf": "TF-IDF", "embedding": "embeddings", "tfidf_nouns_masked": "TF-IDF, nouns masked"}


# ----------------------------------------------------------------- pure functions
def community_counts(idx: np.ndarray, group: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """Links per community for each text: idx (texts x k) holds folktale indices; group[f] is the community of
    folktale f (-1 = the small communities, reported together). Returns counts (texts x K) and community names."""
    labels = sorted(set(group.tolist()) - {-1}) + ([-1] if (group == -1).any() else [])
    code = np.full(int(group.max()) + 2, -1)
    for k, g in enumerate(labels):
        code[g] = k                                   # code[-1] is the last slot, used for group -1
    gi = code[group]
    C = np.stack([(gi[idx] == k).sum(axis=1) for k in range(len(labels))], axis=1)
    return C, [f"C{g + 1}" if g >= 0 else "small" for g in labels]


def type_votes(idx: np.ndarray, val: np.ndarray, folk_atu) -> np.ndarray:
    """ATU type with the largest summed cosine among each text's nearest folktales; ties go to the type met first
    (that is, the type of the nearer folktale). Folktales without a type do not vote. None if no neighbour has one."""
    out = np.empty(len(idx), dtype=object)
    for q in range(len(idx)):
        score: dict[str, float] = {}
        for f, v in zip(idx[q], val[q]):
            a = folk_atu[f]
            if isinstance(a, str) and a:
                score[a] = score.get(a, 0.0) + float(v)
        out[q] = max(score, key=lambda a: score[a]) if score else None        # dict order = first met, max keeps it
    return out


def profile(C: np.ndarray) -> np.ndarray:
    """Share of all links (rows of C) that end in each community."""
    tot = C.sum(axis=0).astype(float)
    return tot / max(tot.sum(), 1e-12)


def tradition_stats(x: np.ndarray, C: np.ndarray, is_par: np.ndarray) -> tuple[float, np.ndarray, float, float]:
    """Median difference, profile excess, JSD of the profiles and inside share for one tradition's texts."""
    xp, xb = x[is_par], x[~is_par]
    p, b = profile(C[is_par]), profile(C[~is_par])
    return (float(np.median(xp) - np.median(xb)), p - b, jsd_bits(p, b),
            float((xp > np.quantile(xb, 0.95)).mean()))


def headline_tests(x: np.ndarray, C: np.ndarray, is_par: np.ndarray, tradition: np.ndarray, n_perm: int,
                   n_boot: int, seed: int) -> dict:
    """All headline statistics per tradition, with a null that shuffles the parable/baseline label within each
    tradition (`permute_within`) and bootstrap intervals that resample parables and baseline passages separately."""
    trads = [t for t in pd.unique(tradition) if (is_par & (tradition == t)).any() and (~is_par & (tradition == t)).any()]
    rows = {t: np.flatnonzero(tradition == t) for t in trads}
    obs = {t: tradition_stats(x[r], C[r], is_par[r]) for t, r in rows.items()}
    rng = np.random.default_rng(seed)
    null = {t: [] for t in trads}
    for _ in range(n_perm):
        lab = is_par[permute_within(tradition, rng)]
        for t, r in rows.items():
            null[t].append(tradition_stats(x[r], C[r], lab[r]))
    out = {}
    for t, r in rows.items():
        d, ex, js, ins = obs[t]
        nd = np.array([v[0] for v in null[t]])
        nex = np.stack([v[1] for v in null[t]])
        njs = np.array([v[2] for v in null[t]])
        nins = np.array([v[3] for v in null[t]])
        N = len(nd)
        brng = np.random.default_rng([seed, len(out)])
        xp, xb = x[r][is_par[r]], x[r][~is_par[r]]
        Cp, Cb = C[r][is_par[r]], C[r][~is_par[r]]
        bd = bootstrap_median(xp, n_boot, brng) - bootstrap_median(xb, n_boot, brng)
        bp = Cp[brng.integers(0, len(Cp), size=(n_boot, len(Cp)))].sum(axis=1).astype(float)
        bb = Cb[brng.integers(0, len(Cb), size=(n_boot, len(Cb)))].sum(axis=1).astype(float)
        bex = bp / bp.sum(axis=1, keepdims=True) - bb / bb.sum(axis=1, keepdims=True)
        out[t] = dict(
            n_parables=int(len(xp)), n_baseline=int(len(xb)), parable_median=float(np.median(xp)),
            baseline_median=float(np.median(xb)), diff=d, diff_ci_low=float(np.quantile(bd, 0.025)),
            diff_ci_high=float(np.quantile(bd, 0.975)), diff_null_sd=float(nd.std(ddof=1)) if N > 1 else np.nan,
            diff_p_upper=float((1 + (nd >= d).sum()) / (1 + N)),
            diff_p_two_sided=float((1 + (np.abs(nd) >= abs(d)).sum()) / (1 + N)),
            parable_profile=profile(Cp), baseline_profile=profile(Cb), excess=ex,
            excess_ci_low=np.quantile(bex, 0.025, axis=0), excess_ci_high=np.quantile(bex, 0.975, axis=0),
            excess_p=(1 + (np.abs(nex) >= np.abs(ex)[None, :]).sum(axis=0)) / (1 + N),
            jsd=js, jsd_null_mean=float(njs.mean()), jsd_p_upper=float((1 + (njs >= js).sum()) / (1 + N)),
            inside=ins, inside_null_mean=float(nins.mean()), inside_p_upper=float((1 + (nins >= ins).sum()) / (1 + N)),
            permutations=N, bootstrap=n_boot)
    return out


def top_types(votes: np.ndarray, atu_name: dict, top: int = 5) -> list[dict]:
    v = pd.Series([x for x in votes if x is not None], dtype=object)
    n = len(votes)
    return [dict(rank=k + 1, atu_id=a, atu_name=atu_name.get(a, ""), texts=int(c), share=c / n)
            for k, (a, c) in enumerate(v.value_counts().head(top).items())]


def collection_share(idx: np.ndarray, folk_collection: np.ndarray) -> pd.Series:
    """Share of links (with a known source collection) per collection, largest first."""
    c = pd.Series(folk_collection[idx.ravel()]).dropna()
    return c.value_counts(normalize=True)


# ----------------------------------------------------------------- the stage
def neighbours(ctx: Ctx, variant: str, queries: pd.DataFrame) -> dict | None:
    """Nearest folktales of every query for one variant (written by partB, or by the vocab stage)."""
    path = ctx.work / (f"partB_{variant}.npz" if variant in ctx.reps else f"{variant}.npz")
    if not path.exists():
        return None
    z = np.load(path, allow_pickle=False)
    assert z["query_ids"].tolist() == queries["id"].tolist(), f"{path.name} does not match the queries; rerun the stage that writes it"
    return dict(idx=z["idx"], val=z["val"], closeness=z["closeness"])


def variants(ctx: Ctx) -> list[str]:
    return list(ctx.reps) + ["tfidf_nouns_masked"]


def run(ctx: Ctx) -> dict:
    corpus = load_corpus(ctx)
    folk, queries = corpus.folk, corpus.queries(ctx)
    sel = queries["kind"].isin(["parable", "baseline"]).to_numpy()
    q = queries[sel].reset_index(drop=True)
    is_par = (q["kind"] == "parable").to_numpy()
    trad = q["tradition"].to_numpy()
    comm = pd.read_csv(ctx.results / "partA_communities.csv")
    atu_name = folk.dropna(subset=["atu_id"]).drop_duplicates("atu_id").set_index("atu_id")["atu_name"].to_dict()
    folk_atu = folk["atu_id"].to_numpy(dtype=object)
    folk_coll = folk["source_collection"].to_numpy(dtype=object)
    map_coll = folk["source_collection"].dropna().value_counts(normalize=True)
    n_perm = ctx.shuffles(ctx.paper["headline"]["permutations"])
    n_boot = ctx.shuffles(ctx.paper["partB"]["bootstrap"], cap=1000)

    by_trad, cells, types, per_text = [], [], [], []
    for variant in variants(ctx):
        nb = neighbours(ctx, variant, queries)
        if nb is None:
            print(f"    {variant}: no neighbours yet (stage vocab writes them); skipped")
            continue
        rep = COMMUNITY_VARIANT_MAP[variant]
        z = np.load(ctx.work / f"map_{rep}.npz", allow_pickle=False)
        assert z["ids"].tolist() == folk["id"].tolist(), "run partA first"
        group = z["group"]
        idx, val, x = nb["idx"][sel], nb["val"][sel], nb["closeness"][sel]
        C, names = community_counts(idx, group)
        words = comm[comm["rep"] == rep].set_index("community")["top_words"].astype(str).to_dict()
        map_share = {nm: float(np.mean([("small" if g < 0 else f"C{g + 1}") == nm for g in group])) for nm in names}
        res = headline_tests(x, C, is_par, trad, n_perm, n_boot, ctx.paper["headline"]["seed"])
        votes = type_votes(idx, val, folk_atu)
        n_cells = len(res) * len(names)
        for t in [t for t in TRADITIONS if t in res]:
            r = res[t]
            rows = np.flatnonzero(trad == t)
            for k, nm in enumerate(names):
                cells.append(dict(variant=variant, rep=rep, tradition=t, community=nm, community_words=" ".join(words.get(nm, "").split()[:8]),
                                  map_share=map_share[nm], parable_share=r["parable_profile"][k], baseline_share=r["baseline_profile"][k],
                                  excess=r["excess"][k], excess_ci_low=r["excess_ci_low"][k], excess_ci_high=r["excess_ci_high"][k],
                                  p_two_sided=r["excess_p"][k], significant_05=bool(r["excess_p"][k] < 0.05),
                                  significant_bonferroni=bool(r["excess_p"][k] < 0.05 / n_cells), cells_in_correction=n_cells,
                                  permutations=r["permutations"]))
            k_top = int(np.argmax(r["excess"]))
            tops = {}
            for kind, m in (("parable", is_par[rows]), ("baseline", ~is_par[rows])):
                tt = top_types(votes[rows][m], atu_name)
                tops[kind] = tt
                types += [dict(variant=variant, tradition=t, kind=kind, n_texts=int(m.sum()), **x_) for x_ in tt]
            cs_par = collection_share(idx[rows][is_par[rows]], folk_coll)
            cs_base = collection_share(idx[rows][~is_par[rows]], folk_coll)
            top_c = cs_par.index[0] if len(cs_par) else None
            fmt_t = lambda tt: "; ".join(f"{d['atu_id']} {d['atu_name']} ({d['share']:.0%})" for d in tt[:3])
            by_trad.append(dict(
                variant=variant, rep=rep, tradition=t, n_parables=r["n_parables"], n_baseline=r["n_baseline"],
                parable_tokens_median=float(q.loc[rows[is_par[rows]], "n_tokens"].median()),
                baseline_tokens_median=float(q.loc[rows[~is_par[rows]], "n_tokens"].median()),
                parable_median=r["parable_median"], baseline_median=r["baseline_median"], diff=r["diff"],
                diff_ci_low=r["diff_ci_low"], diff_ci_high=r["diff_ci_high"], diff_p_upper=r["diff_p_upper"],
                diff_p_two_sided=r["diff_p_two_sided"], closer_than_baseline=bool(r["diff_p_upper"] < 0.05),
                inside_share=r["inside"], inside_null_mean=r["inside_null_mean"], inside_p_upper=r["inside_p_upper"],
                jsd_bits=r["jsd"], jsd_null_mean=r["jsd_null_mean"], jsd_p_upper=r["jsd_p_upper"],
                profile_differs=bool(r["jsd_p_upper"] < 0.05),
                top_excess_community=names[k_top], top_excess_community_words=" ".join(words.get(names[k_top], "").split()[:3]),
                top_excess=r["excess"][k_top], top_excess_p=r["excess_p"][k_top],
                top_excess_significant_bonferroni=bool(r["excess_p"][k_top] < 0.05 / n_cells),
                parable_top_types=fmt_t(tops["parable"]), baseline_top_types=fmt_t(tops["baseline"]),
                top_source_collection=top_c, top_source_collection_share=float(cs_par.iloc[0]) if top_c else np.nan,
                top_source_collection_map_share=float(map_coll.get(top_c, 0.0)) if top_c else np.nan,
                top_source_collection_baseline_share=float(cs_base.get(top_c, 0.0)) if top_c else np.nan,
                permutations=r["permutations"], bootstrap=r["bootstrap"]))
        for i in range(len(q)):
            per_text.append(dict(variant=variant, id=q.at[i, "id"], kind=q.at[i, "kind"], tradition=q.at[i, "tradition"],
                                 folk_closeness=x[i], voted_atu=votes[i], voted_atu_name=atu_name.get(votes[i], "") if votes[i] else "",
                                 modal_community=names[int(np.argmax(C[i]))]))
        b = [d for d in by_trad if d["variant"] == variant]
        print(f"    {variant}: parables minus baseline (permutation p): "
              + "; ".join(f"{d['tradition']} {d['diff']:+.3f} (p={d['diff_p_upper']:.3f})" for d in b))

    write_csv(pd.DataFrame(by_trad), ctx.results / "headline_by_tradition.csv")
    write_csv(pd.DataFrame(cells), ctx.results / "headline_community_excess.csv")
    write_csv(pd.DataFrame(types), ctx.results / "headline_atu_by_tradition.csv")
    write_csv(pd.DataFrame(per_text), ctx.results / "headline_texts.csv")
    return dict(variants=sorted({d["variant"] for d in by_trad}))
