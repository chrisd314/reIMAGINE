"""Corrected frame for the recommended design: tale types with a religious-collection version and other versions.

Framing comes from a metadata screen (provenance/source/title) and still needs a hand check; two scripture
false positives found on inspection are excluded (tale-1375 'The Bible and Key Trial', tale-1388 'The Fable
of the Flying Dutchman': folk texts that mention a Bible).
"""
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = Path(sys.argv[1])
d = pd.read_parquet(P / "data/processed/narratives.parquet")


def j(v):
    if isinstance(v, str):
        return v
    try:
        return " | ".join(str(x) for x in v if isinstance(x, str))
    except TypeError:
        return ""


meta = d.provenance_raw.map(j) + " || " + d.source.map(j) + " || " + d.title.fillna("")
REL = {"Buddhist: Jataka": r"J[aā]taka", "Christian: Gesta Romanorum": r"Gesta Romanorum",
       "Christian: sermon exempla": r"Vitry|Odo of Cheriton|Bourbon|Bromyard|exempl",
       "Jewish: Talmud/Midrash": r"Talmud|Midrash", "Islamic: Qur'an": r"Koran|Qur.an",
       "Islamic (Sufi): Rumi/Sa'di/Attar": r"Rumi|Masnavi|Mathnawi|Sa.di|Gulistan|Bustan|Attar|Sufi"}
d["framing"] = ""
for k, p in REL.items():
    d.loc[meta.str.contains(p, regex=True) & (d.framing == ""), "framing"] = k
d.loc[d.narrative_id.isin(["tale-1375", "tale-1388"]), "framing"] = ""
d["religious"] = d.framing != ""
types = d[d.religious].atu_id.dropna().unique()
sub = d[d.atu_id.isin(types)]
t = sub.groupby("atu_id").agg(name=("atu_name", "first"), religious_versions=("religious", "sum"), other_versions=("religious", lambda x: int((~x).sum())),
                              framings=("framing", lambda x: "; ".join(sorted(set(x) - {""}))), median_words=("n_words", "median"))
t = t[(t.religious_versions > 0) & (t.other_versions > 0)]
t.to_csv("evidence/annotation_frame_types.csv")
rv = d[d.religious & d.atu_id.isin(t.index)][["narrative_id", "atu_id", "title", "framing", "n_words", "in_joint", "place_label"]]
rv.to_csv("evidence/religious_collection_versions.csv", index=False)
print(f"{len(t)} types; {int(t.religious_versions.sum())} religious-collection versions; {int(t.other_versions.sum())} other versions; "
      f"{int((t.other_versions >= 2).sum())} types with >= 2 other versions; frame with <= 3 others per type: {int((t.religious_versions + t.other_versions.clip(upper=3)).sum())}")
print("framings:", rv.framing.value_counts().to_dict(), "| in joint cohort:", int(rv.in_joint.sum()))
