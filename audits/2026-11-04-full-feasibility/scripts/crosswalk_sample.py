"""Draw the Pilot A review sample (30 candidate links) with a fixed, documented stratified rule."""
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
cw = pd.read_csv("crosswalk/crosswalk_candidates.csv", low_memory=False)
key = ["target", "berezkin_name", "target_id"]
agg = cw.groupby(key, dropna=False).agg(
    routes=("route", lambda x: "+".join(sorted(set(x)))), evidence=("evidence", lambda x: " | ".join(dict.fromkeys(x))),
    **{c: (c, "first") for c in ["idn", "oid", "b_lat", "b_lon", "b_family", "b_branch", "n_motifs", "nmbr_title", "year_firstpub",
                                 "year_avgpub", "target_name", "target_alt", "t_lat", "t_lon", "t_family", "t_region", "t_focal_year",
                                 "religion_code", "deep_code", "christian_influence", "distance_km", "multi_group_berezkin"]}).reset_index()
named = agg.routes.str.split("+").map(lambda r: bool({"name", "ea"} & set(r)))
world = agg.religion_code.astype(str).str.match(r"^[1-8] ")
strata = [
    ("S1 SCCS, world-religion code, name/EA route", agg[(agg.target == "SCCS") & named & world], 14),
    ("S2 SCCS, indigenous or missing code, name/EA route", agg[(agg.target == "SCCS") & named & ~world], 6),
    ("S3 SCCS, nearest-society route only", agg[(agg.target == "SCCS") & ~named], 3),
    ("S4 Pulotu, name route", agg[agg.target == "Pulotu"], 4),
    ("S5 DRH entries from eHRAF, name route", agg[agg.target == "DRH(eHRAF)"], 3),
]
FROZEN = "crosswalk/review_sample_keys.csv"  # the draw actually reviewed (2026-11-04, seed 2805)
if os.path.exists(FROZEN):
    keys = pd.read_csv(FROZEN, dtype=str)
    smp = keys.merge(agg.astype({"target_id": str}), on=["target", "berezkin_name", "target_id"], how="left")
    assert len(smp) == 30 and smp.routes.notna().all(), "frozen sample no longer matches the candidates"
    for label, frame, n in strata:
        print(f"{label}: population now {len(frame)}; frozen sample has {int((smp.stratum == label).sum())}")
else:
    picked = []
    for label, frame, n in strata:
        s = frame.sample(n=min(n, len(frame)), random_state=2805).assign(stratum=label, stratum_size=len(frame))
        picked.append(s)
        print(f"{label}: population {len(frame)}, sampled {len(s)}")
    smp = pd.concat(picked, ignore_index=True)
    smp.insert(0, "review_id", [f"A{i + 1:02d}" for i in range(len(smp))])
    smp[["review_id", "stratum", "stratum_size", "target", "berezkin_name", "target_id"]].to_csv(FROZEN, index=False)
smp.to_csv("crosswalk/review_sample_evidence.csv", index=False)
agg.to_csv("crosswalk/crosswalk_candidate_pairs.csv", index=False)
pd.set_option("display.width", 260)
cols = ["review_id", "berezkin_name", "target_name", "target_alt", "routes", "distance_km", "b_family", "b_branch", "t_family",
        "t_focal_year", "year_firstpub", "year_avgpub", "n_motifs", "nmbr_title", "religion_code"]
print(smp[cols].to_string(max_colwidth=34))
