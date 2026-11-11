"""Agreement between the two coders of the top-1 parable-folktale pairs, and precision of the ranking.

    python -m ouaw.agreement [labeling/hand_labels.csv]

Copy labeling/hand_labels_template.csv to labeling/hand_labels.csv and fill `coder1` and `coder2`,
independently, with one of: same_plot, shared_motif, theme_only, unrelated. This module then writes
results/hand_label_agreement.json and results/hand_label_confusion.csv; the figures stage picks the
precision up from there. Until labels exist the status is "pending". No label is ever filled in by code.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .common import LABELING, ROOT, write_csv, write_json

LABELS = ["same_plot", "shared_motif", "theme_only", "unrelated"]      # ordered from closest to farthest
PARALLEL = {"strict": {"same_plot"}, "lenient": {"same_plot", "shared_motif"}}


def confusion(a: list[str], b: list[str], labels: list[str] = LABELS) -> np.ndarray:
    """Counts with coder 1 in rows and coder 2 in columns."""
    pos = {x: k for k, x in enumerate(labels)}
    m = np.zeros((len(labels), len(labels)), dtype=int)
    for x, y in zip(a, b):
        m[pos[x], pos[y]] += 1
    return m


def cohen_kappa(m: np.ndarray, weighted: bool = False) -> float:
    """Cohen's kappa from a confusion matrix; `weighted` uses linear weights for the ordered labels."""
    n = m.sum()
    if n == 0:
        return float("nan")
    k = len(m)
    w = np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1) if weighted else 1.0 - np.eye(k)
    observed = (w * m).sum() / n
    expected = (w * np.outer(m.sum(axis=1), m.sum(axis=0))).sum() / n ** 2
    return float(1.0 - observed / expected) if expected > 0 else float("nan")


def summarise(df: pd.DataFrame) -> dict:
    a = df["coder1"].fillna("").astype(str).str.strip().str.lower()
    b = df["coder2"].fillna("").astype(str).str.strip().str.lower()
    bad = sorted((set(a) | set(b)) - set(LABELS) - {""})
    if bad:
        raise ValueError(f"labels must be one of {LABELS}; found {bad}")
    both = (a != "") & (b != "")
    out = dict(pairs=int(len(df)), coded_by_coder1=int((a != "").sum()), coded_by_coder2=int((b != "").sum()),
               coded_by_both=int(both.sum()))
    if not (a != "").any() and not (b != "").any():
        return dict(status="pending", **out)
    out["status"] = "complete" if both.all() else "partial"
    if both.any():
        m = confusion(a[both].tolist(), b[both].tolist())
        out.update(raw_agreement=float(np.trace(m) / m.sum()), cohen_kappa=cohen_kappa(m),
                   cohen_kappa_linear_weights=cohen_kappa(m, weighted=True),
                   confusion=dict(labels=LABELS, rows="coder1", columns="coder2", counts=m.tolist()))
    precision = {}
    for name, ok in PARALLEL.items():
        entry = {}
        for coder, lab in (("coder1", a), ("coder2", b)):
            if (lab != "").any():
                entry[coder] = float(lab[lab != ""].isin(ok).mean())
        if both.any():
            entry["both_coders_agree_it_is_a_parallel"] = float((a[both].isin(ok) & b[both].isin(ok)).mean())
            entry["either_coder"] = float((a[both].isin(ok) | b[both].isin(ok)).mean())
            if "tradition" in df:
                entry["by_tradition_both_agree"] = {t: float((a[g.index].isin(ok) & b[g.index].isin(ok)).mean())
                                                    for t, g in df[both].groupby("tradition")}
        precision[name] = entry
    out["precision"] = precision
    out["precision_definition"] = {"strict": "same_plot", "lenient": "same_plot or shared_motif"}
    return out


def run(path: Path | None = None, results: Path | None = None) -> dict:
    path = path or LABELING / "hand_labels.csv"
    results = results or ROOT / "results"
    if not path.exists():
        res = dict(status="pending", note=f"{path.relative_to(ROOT).as_posix()} not found: copy the template and fill coder1, coder2")
    else:
        res = summarise(pd.read_csv(path, dtype=str, keep_default_na=False))
        res["file"] = path.relative_to(ROOT).as_posix()
        if "confusion" in res:
            c = pd.DataFrame(res["confusion"]["counts"], index=LABELS, columns=LABELS)
            write_csv(c.rename_axis("coder1 \\ coder2").reset_index(), results / "hand_label_confusion.csv")
    write_json(results / "hand_label_agreement.json", res)
    return res


if __name__ == "__main__":
    r = run(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None)
    print({k: v for k, v in r.items() if k not in ("confusion",)})
