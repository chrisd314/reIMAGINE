"""Stage `partB`: the parables placed among the folktales.

For each representation, every parable, baseline passage and calibration retelling is compared with all
folktales. The folktale network itself (Part A) is never changed.
  closeness   folk-closeness = mean cosine of a text's 5 nearest folktales, and the same quantity for every
              folktale against the other folktales (leave-one-out), the scale the parables are read on
  neighbours  the 10 nearest folktales of every text, which the later stages use to place it among the
              communities and to let its neighbours vote for a tale type
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import TRADITIONS, Ctx, top_k, write_csv, write_json
from .corpus import load_corpus
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


def jsd_bits(p: np.ndarray, q: np.ndarray) -> float:
    """Jensen-Shannon divergence (bits) between two count or share vectors: 0 = same, 1 = disjoint."""
    p, q = p / p.sum(), q / q.sum()
    m = (p + q) / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        kl_p = np.where(p > 0, p * np.log2(p / m), 0.0).sum()
        kl_q = np.where(q > 0, q * np.log2(q / m), 0.0).sum()
    return float((kl_p + kl_q) / 2)


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
    """Query x folktale and folktale x folktale cosines. `transform` (masking) is applied to every text first."""
    t = transform or (lambda s: s)
    space = build_space(rep, [t(x) for x in folk["text"]], ctx.cfg)
    return dict(S=space.sim(space.transform([t(x) for x in queries["text"]])), S_ff=space.folk_sim(), space=space)


def scores(ctx: Ctx, sim: dict, folk: pd.DataFrame) -> dict:
    """Nearest folktales and folk_closeness for the queries, and the leave-one-out values of the folktales."""
    pb = ctx.analysis["partB"]
    idx, val = nearest(sim["S"], pb["attach_k"])
    atu = folk["atu_id"].to_numpy(dtype=object)
    same_type = (atu[:, None] == atu[None, :]) & pd.notna(atu)[:, None]
    return dict(idx=idx, val=val, closeness=val[:, :pb["closeness_k"]].mean(axis=1),
                loo=leave_one_out(sim["S_ff"], pb["closeness_k"]),
                loo_other_types=leave_one_out(sim["S_ff"], pb["closeness_k"], exclude=same_type))


def load_map(ctx: Ctx, rep: str, folk: pd.DataFrame) -> np.ndarray:
    z = np.load(ctx.work / f"map_{rep}.npz", allow_pickle=False)
    assert z["ids"].tolist() == folk["id"].tolist(), "run partA first (the map does not match the folktales)"
    return z["group"]


def run(ctx: Ctx) -> dict:
    corpus = load_corpus(ctx)
    folk, queries = corpus.folk, corpus.queries(ctx)
    pb = ctx.analysis["partB"]
    rank_rows, folk_rows = [], []
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
        for name, v in (("all other folktales", sc["loo"]), ("other folktales of a different tale type", sc["loo_other_types"])):
            folk_rows.append(dict(rep=rep, candidates=name, n=len(v), **{f"q{int(p * 100):02d}": float(np.quantile(v, p))
                                                                      for p in (0.05, 0.25, 0.5, 0.75, 0.95)}))
        medians = {t: float(np.median(sc["closeness"][is_par & (queries["tradition"] == t).to_numpy()]))
                   for t in TRADITIONS if (is_par & (queries["tradition"] == t).to_numpy()).any()}
        print(f"    {rep}: folktale leave-one-out median {np.median(sc['loo']):.3f}, parable medians by tradition: "
              + ", ".join(f"{t} {m:.3f}" for t, m in sorted(medians.items(), key=lambda kv: -kv[1])))

    ranking = pd.DataFrame(rank_rows).sort_values(["rep", "kind", "folk_closeness"], ascending=[True, True, False])
    write_csv(ranking, ctx.results / "partB_ranking.csv")
    write_csv(pd.DataFrame(folk_rows), ctx.results / "partB_folktale_baseline.csv")
    summary = dict(queries=queries.groupby("kind").size().to_dict(), closeness_k=pb["closeness_k"], attach_k=pb["attach_k"])
    write_json(ctx.results / "partB_summary.json", summary)
    return summary
