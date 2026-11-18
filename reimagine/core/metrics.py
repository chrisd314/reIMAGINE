"""Label-agreement measures and the label-shuffle reference (vectorised).

The fast implementations below are checked against scikit-learn and NetworkX
on observed values in tests/test_metrics.py.
"""
from __future__ import annotations

import numpy as np


def codes(values) -> tuple[np.ndarray, list]:
    cats = sorted(set(values))
    lookup = {c: k for k, c in enumerate(cats)}
    return np.array([lookup[v] for v in values], dtype=np.int64), cats


def entropy_from_counts(c: np.ndarray) -> float:
    c = c[c > 0].astype(float)
    p = c / c.sum()
    return float(-(p * np.log(p)).sum())


def nmi(a: np.ndarray, b: np.ndarray) -> float:
    """Normalised mutual information, arithmetic normalisation: 2I/(H_a + H_b) (week 4)."""
    ka, kb = a.max() + 1, b.max() + 1
    cont = np.bincount(a * kb + b, minlength=ka * kb).reshape(ka, kb).astype(float)
    n = cont.sum()
    ha = entropy_from_counts(cont.sum(axis=1))
    hb = entropy_from_counts(cont.sum(axis=0))
    if ha == 0 and hb == 0:
        return 1.0
    nz = cont > 0
    pij = cont[nz] / n
    pa = (cont.sum(axis=1, keepdims=True) / n)
    pb = (cont.sum(axis=0, keepdims=True) / n)
    mi = float((pij * np.log(pij / (pa @ pb)[nz])).sum())
    return 2.0 * mi / (ha + hb) if (ha + hb) > 0 else 0.0


def assortativity_and_share(labels: np.ndarray, ei: np.ndarray, ej: np.ndarray, deg: np.ndarray):
    """Unweighted attribute assortativity (NetworkX definition) and same-label edge share."""
    m = len(ei)
    same = float((labels[ei] == labels[ej]).sum()) / m
    a = np.bincount(labels, weights=deg, minlength=labels.max() + 1) / (2.0 * m)
    sa = float((a ** 2).sum())
    r = (same - sa) / (1.0 - sa) if sa < 1 else float("nan")
    return r, same


def permutation_matrix(n: int, n_perm: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.stack([rng.permutation(n) for _ in range(n_perm)]).astype(np.int32)


def summarise_null(obs: float, null: np.ndarray) -> dict:
    mean, sd = float(null.mean()), float(null.std(ddof=1))
    return dict(observed=float(obs), null_mean=mean, null_sd=sd,
                null_p95=float(np.quantile(null, 0.95)), null_p99=float(np.quantile(null, 0.99)),
                null_max=float(null.max()), excess=float(obs - mean),
                z=float((obs - mean) / sd) if sd > 0 else None,
                p_upper=float((1 + (null >= obs).sum()) / (1 + len(null))),
                exceeds_all=bool(obs > null.max()))


def label_agreement(partition: np.ndarray, labels: np.ndarray, ei: np.ndarray, ej: np.ndarray,
                    perms: np.ndarray, keep_null: bool = False) -> dict:
    n = len(labels)
    deg = np.bincount(np.concatenate([ei, ej]), minlength=n).astype(float)
    obs_nmi = nmi(partition, labels)
    obs_r, obs_share = assortativity_and_share(labels, ei, ej, deg)
    nn, nr, ns = [], [], []
    for p in perms:
        lp = labels[p]
        nn.append(nmi(partition, lp))
        r, s = assortativity_and_share(lp, ei, ej, deg)
        nr.append(r)
        ns.append(s)
    nn, nr, ns = np.array(nn), np.array(nr), np.array(ns)
    out = dict(categories=int(len(np.unique(labels))),
               nmi=summarise_null(obs_nmi, nn), assortativity=summarise_null(obs_r, nr),
               same_label_edge_share=summarise_null(obs_share, ns))
    if keep_null:
        out["null_values"] = dict(nmi=nn.round(5).tolist(), assortativity=nr.round(5).tolist())
    return out


def top_k_neighbours(S: np.ndarray, k: int, eligible: np.ndarray | None = None) -> np.ndarray:
    """Indices of each row's k most similar other rows (ties by lower index).

    `eligible` is an optional boolean matrix restricting candidate neighbours.
    """
    n = S.shape[0]
    M = S.copy()
    np.fill_diagonal(M, -np.inf)
    if eligible is not None:
        M[~eligible] = -np.inf
    out = np.empty((n, k), dtype=np.int64)
    cols = np.arange(n)
    for r in range(n):
        order = np.lexsort((cols, -np.round(M[r], 12)))
        out[r] = order[:k]
    return out
