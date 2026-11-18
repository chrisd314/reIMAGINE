"""Stage `length`: does text length drive folk-closeness? (TA feedback, step 3)

Parables are much shorter than most folktales, and both representations behave differently on short texts.
  excerpts    for every parable and baseline passage, 5 contiguous excerpts of the same number of words
              (within 10%) from random folktales; each excerpt's folk-closeness is computed against the pool
              without its own source tale (and that tale's near-copies). This is a "folktale as query" at the
              text's length. Per tradition: parable minus its excerpts (paired), with a bootstrap interval.
  regression  OLS of folk-closeness on log(words) and group (each tradition's parables, each tradition's
              baseline, folktale excerpts), robust (HC1) standard errors; and a parables-only model with
              tradition. Does the tradition ranking hold at equal length?
  matching    are the baseline passages as long as the parables? (medians, Mann-Whitney test)
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, mannwhitneyu, norm

from .common import PROCESSED, TRADITIONS, Ctx, write_csv
from .corpus import load_corpus
from .part_b import bootstrap_median, folk_closeness
from .reps import build_space

_SENTENCE_END = re.compile(r"[.!?][\"'”’)\]]*$")


# ----------------------------------------------------------------- pure functions
def sentence_starts(words: list[str]) -> np.ndarray:
    """Word positions that open a sentence (position 0, or after a word ending in . ! ?)."""
    ends = np.array([bool(_SENTENCE_END.search(w)) for w in words], dtype=bool)
    return np.flatnonzero(np.concatenate([[True], ends[:-1]]))


def sample_excerpts(targets, folk_words: list[list[str]], n_per: int, tol: float, seed: int) -> list[dict]:
    """Contiguous folktale excerpts matched in length to each target.

    For a target of n words, a folktale is eligible if it has at least ceil((1 - tol) n) words; `n_per` distinct
    eligible folktales are drawn at random, and from each an excerpt of min(n, its length) words is cut, starting
    at a random sentence start that leaves room for it (any word if none does). Excerpt lengths therefore lie in
    [(1 - tol) n, n]. Returns one dict per excerpt: target, k, source (folktale index), start, n_tokens, text.
    """
    rng = np.random.default_rng(seed)
    lens = np.array([len(w) for w in folk_words])
    out = []
    for t, n in enumerate(np.asarray(targets, dtype=int)):
        eligible = np.flatnonzero(lens >= int(np.ceil((1 - tol) * n)))
        if not len(eligible):
            continue
        for k, f in enumerate(rng.choice(eligible, size=min(n_per, len(eligible)), replace=False)):
            words = folk_words[f]
            L = int(min(n, len(words)))
            starts = sentence_starts(words)
            starts = starts[starts + L <= len(words)]
            s = int(rng.choice(starts)) if len(starts) else int(rng.integers(0, len(words) - L + 1))
            out.append(dict(target=t, k=k, source=int(f), start=s, n_tokens=L, text=" ".join(words[s:s + L])))
    return out


def ols(y: np.ndarray, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Least squares with heteroskedasticity-robust (HC1) covariance."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    n, p = X.shape
    bread = np.linalg.pinv(X.T @ X)
    cov = bread @ (X.T * e ** 2) @ X @ bread * n / max(n - p, 1)
    return beta, cov


def group_model(y: np.ndarray, log_tokens: np.ndarray, groups: np.ndarray, at: float):
    """closeness = slope * (log words - at) + one level per group (no intercept): each group coefficient is the
    group's expected closeness at `at` (log words). Returns (names, beta, cov) with the slope first."""
    names = list(pd.unique(groups))
    X = np.column_stack([log_tokens - at] + [(groups == g).astype(float) for g in names])
    beta, cov = ols(y, X)
    return ["log_words"] + names, beta, cov


def contrast(names: list[str], beta: np.ndarray, cov: np.ndarray, a: str, b: str) -> tuple[float, float, float]:
    """Estimate, robust SE and two-sided normal p of coefficient a minus coefficient b."""
    w = np.zeros(len(names))
    w[names.index(a)], w[names.index(b)] = 1.0, -1.0
    est, se = float(w @ beta), float(np.sqrt(w @ cov @ w))
    return est, se, float(2 * norm.sf(abs(est) / se)) if se > 0 else np.nan


# ----------------------------------------------------------------- the stage
def run(ctx: Ctx) -> dict:
    lc = ctx.paper["length"]
    corpus = load_corpus(ctx)
    folk, queries = corpus.folk, corpus.queries(ctx)
    texts = queries[queries["kind"].isin(["parable", "baseline"])].reset_index(drop=True)
    folk_words = [t.split() for t in folk["text"]]
    ex = pd.DataFrame(sample_excerpts(texts["n_tokens"].to_numpy(), folk_words, lc["excerpts_per_text"], lc["tolerance"], lc["seed"]))
    ex["text_id"] = texts["id"].to_numpy()[ex["target"]]
    ex["kind"] = texts["kind"].to_numpy()[ex["target"]]
    ex["tradition"] = texts["tradition"].to_numpy()[ex["target"]]
    ex["source_id"] = folk["id"].to_numpy()[ex["source"]]
    short = texts.assign(n=np.bincount(ex["target"], minlength=len(texts)))
    print(f"    {len(ex)} excerpts for {len(texts)} texts; fewer than {lc['excerpts_per_text']} for "
          f"{int((short['n'] < lc['excerpts_per_text']).sum())} texts (too few long folktales)")

    # the pool without each excerpt's own source tale and that tale's near-copies (corpus audit)
    nar = pd.read_parquet(PROCESSED / "narratives.parquet", columns=["narrative_id", "near_duplicates"])
    near = {k: set(v) for k, v in zip(nar["narrative_id"], nar["near_duplicates"]) if len(v)}
    pos = {k: i for i, k in enumerate(folk["id"])}
    blocked = [[s] + [pos[p] for p in near.get(folk.at[s, "id"], ()) if p in pos] for s in ex["source"]]

    k = ctx.paper["partB"]["closeness_k"]
    rows, reg_rows, match_rows, all_rows = [], [], [], []
    for rep in ctx.reps:
        space = build_space(rep, folk["text"].tolist(), ctx.cfg)
        S = space.sim(space.transform(ex["text"].tolist()))
        for r, b in enumerate(blocked):
            S[r, b] = -np.inf
        ex[f"closeness_{rep}"] = folk_closeness(S, k)
        z = np.load(ctx.work / f"partB_{rep}.npz", allow_pickle=False)
        assert z["query_ids"].tolist() == queries["id"].tolist(), "rerun partB"
        cq = pd.Series(z["closeness"], index=z["query_ids"])
        texts[f"closeness_{rep}"] = cq.loc[texts["id"]].to_numpy()
        mean_ex = ex.groupby("target")[f"closeness_{rep}"].mean()
        texts[f"excerpt_closeness_{rep}"] = mean_ex.reindex(range(len(texts))).to_numpy()

        # ---- paired: text minus its own length-matched excerpts
        rng = np.random.default_rng(lc["seed"])
        n_boot = ctx.shuffles(ctx.paper["partB"]["bootstrap"], cap=1000)
        for trad in TRADITIONS:
            for kind in ("parable", "baseline"):
                m = ((texts["tradition"] == trad) & (texts["kind"] == kind)).to_numpy() & texts[f"excerpt_closeness_{rep}"].notna().to_numpy()
                if m.sum() < 2:
                    continue
                d = (texts[f"closeness_{rep}"] - texts[f"excerpt_closeness_{rep}"]).to_numpy()[m]
                bd = bootstrap_median(d, n_boot, rng)
                exm = ex[ex["target"].isin(np.flatnonzero(m))]
                rows.append(dict(rep=rep, tradition=trad, kind=kind, n=int(m.sum()), excerpts=int(len(exm)),
                                 tokens_median=float(texts.loc[m, "n_tokens"].median()), excerpt_tokens_median=float(exm["n_tokens"].median()),
                                 closeness_median=float(texts.loc[m, f"closeness_{rep}"].median()),
                                 excerpt_closeness_median=float(exm[f"closeness_{rep}"].median()),
                                 diff_median=float(np.median(d)), diff_ci_low=float(np.quantile(bd, 0.025)),
                                 diff_ci_high=float(np.quantile(bd, 0.975)), share_above_own_excerpts=float((d > 0).mean()),
                                 bootstrap=n_boot))

        # ---- regression on parables + baseline + excerpts
        y = np.concatenate([texts[f"closeness_{rep}"].to_numpy(), ex[f"closeness_{rep}"].to_numpy()])
        lt = np.log(np.concatenate([texts["n_tokens"].to_numpy(), ex["n_tokens"].to_numpy()]).astype(float))
        grp = np.concatenate([(texts["tradition"] + " " + texts["kind"]).to_numpy(), np.full(len(ex), "folktale excerpt")])
        at = float(np.median(np.log(texts.loc[texts["kind"] == "parable", "n_tokens"])))
        names, beta, cov = group_model(y, lt, grp, at)
        reg_rows.append(dict(rep=rep, model="all texts: closeness ~ log(words) + group", term="log(words)", estimate=beta[0],
                             se=float(np.sqrt(cov[0, 0])), p=float(2 * norm.sf(abs(beta[0]) / np.sqrt(cov[0, 0]))), n=len(y)))
        for trad in TRADITIONS:
            for kind in ("parable", "baseline"):
                g = f"{trad} {kind}"
                if g in names:
                    i = names.index(g)
                    reg_rows.append(dict(rep=rep, model="all texts: closeness ~ log(words) + group", term=f"{g} (at median parable length)",
                                         estimate=beta[i], se=float(np.sqrt(cov[i, i])), p=np.nan, n=len(y)))
            if f"{trad} parable" in names and f"{trad} baseline" in names:
                est, se, p = contrast(names, beta, cov, f"{trad} parable", f"{trad} baseline")
                reg_rows.append(dict(rep=rep, model="all texts: closeness ~ log(words) + group", term=f"{trad}: parables minus baseline at equal length",
                                     estimate=est, se=se, p=p, n=len(y)))
            if f"{trad} parable" in names:
                est, se, p = contrast(names, beta, cov, f"{trad} parable", "folktale excerpt")
                reg_rows.append(dict(rep=rep, model="all texts: closeness ~ log(words) + group", term=f"{trad}: parables minus folktale excerpts at equal length",
                                     estimate=est, se=se, p=p, n=len(y)))
        # parables only: does the tradition ranking hold at equal length?
        par = (texts["kind"] == "parable").to_numpy()
        yp, ltp, gp = texts.loc[par, f"closeness_{rep}"].to_numpy(), np.log(texts.loc[par, "n_tokens"].to_numpy().astype(float)), texts.loc[par, "tradition"].to_numpy()
        names_p, beta_p, cov_p = group_model(yp, ltp, gp, at)
        raw = texts[par].groupby("tradition")[f"closeness_{rep}"].median()
        adj = pd.Series({t: beta_p[names_p.index(t)] for t in names_p[1:]})
        order_raw, order_adj = raw.sort_values(ascending=False).index.tolist(), adj.sort_values(ascending=False).index.tolist()
        tau = kendalltau([order_raw.index(t) for t in raw.index], [order_adj.index(t) for t in raw.index])[0] if len(raw) > 1 else np.nan
        reg_rows.append(dict(rep=rep, model="parables: closeness ~ log(words) + tradition", term="log(words)", estimate=beta_p[0],
                             se=float(np.sqrt(cov_p[0, 0])), p=float(2 * norm.sf(abs(beta_p[0]) / np.sqrt(cov_p[0, 0]))), n=int(par.sum()),
                             order_raw=" > ".join(order_raw), order_at_equal_length=" > ".join(order_adj), kendall_tau=tau,
                             same_first_and_last=bool(order_raw[0] == order_adj[0] and order_raw[-1] == order_adj[-1])))
        for t in order_adj:
            i = names_p.index(t)
            reg_rows.append(dict(rep=rep, model="parables: closeness ~ log(words) + tradition", term=f"{t} (at median parable length)",
                                 estimate=beta_p[i], se=float(np.sqrt(cov_p[i, i])), p=np.nan, n=int(par.sum())))
        print(f"    {rep}: length slope {beta[0]:+.3f} per log word (all texts); tradition order raw {' > '.join(order_raw)}; "
              f"at equal length {' > '.join(order_adj)}")

    # ---- are the baseline passages as long as the parables?
    for trad in TRADITIONS:
        a = texts.loc[(texts["tradition"] == trad) & (texts["kind"] == "parable"), "n_tokens"]
        b = texts.loc[(texts["tradition"] == trad) & (texts["kind"] == "baseline"), "n_tokens"]
        e = ex.loc[(ex["tradition"] == trad) & (ex["kind"] == "parable"), "n_tokens"]
        if len(a) and len(b):
            p = float(mannwhitneyu(a, b).pvalue) if len(a) > 1 and len(b) > 1 else np.nan
            match_rows.append(dict(tradition=trad, parables=len(a), parable_tokens_median=float(a.median()),
                                   baseline=len(b), baseline_tokens_median=float(b.median()),
                                   baseline_over_parable_median=float(b.median() / a.median()),
                                   excerpt_tokens_median=float(e.median()) if len(e) else np.nan,
                                   mann_whitney_p=p, matched=bool(np.isnan(p) or p >= lc["matching_alpha"])))

    write_csv(pd.DataFrame(rows), ctx.results / "length_control.csv")
    write_csv(pd.DataFrame(reg_rows), ctx.results / "length_regression.csv")
    write_csv(pd.DataFrame(match_rows), ctx.results / "length_matching.csv")
    keep = ["text_id", "kind", "tradition", "k", "source_id", "start", "n_tokens"] + [f"closeness_{r}" for r in ctx.reps]
    write_csv(ex[keep], ctx.results / "length_excerpts.csv")
    return dict(excerpts=len(ex))
