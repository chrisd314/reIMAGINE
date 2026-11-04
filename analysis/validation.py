"""Stage 7: human-validation sample and (when real annotations exist) agreement summaries.

The sample is drawn independently of any agreement result: strata are
similarity band x same/different ATU x same/different region, sampled with a
fixed seed. No simulated or machine labels are ever counted as human labels.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .analyze import load_inputs
from .common import OUTPUTS, load_config, utc_now, write_json
from .networks import similarity_matrix

ASPECTS = ["shared_vocabulary", "shared_topic", "shared_plot", "different_outcome", "insufficient_evidence"]
RUBRIC = {
    "shared_vocabulary": "The two texts use several of the same distinctive words or names (not just common words).",
    "shared_topic": "Both texts are broadly about the same kind of thing (e.g. a trickster animal, a ghost, a clever servant).",
    "shared_plot": "Both texts contain at least one recognisably shared narrative event or sequence (e.g. an impossible task solved with animal help).",
    "different_outcome": "Despite any similarity, the outcome, moral or the role of a main character clearly differs.",
    "insufficient_evidence": "You cannot judge from what you read (too short, fragmentary, or unclear).",
}
VALUES = ["yes", "no", "unsure"]
ANNOT_DIR = OUTPUTS / "validation" / "annotations"


def build_sample() -> pd.DataFrame:
    cfg = load_config()
    vcfg = cfg["validation"]
    nar, reps = load_inputs()
    ids = np.flatnonzero(nar["in_joint"].to_numpy())
    sub = nar.loc[ids].reset_index(drop=True)
    S_sem = similarity_matrix("semantic", ids, None, reps["semantic"][1])
    S_lex = similarity_matrix("lexical", ids, reps["lexical"][1], None)
    n = len(ids)
    iu, ju = np.triu_indices(n, 1)
    sim = S_sem[iu, ju]
    pct = (np.argsort(np.argsort(sim)) + 0.5) / len(sim)
    atu = sub["atu_id"].to_numpy()
    reg = sub["broad_region"].to_numpy()
    same_atu = atu[iu] == atu[ju]
    same_reg = reg[iu] == reg[ju]
    rng = np.random.default_rng(vcfg["seed"])
    used = np.zeros(n, dtype=int)
    rows = []
    for band, (lo, hi) in vcfg["bands"].items():
        in_band = (pct >= lo) & (pct < hi) if hi < 1 else (pct >= lo)
        for sa in (True, False):
            for sr in (True, False):
                cand = np.flatnonzero(in_band & (same_atu == sa) & (same_reg == sr))
                rng.shuffle(cand)
                need = vcfg["per_stratum_dev"] + vcfg["per_stratum_final"]
                picked = []
                for c in cand:
                    a, b = iu[c], ju[c]
                    if used[a] < vcfg["max_pairs_per_tale"] and used[b] < vcfg["max_pairs_per_tale"]:
                        picked.append(c)
                        used[a] += 1
                        used[b] += 1
                    if len(picked) == need:
                        break
                for k, c in enumerate(picked):
                    rows.append(dict(stratum=f"{band}|{'same' if sa else 'different'} ATU|{'same' if sr else 'different'} region",
                                     band=band, same_atu=bool(sa), same_region=bool(sr),
                                     split="development" if k < vcfg["per_stratum_dev"] else "final",
                                     narrative_a=sub.loc[iu[c], "narrative_id"], narrative_b=sub.loc[ju[c], "narrative_id"],
                                     semantic_similarity=float(sim[c]), semantic_percentile=float(pct[c]),
                                     lexical_similarity=float(S_lex[iu[c], ju[c]]), candidates_in_stratum=int(len(cand))))
    df = pd.DataFrame(rows)
    # item IDs are assigned after a seeded shuffle so that order does not reveal the stratum
    df = df.sample(frac=1.0, random_state=vcfg["seed"]).reset_index(drop=True)
    df.insert(0, "item_id", [f"V{k + 1:03d}" for k in range(len(df))])
    return df


def summarise_annotations(sample: pd.DataFrame) -> dict:
    files = sorted(ANNOT_DIR.glob("*.csv")) if ANNOT_DIR.exists() else []
    if not files:
        return dict(status="pending", note="No human annotation files found in outputs/validation/annotations/. "
                    "Validation statistics are not computed until real annotations exist.", files=[])
    ann = pd.concat([pd.read_csv(f, dtype=str) for f in files], ignore_index=True)
    ann = ann[ann["item_id"].isin(sample["item_id"])]
    if "label_source" in ann.columns:
        ann = ann[ann["label_source"].fillna("human") == "human"]
    reviewers = sorted(ann["reviewer_id"].unique())
    per_item = ann.groupby("item_id")["reviewer_id"].nunique()
    overlap = per_item[per_item >= 2].index
    agreement = {}
    for asp in ASPECTS:
        if asp not in ann.columns:
            continue
        piv = ann[ann["item_id"].isin(overlap)].pivot_table(index="item_id", columns="reviewer_id", values=asp, aggfunc="first")
        if piv.shape[1] >= 2:
            a, b = piv.columns[:2]
            both = piv[[a, b]].dropna()
            agreement[asp] = dict(items=int(len(both)), agree=int((both[a] == both[b]).sum()),
                                  disagree=int((both[a] != both[b]).sum()),
                                  raw_agreement=float((both[a] == both[b]).mean()) if len(both) else None)
    merged = ann.merge(sample[["item_id", "band", "split"]], on="item_id")
    by_band = {}
    for asp in ASPECTS:
        if asp in merged.columns:
            t = merged[merged["split"] == "final"].groupby("band")[asp].apply(lambda s: (s == "yes").mean())
            by_band[asp] = {k: float(v) for k, v in t.items()}
    return dict(status="annotations present", files=[f.name for f in files], reviewers=reviewers,
                annotations=int(len(ann)), items_with_two_or_more_reviewers=int(len(overlap)),
                raw_agreement=agreement, share_yes_by_band_final_split=by_band,
                note="Raw agreement only (the course reports percentage agreement); no kappa is computed.")


def run() -> dict:
    sample = build_sample()
    out_dir = OUTPUTS / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    ANNOT_DIR.mkdir(parents=True, exist_ok=True)
    sample.to_csv(out_dir / "validation_sample.csv", index=False)
    summary = dict(generated=utc_now(), items=int(len(sample)),
                   development_items=int((sample["split"] == "development").sum()),
                   final_items=int((sample["split"] == "final").sum()),
                   strata={k: int(v) for k, v in sample.groupby("stratum").size().items()},
                   aspects=ASPECTS, values=VALUES, rubric=RUBRIC,
                   annotations=summarise_annotations(sample))
    write_json(out_dir / "validation_summary.json", summary)
    print(f"  validation sample: {len(sample)} items; status: {summary['annotations']['status']}")
    return summary


if __name__ == "__main__":
    run()
