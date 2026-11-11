"""Stage `partB`: parables on the map.

For each representation, every parable, baseline passage and calibration version is compared with
all folktales. The map itself (Part A) is never changed.
  rank     folk_closeness = mean cosine of the 5 nearest folktales; parables and traditions ranked by it
  scale    the same quantity for every folktale against the other folktales (leave-one-out), and for
           non-story passages of the same translations
  attach   each parable is linked to its 10 nearest folktales; per tradition, the share of links in
           each folklore community against 1,000 shuffles of the community labels
  words    distinctive words of the closest against the farthest quarter of each tradition's parables
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from .common import TRADITIONS, Ctx, summarise_null, top_k, write_csv, write_json
from .corpus import load_corpus
from .part_a import FRAGMENTS, count_matrix
from .reps import build_space


# ----------------------------------------------------------------- core quantities (pure functions)
def nearest(S: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Indices and cosines of the k most similar folktales per row (ties: lower index first)."""
    idx = top_k(S, k)
    return idx, np.take_along_axis(S, idx, axis=1)


def folk_closeness(S: np.ndarray, k: int = 5) -> np.ndarray:
    """Mean cosine of the k nearest folktales, per row of a query x folktale similarity matrix."""
    return nearest(S, k)[1].mean(axis=1)


def leave_one_out(S_ff: np.ndarray, k: int, exclude: np.ndarray | None = None) -> np.ndarray:
    """folk_closeness of each folktale to the other folktales (`exclude` masks further candidates)."""
    M = S_ff.copy()
    np.fill_diagonal(M, -np.inf)
    if exclude is not None:
        M[exclude] = -np.inf
    return folk_closeness(M, k)


def bootstrap_median(x: np.ndarray, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    return np.median(x[rng.integers(0, len(x), size=(n_boot, len(x)))], axis=1)


def entropy_bits(counts: np.ndarray) -> np.ndarray:
    """Shannon entropy (bits) of each row of counts."""
    c = np.atleast_2d(counts).astype(float)
    p = c / np.maximum(c.sum(axis=1, keepdims=True), 1e-12)
    with np.errstate(divide="ignore", invalid="ignore"):
        return -np.where(p > 0, p * np.log2(p), 0.0).sum(axis=1)


def placement_null(attach: np.ndarray, groups: np.ndarray, n_groups: int, n_shuffles: int, seed: int) -> np.ndarray:
    """Links per group under shuffles of the group labels over folktales (group sizes kept).

    `attach[f]` = number of links that end at folktale f. Returns an array (n_shuffles, n_groups).
    """
    rng = np.random.default_rng(seed)
    out = np.empty((n_shuffles, n_groups))
    for s in range(n_shuffles):
        out[s] = np.bincount(rng.permutation(groups), weights=attach, minlength=n_groups)
    return out


def jsd_bits(p: np.ndarray, q: np.ndarray) -> float:
    """Jensen-Shannon divergence (bits) between two count or share vectors; 0 = same, 1 = disjoint."""
    p, q = p / p.sum(), q / q.sum()
    m = (p + q) / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        kl_p = np.where(p > 0, p * np.log2(p / m), 0.0).sum()
        kl_q = np.where(q > 0, q * np.log2(q / m), 0.0).sum()
    return float((kl_p + kl_q) / 2)


def log_odds(a: np.ndarray, b: np.ndarray, prior: float) -> np.ndarray:
    """z-scores of the log-odds ratio of word use in group a against group b (Dirichlet prior from both)."""
    alpha = prior * (a + b) + prior
    da = np.log((a + alpha) / (a.sum() + alpha.sum() - a - alpha))
    db = np.log((b + alpha) / (b.sum() + alpha.sum() - b - alpha))
    return (da - db) / np.sqrt(1.0 / (a + alpha) + 1.0 / (b + alpha))


def length_curve(tokens: np.ndarray, values: np.ndarray, bins: int = 15):
    """Median of `values` by length, as a function: medians in quantile bins of log length, interpolated."""
    x = np.log(np.maximum(tokens, 1))
    edges = np.unique(np.quantile(x, np.linspace(0, 1, bins + 1)))
    which = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2)
    xs = np.array([x[which == b].mean() for b in range(len(edges) - 1) if (which == b).any()])
    ys = np.array([np.median(values[which == b]) for b in range(len(edges) - 1) if (which == b).any()])
    return lambda t: np.interp(np.log(np.maximum(t, 1)), xs, ys)


# ----------------------------------------------------------------- one representation
def similarities(ctx: Ctx, rep: str, folk: pd.DataFrame, queries: pd.DataFrame, transform=None) -> dict:
    """Query x folktale and folktale x folktale cosines; `transform` (masking) is applied to every text first."""
    t = transform or (lambda s: s)
    space = build_space(rep, [t(x) for x in folk["text"]], ctx.cfg)
    return dict(S=space.sim(space.transform([t(x) for x in queries["text"]])), S_ff=space.folk_sim(), space=space)


def scores(ctx: Ctx, sim: dict, folk: pd.DataFrame) -> dict:
    """Nearest folktales and folk_closeness for the queries, and the leave-one-out values of the folktales."""
    pb = ctx.paper["partB"]
    idx, val = nearest(sim["S"], pb["attach_k"])
    atu = folk["atu_id"].to_numpy(dtype=object)
    same_type = (atu[:, None] == atu[None, :]) & pd.notna(atu)[:, None]
    return dict(idx=idx, val=val, closeness=val[:, :pb["closeness_k"]].mean(axis=1),
                loo=leave_one_out(sim["S_ff"], pb["closeness_k"]),
                loo_other_types=leave_one_out(sim["S_ff"], pb["closeness_k"], exclude=same_type))


def tradition_table(ctx: Ctx, rep: str, queries: pd.DataFrame, sc: dict, folk: pd.DataFrame) -> pd.DataFrame:
    pb = ctx.paper["partB"]
    rng = np.random.default_rng(ctx.seed)
    n_boot = ctx.shuffles(pb["bootstrap"], cap=1000)
    loo, loo_x = sc["loo"], sc["loo_other_types"]
    expected = length_curve(folk["n_tokens"].to_numpy(), loo)
    adj = sc["closeness"] - expected(queries["n_tokens"].to_numpy())
    rows = []
    for trad in TRADITIONS:
        par = ((queries["kind"] == "parable") & (queries["tradition"] == trad)).to_numpy()
        base = ((queries["kind"] == "baseline") & (queries["tradition"] == trad)).to_numpy()
        if not par.any():
            continue
        x, b = sc["closeness"][par], sc["closeness"][base]
        bx = bootstrap_median(x, n_boot, rng)
        row = dict(rep=rep, tradition=trad, n_parables=int(par.sum()), median=float(np.median(x)),
                   ci_low=float(np.quantile(bx, 0.025)), ci_high=float(np.quantile(bx, 0.975)),
                   q25=float(np.quantile(x, 0.25)), q75=float(np.quantile(x, 0.75)),
                   folktale_median=float(np.median(loo)), minus_folktale_median=float(np.median(x) - np.median(loo)),
                   percentile_among_folktales=float(100 * (loo < np.median(x)).mean()),
                   share_above_folktale_q25=float((x > np.quantile(loo, 0.25)).mean()),
                   folktale_other_types_median=float(np.median(loo_x)),
                   percentile_among_folktales_other_types=float(100 * (loo_x < np.median(x)).mean()),
                   median_minus_folktales_of_same_length=float(np.median(adj[par])),
                   tokens_median=float(queries.loc[par, "n_tokens"].median()))
        if base.any():
            bb = bootstrap_median(b, n_boot, rng)
            diff = bx - bb
            row.update(n_baseline=int(base.sum()), baseline_median=float(np.median(b)),
                       baseline_ci_low=float(np.quantile(bb, 0.025)), baseline_ci_high=float(np.quantile(bb, 0.975)),
                       baseline_q95=float(np.quantile(b, 0.95)), minus_baseline_median=float(np.median(x) - np.median(b)),
                       minus_baseline_ci_low=float(np.quantile(diff, 0.025)), minus_baseline_ci_high=float(np.quantile(diff, 0.975)),
                       share_above_baseline_median=float((x > np.median(b)).mean()),
                       share_above_baseline_q95=float((x > np.quantile(b, 0.95)).mean()),
                       baseline_tokens_median=float(queries.loc[base, "n_tokens"].median()))
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("median", ascending=False).reset_index(drop=True)
    out.insert(2, "rank", np.arange(1, len(out) + 1))
    return out


def attachment(ctx: Ctx, rep: str, queries: pd.DataFrame, sc: dict, group: np.ndarray):
    """Share of each tradition's links per folklore community, against shuffles of the community labels."""
    pb = ctx.paper["partB"]
    n_shuf = ctx.shuffles(pb["placement_shuffles"])
    labels = sorted(set(group.tolist()) - {-1}) + ([-1] if (group == -1).any() else [])
    code = {g: k for k, g in enumerate(labels)}
    names = [f"C{g + 1}" if g >= 0 else "small" for g in labels]
    gi = np.array([code[g] for g in group])
    K, nf = len(labels), len(group)
    size_share = np.bincount(gi, minlength=K) / nf
    par = (queries["kind"] == "parable").to_numpy()
    comm_of_links = gi[sc["idx"]]                                           # (queries, k)
    per_parable = np.stack([(comm_of_links == c).sum(axis=1) for c in range(K)], axis=1)   # links per community

    cells, trads, counts = [], [], {}
    for t, trad in enumerate(TRADITIONS):
        rows = np.flatnonzero(par & (queries["tradition"] == trad).to_numpy())
        if not len(rows):
            continue
        attach = np.bincount(sc["idx"][rows].ravel(), minlength=nf).astype(float)
        obs = np.bincount(gi, weights=attach, minlength=K)
        counts[trad] = per_parable[rows]
        null = placement_null(attach, gi, K, n_shuf, pb["placement_seed"] + t)
        total = obs.sum()
        modal = np.bincount(per_parable[rows].argmax(axis=1), minlength=K) / len(rows)
        for c in range(K):
            dev = np.abs(null[:, c] - null[:, c].mean())
            p2 = (1 + (dev >= abs(obs[c] - null[:, c].mean())).sum()) / (1 + n_shuf)
            sd = null[:, c].std(ddof=1) / total
            cells.append(dict(rep=rep, tradition=trad, community=names[c], community_share_of_folktales=size_share[c],
                              links=int(obs[c]), share=obs[c] / total, expected_share=null[:, c].mean() / total,
                              share_minus_expected=(obs[c] - null[:, c].mean()) / total, null_sd=sd,
                              z=(obs[c] - null[:, c].mean()) / total / sd if sd > 0 else np.nan, p_two_sided=p2,
                              parables_with_this_modal_community=modal[c]))
        h_null = entropy_bits(null)
        h = summarise_null(float(entropy_bits(obs)[0]), h_null)
        trads.append(dict(rep=rep, tradition=trad, parables=len(rows), links=int(total), entropy_bits=h["observed"],
                          entropy_max_bits=float(np.log2(K)), null_mean=h["null_mean"], null_sd=h["null_sd"], z=h["z"],
                          p_lower=float((1 + (h_null <= h["observed"]).sum()) / (1 + n_shuf)), shuffles=n_shuf,
                          top_community=names[int(obs.argmax())], top_share=float(obs.max() / total)))
    cells = pd.DataFrame(cells)
    if len(cells):
        m = len(cells)
        cells["significant_05"] = cells["p_two_sided"] < 0.05
        cells["significant_bonferroni"] = cells["p_two_sided"] < 0.05 / m

    # do traditions land in the same communities? parable = unit; tradition labels shuffled over parables
    pairs = []
    have = [t for t in TRADITIONS if t in counts]
    if len(have) > 1:
        allc = np.vstack([counts[t] for t in have])
        owner = np.concatenate([np.full(len(counts[t]), k) for k, t in enumerate(have)])
        rng = np.random.default_rng(pb["placement_seed"] + 100)
        def pair_jsd(own):
            tot = np.stack([allc[own == k].sum(axis=0) for k in range(len(have))])
            return np.array([jsd_bits(tot[a], tot[b]) for a, b in itertools.combinations(range(len(have)), 2)])
        obs = pair_jsd(owner)
        null = np.stack([pair_jsd(rng.permutation(owner)) for _ in range(n_shuf)])
        for k, (a, b) in enumerate(itertools.combinations(range(len(have)), 2)):
            s = summarise_null(obs[k], null[:, k])
            pairs.append(dict(rep=rep, tradition_a=have[a], tradition_b=have[b], jsd_bits=obs[k], null_mean=s["null_mean"],
                              null_sd=s["null_sd"], z=s["z"], p_upper=s["p_upper"], shuffles=n_shuf))
        s = summarise_null(obs.mean(), null.mean(axis=1))
        pairs.append(dict(rep=rep, tradition_a="all pairs (mean)", tradition_b="", jsd_bits=obs.mean(), null_mean=s["null_mean"],
                          null_sd=s["null_sd"], z=s["z"], p_upper=s["p_upper"], shuffles=n_shuf))
    return cells, pd.DataFrame(trads), pd.DataFrame(pairs)


def distinctive_words(ctx: Ctx, rep: str, queries: pd.DataFrame, closeness: np.ndarray) -> pd.DataFrame:
    d = ctx.paper["partB"]["distinctive"]
    rows = []
    for trad in TRADITIONS:
        sel = np.flatnonzero(((queries["kind"] == "parable") & (queries["tradition"] == trad)).to_numpy())
        if len(sel) < 8:
            continue
        order = sel[np.argsort(-closeness[sel], kind="stable")]
        q = max(2, int(round(d["quantile"] * len(sel))))
        X, vocab = count_matrix(queries.loc[sel, "text"].tolist(), ctx.cfg["lexical"], extra_stop=FRAGMENTS, min_df=2)
        pos = {i: k for k, i in enumerate(sel)}
        a = np.asarray(X[[pos[i] for i in order[:q]]].sum(axis=0)).ravel().astype(float)
        b = np.asarray(X[[pos[i] for i in order[-q:]]].sum(axis=0)).ravel().astype(float)
        z = log_odds(a, b, d["prior"])
        rows.append(dict(rep=rep, tradition=trad, parables_per_group=q,
                         closest_quarter=" ".join(vocab[np.argsort(-z)[:d["top"]]]),
                         farthest_quarter=" ".join(vocab[np.argsort(z)[:d["top"]]])))
    return pd.DataFrame(rows)


def load_map(ctx: Ctx, rep: str, folk: pd.DataFrame) -> np.ndarray:
    z = np.load(ctx.work / f"map_{rep}.npz", allow_pickle=False)
    assert z["ids"].tolist() == folk["id"].tolist(), "run partA first (the map does not match the folktales)"
    return z["group"]


def run(ctx: Ctx) -> dict:
    corpus = load_corpus(ctx)
    folk, queries = corpus.folk, corpus.queries(ctx)
    pb = ctx.paper["partB"]
    rank_rows, nb_rows, trad_tabs, cell_tabs, ent_tabs, pair_tabs, word_tabs, folk_rows = [], [], [], [], [], [], [], []
    for rep in ctx.reps:
        sim = similarities(ctx, rep, folk, queries)
        sc = scores(ctx, sim, folk)
        group = load_map(ctx, rep, folk)
        comm = np.array([f"C{g + 1}" if g >= 0 else "small" for g in group])
        np.savez_compressed(ctx.work / f"partB_{rep}.npz", query_ids=queries["id"].to_numpy(dtype=str), idx=sc["idx"],
                            val=sc["val"], closeness=sc["closeness"], loo=sc["loo"], loo_other_types=sc["loo_other_types"])
        expected = length_curve(folk["n_tokens"].to_numpy(), sc["loo"])
        is_par = (queries["kind"] == "parable").to_numpy()
        rank = np.full(len(queries), np.nan)
        rank[is_par] = (-sc["closeness"][is_par]).argsort(kind="stable").argsort() + 1
        for q in range(len(queries)):
            r = queries.iloc[q]
            i = sc["idx"][q]
            rank_rows.append(dict(
                rep=rep, id=r["id"], kind=r["kind"], tradition=r["tradition"], title=r["title"], n_tokens=r["n_tokens"],
                folk_closeness=sc["closeness"][q], rank_among_parables=rank[q],
                minus_folktales_of_same_length=sc["closeness"][q] - float(expected(r["n_tokens"])),
                nearest_id=folk.at[i[0], "id"], nearest_title=folk.at[i[0], "title"], nearest_atu=folk.at[i[0], "atu_id"],
                nearest_cosine=sc["val"][q, 0], modal_community=pd.Series(comm[i]).mode().iat[0],
                nearest_10_ids=";".join(folk["id"].to_numpy()[i]), nearest_10_cosines=";".join(f"{v:.4f}" for v in sc["val"][q])))
            for k in range(len(i)):
                nb_rows.append(dict(rep=rep, id=r["id"], kind=r["kind"], tradition=r["tradition"], rank=k + 1,
                                    folktale_id=folk.at[i[k], "id"], folktale_title=folk.at[i[k], "title"],
                                    folktale_atu=folk.at[i[k], "atu_id"], community=comm[i[k]], cosine=sc["val"][q, k]))
        for name, v in (("all other folktales", sc["loo"]), ("other folktales of a different tale type", sc["loo_other_types"])):
            folk_rows.append(dict(rep=rep, candidates=name, n=len(v), **{f"q{int(p * 100):02d}": float(np.quantile(v, p))
                                                                      for p in (0.05, 0.25, 0.5, 0.75, 0.95)}))
        trad_tabs.append(tradition_table(ctx, rep, queries, sc, folk))
        cells, ent, pairs = attachment(ctx, rep, queries, sc, group)
        cell_tabs.append(cells); ent_tabs.append(ent); pair_tabs.append(pairs)
        word_tabs.append(distinctive_words(ctx, rep, queries, sc["closeness"]))
        t = trad_tabs[-1]
        print(f"    {rep}: folktale leave-one-out median {np.median(sc['loo']):.3f}; traditions by median folk_closeness: "
              + ", ".join(f"{r.tradition} {r['median']:.3f}" for _, r in t.iterrows()))

    ranking = pd.DataFrame(rank_rows).sort_values(["rep", "kind", "folk_closeness"], ascending=[True, True, False])
    write_csv(ranking, ctx.results / "partB_ranking.csv")
    write_csv(pd.DataFrame(nb_rows), ctx.results / "partB_neighbours.csv")
    write_csv(pd.concat(trad_tabs, ignore_index=True), ctx.results / "partB_traditions.csv")
    write_csv(pd.DataFrame(folk_rows), ctx.results / "partB_folktale_baseline.csv")
    write_csv(pd.concat(cell_tabs, ignore_index=True), ctx.results / "partB_attachment.csv")
    write_csv(pd.concat(ent_tabs, ignore_index=True), ctx.results / "partB_attachment_entropy.csv")
    write_csv(pd.concat(pair_tabs, ignore_index=True), ctx.results / "partB_tradition_overlap.csv")
    write_csv(pd.concat(word_tabs, ignore_index=True), ctx.results / "partB_distinctive_words.csv")
    # the five closest parable-folktale pairs, with the opening words of both texts
    excerpt = lambda t: " ".join(t.split()[:30]) + " …"
    qtext, ftext = queries.set_index("id")["text"], folk.set_index("id")["text"]
    top = (ranking[ranking["kind"] == "parable"].sort_values("nearest_cosine", ascending=False)
           .groupby("rep", sort=False).head(5))
    top = top[["rep", "id", "tradition", "title", "nearest_id", "nearest_title", "nearest_atu", "nearest_cosine"]].copy()
    top["parable_opening"] = top["id"].map(lambda i: excerpt(qtext[i]))
    top["folktale_opening"] = top["nearest_id"].map(lambda i: excerpt(ftext[i]))
    write_csv(top, ctx.results / "top_pairs.csv")
    summary = dict(queries=queries.groupby("kind").size().to_dict(), closeness_k=pb["closeness_k"], attach_k=pb["attach_k"])
    write_json(ctx.results / "partB_summary.json", summary)
    return summary
