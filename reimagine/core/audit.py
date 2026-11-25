"""Stage 1b: executable audit of the pinned raw file and of the cleaning outcome."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .common import INTERIM, AUDIT, RAW, read_json, write_json

EXPECTED = {  # diagnostics quoted in the brief, to verify rather than hard-code
    "rows": 1518, "distinct_texts_ws": 1511, "distinct_atu": 182, "nonmissing_provenance": 1502,
    "nonmissing_source": 1336, "atu_with_5plus": 133, "median_words": 543,
}


def run() -> dict:
    raw = pd.read_csv(RAW / "trilogy" / "aft.csv", dtype=str, keep_default_na=False, na_values=[], encoding="utf-8")
    manifest = read_json(RAW / "source_manifest.json")
    aft_entry = next(e for e in manifest["files"] if e["filename"] == "trilogy/aft.csv")
    ws = raw["text"].map(lambda s: re.sub(r"\s+", " ", s).strip())
    words = raw["text"].map(lambda s: len(s.split()))
    atu_counts = raw["atu_id"].value_counts()
    measured = {
        "rows": len(raw), "distinct_texts_ws": int(ws.nunique()), "distinct_atu": int(raw["atu_id"].nunique()),
        "nonmissing_provenance": int((raw["provenance"] != "NA").sum()),
        "nonmissing_source": int((raw["source"] != "NA").sum()),
        "atu_with_5plus": int((atu_counts >= 5).sum()), "median_words": float(words.median()),
    }
    checks = {k: dict(expected=EXPECTED[k], measured=measured[k], match=float(EXPECTED[k]) == float(measured[k]))
              for k in EXPECTED}
    missing = {c: dict(literal_NA=int((raw[c] == "NA").sum()), empty=int((raw[c].str.strip() == "").sum()))
               for c in raw.columns}
    q = [0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1]
    length = {"quantiles_words": {str(k): float(v) for k, v in zip(q, np.quantile(words, q))},
              "under_30_words": int((words < 30).sum()), "under_100_words": int((words < 100).sum()),
              "over_5000_words": int((words > 5000).sum())}
    groups = []
    for norm, g in raw.assign(norm=ws).groupby("norm"):
        if len(g) > 1:
            groups.append(dict(source_rows=[int(i) + 1 for i in g.index], atu_ids=sorted(set(g["atu_id"])),
                               provenance=sorted(set(g["provenance"])), titles=list(g["tale_title"]),
                               label_conflict=len(set(g["atu_id"])) > 1))
    prov = raw["provenance"].value_counts()
    rec = pd.read_parquet(INTERIM / "records.parquet")
    log = pd.read_csv(AUDIT / "cleaning_log.csv", dtype=str, keep_default_na=False)
    flags = rec["flags"].str.split(";").explode()
    report = {
        "source_file": {k: aft_entry[k] for k in ("url", "version", "sha256", "bytes", "retrieved_at")},
        "brief_diagnostics": checks,
        "missing_values_note": "The R export writes missing values as the literal string 'NA'; counts above treat it as missing.",
        "missingness": missing,
        "length": length,
        "exact_duplicate_groups_raw": groups,
        "atu": {"distinct": int(raw["atu_id"].nunique()), "types_with_5plus": int((atu_counts >= 5).sum()),
                "largest": atu_counts.head(10).to_dict()},
        "provenance": {"distinct_strings_including_NA": int(prov.size), "distinct_nonmissing": int((prov.index != "NA").sum()),
                       "top": prov.head(15).to_dict()},
        "date_obtained": {"values": raw["date_obtained"].value_counts().to_dict(),
                          "meaning": "Date the dataset authors scraped the record; not a collection, publication or origin date."},
        "data_source": raw["data_source"].value_counts().to_dict(),
        "cleaning": {
            "removals_by_rule": log["rule"].value_counts().to_dict(),
            "records_with_removals": int(log["record_id"].nunique()),
            "words_removed": int(rec["n_words_raw"].sum() - rec["n_words"].sum()),
            "mojibake_repaired_texts": int(rec["mojibake_repaired"].sum()),
            "excluded_non_narrative": rec.loc[rec["excluded_reason"] != "", ["record_id", "excluded_reason"]].to_dict("records"),
            "flags": flags[flags != ""].value_counts().to_dict(),
        },
    }
    write_json(AUDIT / "raw_audit.json", report)
    atu_counts.rename_axis("atu_id").reset_index(name="records").to_csv(AUDIT / "atu_frequencies.csv", index=False)
    prov.rename_axis("raw_provenance").reset_index(name="records").to_csv(AUDIT / "provenance_frequencies.csv", index=False)
    # reproducible varied sample for manual inspection (stratified by length quartile)
    quart = pd.qcut(words, 4, labels=False)
    sample = raw.assign(source_row=raw.index + 1, words=words, quartile=quart).groupby("quartile", group_keys=False).apply(
        lambda g: g.sample(6, random_state=7))
    sample[["source_row", "atu_id", "tale_title", "provenance", "words"]].to_csv(
        AUDIT / "manual_inspection_sample.csv", index=False)
    ok = all(c["match"] for c in checks.values())
    print(f"  audit: brief diagnostics {'all reproduced' if ok else 'DIFFER'}; {len(groups)} exact-duplicate groups")
    return report


if __name__ == "__main__":
    run()
