"""Stage `checks`: can the ranking be trusted, and does the tradition ranking survive?

  calibration    the 36 religious retellings as queries with a known answer (a folktale of the same
                 ATU type): recall@10 against the analytic chance rate; this is the 14 November gate
  second method  TF-IDF against embeddings: rank correlation of folk_closeness, overlap of neighbours
  length         folk_closeness against text length
  hubness        how often each folktale is a neighbour; ranking repeated without the 10 biggest hubs
  masking        ranking repeated with names and collection formulae replaced by a placeholder
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import skew, spearmanr

from .common import TRADITIONS, Ctx, write_csv, write_json
from .corpus import check_calibration_exclusion, load_corpus
from .headline import type_votes
from .part_b import folk_closeness, length_curve, load_map, nearest, scores, similarities
from .reps import Masker

# ----------------------------------------------------------------- calibration (pure functions)
def chance_recall(n_same: np.ndarray, n_total: int, k: int) -> np.ndarray:
    """P(at least one of `n_same` right answers among k folktales drawn at random from n_total):
    1 - C(N - n, k) / C(N, k)."""
    n_same = np.asarray(n_same, dtype=float)
    i = np.arange(k)[None, :]
    miss = np.prod(np.clip((n_total - n_same[:, None] - i) / (n_total - i), 0, None), axis=1)
    return 1.0 - miss


def first_hit_rank(S: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Rank (1 = nearest) of the first right answer in each row; `right` is a boolean matrix like S."""
    order = np.argsort(-np.round(S, 12), axis=1, kind="stable")
    hit = np.take_along_axis(right, order, axis=1)
    return np.where(hit.any(axis=1), hit.argmax(axis=1) + 1, S.shape[1] + 1)


def poisson_binomial_sf(p: np.ndarray, x: int) -> float:
    """P(X >= x) for a sum of independent Bernoulli(p_i): the chance of at least x hits."""
    dist = np.array([1.0])
    for pi in p:
        dist = np.convolve(dist, [1 - pi, pi])
    return float(dist[x:].sum())


def vote_chance(cal_atu: np.ndarray, folk_atu: np.ndarray, val: np.ndarray, n_draws: int, seed: int) -> tuple[float, float, float]:
    """Type-vote accuracy if each query's nearest folktales were drawn at random from the pool (the query keeps its
    own cosines, in rank order). Returns the mean over draws and the middle 95% of the draws."""
    rng = np.random.default_rng(seed)
    acc = np.empty(n_draws)
    n, k = len(folk_atu), val.shape[1]
    for d in range(n_draws):
        idx = np.stack([rng.choice(n, size=k, replace=False) for _ in range(len(cal_atu))])
        acc[d] = np.mean([v == a for v, a in zip(type_votes(idx, val, folk_atu), cal_atu)])
    return float(acc.mean()), float(np.quantile(acc, 0.025)), float(np.quantile(acc, 0.975))


def calibration(S_cal: np.ndarray, cal_atu: np.ndarray, folk_atu: np.ndarray, k: int, n_boot: int, seed: int):
    right = cal_atu[:, None] == folk_atu[None, :]
    ranks = first_hit_rank(S_cal, right)
    chance = chance_recall(right.sum(axis=1), S_cal.shape[1], k)
    hits = ranks <= k
    rng = np.random.default_rng(seed)
    boot = hits[rng.integers(0, len(hits), size=(n_boot, len(hits)))].mean(axis=1)
    summary = dict(queries=int(len(hits)), recall_at_1=float((ranks <= 1).mean()), recall_at_5=float((ranks <= 5).mean()),
                   recall_at_k=float(hits.mean()), k=k, ci_low=float(np.quantile(boot, 0.025)), ci_high=float(np.quantile(boot, 0.975)),
                   chance_at_k=float(chance.mean()), hits=int(hits.sum()), expected_hits_by_chance=float(chance.sum()),
                   p_value=poisson_binomial_sf(chance, int(hits.sum())), median_rank_of_first_right_answer=float(np.median(ranks)),
                   mean_reciprocal_rank=float((1.0 / ranks).mean()))
    return summary, ranks, chance


# ----------------------------------------------------------------- the checks
def ranking_of(queries: pd.DataFrame, closeness: np.ndarray, keep: np.ndarray | None = None) -> pd.DataFrame:
    rows = []
    for trad in TRADITIONS:
        m = ((queries["kind"] == "parable") & (queries["tradition"] == trad)).to_numpy()
        if keep is not None:
            m = m & keep
        if m.any():
            rows.append(dict(tradition=trad, n=int(m.sum()), median=float(np.median(closeness[m]))))
    out = pd.DataFrame(rows).sort_values("median", ascending=False)
    out["rank"] = np.arange(1, len(out) + 1)
    return out


def run(ctx: Ctx) -> dict:
    corpus = load_corpus(ctx)
    folk, queries = corpus.folk, corpus.queries(ctx)
    ck, pb = ctx.paper["checks"], ctx.paper["partB"]
    masker = Masker(folk["text"].tolist() + queries["text"].tolist(), ctx.paper["masking"])
    par = (queries["kind"] == "parable").to_numpy()
    cal = (queries["kind"] == "calibration").to_numpy()
    tokens = queries["n_tokens"].to_numpy()
    folk_atu = folk["atu_id"].fillna("").to_numpy(dtype=str)

    variants = {}                                   # name -> (similarities, scores)
    for rep in ctx.reps:
        for name, transform in ((rep, None), (f"{rep}_masked", masker.mask)):
            sim = similarities(ctx, rep, folk, queries, transform)
            variants[name] = (sim, scores(ctx, sim, folk))
            print(f"    computed {name}")

    # ---- calibration and the gate; first make sure the test is not circular
    for rep in ctx.reps:
        check_calibration_exclusion(folk["id"], queries.loc[cal, "id"], None, variants[rep][0]["S"][cal],
                                    float(ctx.paper["calibration_exclusion"]["max_cosine"]))
    cal_rows, per_query = [], queries.loc[cal, ["id", "title", "tradition", "atu_id", "n_tokens"]].reset_index(drop=True)
    S_cal = {name: sim["S"][cal] for name, (sim, _) in variants.items()}
    nm = ctx.work / "tfidf_nouns_masked.npz"                       # written by the vocab stage (step 4)
    if nm.exists():
        z = np.load(nm, allow_pickle=False)
        assert z["query_ids"].tolist() == queries["id"].tolist(), "rerun the vocab stage"
        S_cal["tfidf_nouns_masked"] = z["S_calibration"]
    cal_atu = queries.loc[cal, "atu_id"].to_numpy(dtype=str)
    folk_atu_obj = folk["atu_id"].to_numpy(dtype=object)
    for name, Sc in S_cal.items():
        s, ranks, chance = calibration(Sc, cal_atu, folk_atu, ck["recall_k"], ctx.shuffles(pb["bootstrap"], cap=1000), ctx.seed)
        idx10, val10 = nearest(Sc, ck["recall_k"])
        votes = type_votes(idx10, val10, folk_atu_obj)
        hit = np.array([v == a for v, a in zip(votes, cal_atu)])
        vc_mean, vc_lo, vc_hi = vote_chance(cal_atu, folk_atu_obj, val10, ctx.shuffles(ck["vote_chance_draws"]), ctx.seed)
        s.update(vote_accuracy=float(hit.mean()), vote_hits=int(hit.sum()), vote_chance=vc_mean,
                 vote_chance_low=vc_lo, vote_chance_high=vc_hi)
        cal_rows.append(dict(representation=name, **s))
        per_query[f"rank_{name}"] = ranks
        per_query[f"vote_{name}"] = votes
        per_query["chance_at_k"] = chance
        per_query["same_type_folktales"] = (queries.loc[cal, "atu_id"].to_numpy(dtype=str)[:, None] == folk_atu[None, :]).sum(axis=1)
    cal_tab = pd.DataFrame(cal_rows)
    write_csv(cal_tab, ctx.results / "calibration.csv")
    write_csv(per_query, ctx.results / "calibration_queries.csv")
    base = cal_tab[cal_tab["representation"].isin(ctx.reps)]
    ok = base[(base["ci_low"] > base["chance_at_k"]) & (base["p_value"] < 0.001)]
    gate = dict(passed=bool(len(ok)), rule="recall@10 of the 36 calibration versions is clearly above chance for at least one "
                "representation: the bootstrap 95% interval lies above the analytic chance rate and the chance of that many "
                "hits is below 0.001",
                representations_passing=ok["representation"].tolist(),
                recall_at_10={r.representation: r.recall_at_k for r in cal_tab.itertuples()},
                chance_at_10=float(cal_tab["chance_at_k"].iloc[0]))
    write_json(ctx.results / "gate.json", gate)
    print("    gate " + ("PASSED" if gate["passed"] else "FAILED") + ": recall@10 "
          + ", ".join(f"{r.representation} {r.recall_at_k:.2f}" for r in cal_tab.itertuples())
          + f"; chance {gate['chance_at_10']:.3f}. Type vote: "
          + ", ".join(f"{r.representation} {r.vote_accuracy:.2f}" for r in cal_tab.itertuples())
          + f"; chance {cal_tab['vote_chance'].iloc[0]:.3f}")

    # ---- second method
    a, b = ctx.reps[0], ctx.reps[1] if len(ctx.reps) > 1 else ctx.reps[0]
    ca, cb = variants[a][1], variants[b][1]
    jac = np.array([len(set(x) & set(y)) / len(set(x) | set(y)) for x, y in zip(ca["idx"][par], cb["idx"][par])])
    second = [dict(scope="all parables", n=int(par.sum()), spearman_folk_closeness=float(spearmanr(ca["closeness"][par], cb["closeness"][par])[0]),
                   mean_jaccard_top10=float(jac.mean()), share_with_no_shared_neighbour=float((jac == 0).mean()),
                   same_nearest_folktale=float((ca["idx"][par, 0] == cb["idx"][par, 0]).mean()))]
    for trad in TRADITIONS:
        m = par & (queries["tradition"] == trad).to_numpy()
        if m.sum() > 3:
            j = jac[m[par]]
            second.append(dict(scope=trad, n=int(m.sum()), spearman_folk_closeness=float(spearmanr(ca["closeness"][m], cb["closeness"][m])[0]),
                               mean_jaccard_top10=float(j.mean()), share_with_no_shared_neighbour=float((j == 0).mean()),
                               same_nearest_folktale=float((ca["idx"][m, 0] == cb["idx"][m, 0]).mean())))
    write_csv(pd.DataFrame(second).assign(representations=f"{a} vs {b}"), ctx.results / "checks_second_method.csv")

    # ---- length, hubness, and the tradition ranking under every variant
    length_rows, hub_rows, hub_list, rank_rows = [], [], [], []
    for rep in ctx.reps:
        sim, sc = variants[rep]
        group = load_map(ctx, rep, folk)
        for scope, x, y in (("parables", tokens[par], sc["closeness"][par]),
                            ("baseline passages", tokens[queries["kind"].to_numpy() == "baseline"], sc["closeness"][queries["kind"].to_numpy() == "baseline"]),
                            ("folktales (leave-one-out)", folk["n_tokens"].to_numpy(), sc["loo"])):
            if len(x) > 3:
                rho, p = spearmanr(x, y)
                length_rows.append(dict(rep=rep, scope=scope, n=len(x), spearman_closeness_vs_tokens=float(rho), p_value=float(p)))
        occ = np.bincount(sc["idx"][par].ravel(), minlength=len(folk))          # k-occurrence over all parable top-10 lists
        hubs = np.argsort(-occ, kind="stable")[:ck["hubs_removed"]]
        hub_rows.append(dict(rep=rep, parables=int(par.sum()), links=int(occ.sum()), folktales_never_a_neighbour=float((occ == 0).mean()),
                             max_occurrence=int(occ.max()), mean_occurrence=float(occ.mean()), skewness=float(skew(occ)),
                             share_of_links_to_top10_hubs=float(occ[hubs].sum() / max(occ.sum(), 1)),
                             expected_share_if_uniform=float(ck["hubs_removed"] / len(folk))))
        for r, f in enumerate(hubs):
            hub_list.append(dict(rep=rep, rank=r + 1, folktale_id=folk.at[f, "id"], title=folk.at[f, "title"], atu_id=folk.at[f, "atu_id"],
                                 community=f"C{group[f] + 1}" if group[f] >= 0 else "small", n_tokens=int(folk.at[f, "n_tokens"]),
                                 times_a_neighbour=int(occ[f]), share_of_parables=float(occ[f] / max(par.sum(), 1))))
        S_nohub = sim["S"].copy()
        S_nohub[:, hubs] = -np.inf
        expected = length_curve(folk["n_tokens"].to_numpy(), sc["loo"])
        named = {"as reported": (sc["closeness"], None),
                 "names and formulae masked": (variants[f"{rep}_masked"][1]["closeness"], None),
                 f"without the {ck['hubs_removed']} most frequent neighbours": (folk_closeness(S_nohub, pb["closeness_k"]), None),
                 f"parables of at least {ck['long_parable_tokens']} tokens": (sc["closeness"], tokens >= ck["long_parable_tokens"]),
                 "minus folktales of the same length": (sc["closeness"] - expected(tokens), None),
                 "nearest folktale only (k = 1)": (sc["val"][:, 0], None),
                 "10 nearest folktales (k = 10)": (sc["val"].mean(axis=1), None)}
        for name, (values, keep) in named.items():
            t = ranking_of(queries, values, keep)
            rank_rows += [dict(rep=rep, variant=name, **r) for r in t.to_dict("records")]
        m = spearmanr(sc["closeness"][par], variants[f"{rep}_masked"][1]["closeness"][par])[0]
        length_rows.append(dict(rep=rep, scope="parables: masked against unmasked folk_closeness", n=int(par.sum()),
                                spearman_closeness_vs_tokens=float(m), p_value=np.nan))
    write_csv(pd.DataFrame(length_rows), ctx.results / "checks_length.csv")
    write_csv(pd.DataFrame(hub_rows), ctx.results / "checks_hubness.csv")
    write_csv(pd.DataFrame(hub_list), ctx.results / "checks_hubs.csv")
    write_csv(pd.DataFrame(rank_rows), ctx.results / "checks_ranking_variants.csv")
    write_json(ctx.results / "checks_masking.json", dict(
        name_like_words=len(masker.names), formulae=ctx.paper["masking"]["formulae"], placeholder=masker.placeholder,
        share_of_tokens_masked=float(np.mean([masker.masked_share(t) for t in queries.loc[par, "text"]])),
        share_of_tokens_masked_by_tradition={t: float(np.mean([masker.masked_share(x) for x in queries.loc[par & (queries["tradition"] == t).to_numpy(), "text"]]))
                                             for t in TRADITIONS if (par & (queries["tradition"] == t).to_numpy()).any()},
        share_of_tokens_masked_folktales=float(np.mean([masker.masked_share(t) for t in folk["text"]]))))

    return gate
