"""Stage: the annotation frame for the lesson study.

Tale types that are told both in a religious teaching collection and in other collections
("twice-told" types). The frame holds every religious-collection version of those types plus
a fixed-size seeded sample of the other versions. Framing comes from the reviewable table
data/mappings/framing_review.csv; a version not listed there is `other`.

Nothing here looks at text similarity or at lesson codes, so the frame cannot be tuned to a result.
"""
from __future__ import annotations

import random

import pandas as pd

from .common import MAPPINGS, OUTPUTS, PROCESSED, load_config, write_json

FRAME = PROCESSED / "lesson_frame.csv"


def load_framing() -> pd.DataFrame:
    rev = pd.read_csv(MAPPINGS / "framing_review.csv", dtype=str, keep_default_na=False)
    rev["mediated"] = rev["mediated"].str.lower() == "true"
    return rev[rev["framing"] == "religious"].set_index("narrative_id")


def sample_others(group: pd.DataFrame, k: int, seed: int, min_words: int) -> list[str]:
    """Up to k other versions of one tale type: complete texts first, one per source where possible."""
    good = group[group["near_dup_representative"] & ~group["suspected_fragment"] & (group["n_words"] >= min_words)]
    pool = good if len(good) >= min(k, len(group)) else group
    ids = sorted(pool["narrative_id"])
    random.Random(f"{seed}:{group['atu_id'].iloc[0]}").shuffle(ids)
    src = pool.set_index("narrative_id")["source_key"]
    chosen, seen = [], set()
    for nid in ids:                       # first pass: distinct sources
        if len(chosen) < k and src[nid] not in seen:
            chosen.append(nid)
            seen.add(src[nid])
    for nid in ids:                       # second pass: fill up
        if len(chosen) < k and nid not in chosen:
            chosen.append(nid)
    return chosen


def run() -> dict:
    cfg = load_config()["frame"]
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    rel = load_framing()
    missing = set(rel.index) - set(nar["narrative_id"])
    assert not missing, f"framing_review.csv names unknown narratives: {sorted(missing)}"
    nar = nar[nar["atu_status"] == "unique"].copy()
    nar["framing"] = nar["narrative_id"].map(lambda n: "religious" if n in rel.index else "other")

    rows, types = [], []
    for atu, g in nar.groupby("atu_id"):
        n_rel, n_oth = int((g["framing"] == "religious").sum()), int((g["framing"] == "other").sum())
        if n_rel == 0:
            continue
        traditions = sorted(set(rel.loc[g.loc[g["framing"] == "religious", "narrative_id"], "tradition"]))
        in_tests = n_oth > 0
        if not in_tests and len(traditions) < 2:
            continue      # one religious tradition and nothing to compare it with
        others = sample_others(g[g["framing"] == "other"], cfg["others_per_type"], cfg["seed"], cfg["min_words"]) if n_oth else []
        keep = g[(g["framing"] == "religious") | g["narrative_id"].isin(others)]
        for _, r in keep.iterrows():
            nid, religious = r["narrative_id"], r["framing"] == "religious"
            rows.append(dict(
                narrative_id=nid, atu_id=atu, atu_name=r["atu_name"], framing=r["framing"],
                tradition=rel.loc[nid, "tradition"] if religious else "",
                collection=rel.loc[nid, "collection"] if religious else "",
                mediated=bool(rel.loc[nid, "mediated"]) if religious else False,
                in_tests=in_tests, n_words=int(r["n_words"]), title=r["title"],
                source=r["source"] if isinstance(r["source"], str) else ""))
        types.append(dict(atu_id=atu, atu_name=g["atu_name"].iloc[0], religious_versions=n_rel, other_versions=n_oth,
                          other_versions_sampled=len(others), traditions="; ".join(traditions), in_tests=in_tests))
    frame = pd.DataFrame(rows).sort_values(["atu_id", "framing", "narrative_id"]).reset_index(drop=True)
    assert frame["narrative_id"].is_unique
    frame.to_csv(FRAME, index=False, lineterminator="\n")
    tt = pd.DataFrame(types).sort_values("atu_id")
    (OUTPUTS / "audit").mkdir(parents=True, exist_ok=True)
    tt.to_csv(OUTPUTS / "audit" / "lesson_frame_types.csv", index=False, lineterminator="\n")
    tested = frame[frame["in_tests"]]
    summary = dict(
        types=int(len(tt)), types_in_tests=int(tt["in_tests"].sum()),
        versions=int(len(frame)), versions_in_tests=int(len(tested)),
        religious_versions=int((frame["framing"] == "religious").sum()),
        religious_versions_in_tests=int((tested["framing"] == "religious").sum()),
        other_versions_sampled=int((frame["framing"] == "other").sum()),
        other_versions_available=int(tt.loc[tt["in_tests"], "other_versions"].sum()),
        mediated=int(frame["mediated"].sum()),
        by_tradition=frame[frame["framing"] == "religious"].groupby("tradition").size().to_dict(),
        by_collection=frame[frame["framing"] == "religious"].groupby("collection").size().to_dict(),
        rule=f"all religious-collection versions plus up to {cfg['others_per_type']} other versions per tale type "
             f"(seed {cfg['seed']}; complete texts of at least {cfg['min_words']} words first, one per source where possible)")
    write_json(OUTPUTS / "audit" / "lesson_frame.json", summary)
    print(f"  frame: {summary['types_in_tests']} twice-told tale types (+{summary['types'] - summary['types_in_tests']} "
          f"religious-only), {summary['versions']} versions = {summary['religious_versions']} religious-collection "
          f"+ {summary['other_versions_sampled']} others")
    return summary


if __name__ == "__main__":
    run()
