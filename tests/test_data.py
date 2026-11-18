"""Checks on the prepared data (fetch, clean, audit, cohorts).

Run after the `data` stage of `python -m reimagine.run`. Tests are skipped if an output is missing.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
RAW, INTERIM, PROCESSED, AUDIT = ROOT / "data/raw", ROOT / "data/interim", ROOT / "data/processed", ROOT / "results/corpus_audit"
LEAK = re.compile(r"Aarne|\bATU\b|[Tt]ale[- ]type|\btypes? \d{1,4}[A-Z]?\b|Ashliman|folktexts|Return to|\bSource:")


def need(*paths):
    for p in paths:
        if not Path(p).exists():
            pytest.skip(f"missing output {p}")


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- data
def test_raw_file_is_pinned_and_hashed():
    need(RAW / "source_manifest.json")
    from reimagine.core.common import sha256_file
    man = load_json(RAW / "source_manifest.json")
    entry = next(e for e in man["files"] if e["filename"] == "trilogy/aft.csv")
    assert man["trilogy_commit"] in entry["url"] and entry["version"] == man["trilogy_commit"]
    assert sha256_file(RAW / "trilogy/aft.csv") == entry["sha256"]
    for e in man["files"]:
        assert {"url", "version", "retrieved_at", "sha256", "bytes", "format", "citation", "stated_licence", "role"} <= set(e)


def test_audit_reproduces_brief_diagnostics():
    need(AUDIT / "raw_audit.json")
    checks = load_json(AUDIT / "raw_audit.json")["brief_diagnostics"]
    assert all(c["match"] for c in checks.values()), checks


def test_review_and_mapping_files_are_well_formed():
    review = pd.read_csv(ROOT / "data/mappings/text_review.csv", dtype=str, keep_default_na=False)
    assert list(review.columns) == ["record_id", "action", "pattern", "reason", "reviewer", "reviewed_on"]
    assert set(review["action"]) <= {"exclude", "trim_before", "trim_from", "strip_suffix", "flag_fragment", "keep", "no_auto_tail"}
    assert (review["reason"].str.len() > 10).all(), "every decision needs a reason"
    pm = pd.read_csv(ROOT / "data/mappings/provenance_map.csv", dtype=str, keep_default_na=False)
    required = ["raw_provenance", "normalised_label", "entity_kind", "country_code_if_applicable", "broad_region",
                "latitude", "longitude", "coordinate_meaning", "confidence", "evidence_url_or_source", "rationale",
                "review_status"]
    assert set(required) <= set(pm.columns)


def test_ids_traceable_and_ledger_complete():
    need(INTERIM / "records.parquet", PROCESSED / "narratives.parquet", AUDIT / "inclusion_ledger.csv")
    rec = pd.read_parquet(INTERIM / "records.parquet")
    raw = pd.read_csv(RAW / "trilogy/aft.csv", dtype=str, keep_default_na=False, na_values=[])
    assert len(rec) == len(raw) and rec["record_id"].is_unique
    assert (rec["source_row"] == np.arange(1, len(raw) + 1)).all()
    assert (rec["text_raw"].to_numpy() == raw["text"].to_numpy()).all(), "raw strings must be preserved"
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    members = [r for ids in nar["record_ids"] for r in ids]
    assert len(members) == len(set(members)) == (rec["excluded_reason"] == "").sum()
    for nid, ids in zip(nar["narrative_id"], nar["record_ids"]):
        assert nid == f"tale-{min(int(i.rsplit('-', 1)[1]) for i in ids):04d}"
    led = pd.read_csv(AUDIT / "inclusion_ledger.csv")
    assert len(led) == len(raw) and set(led["record_id"]) == set(rec["record_id"])


def test_duplicate_and_conflict_policy():
    need(PROCESSED / "narratives.parquet")
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    assert nar["text"].is_unique, "identical narrative texts are represented once"
    conflict = nar["atu_status"] == "conflict"
    assert conflict.sum() > 0 and not nar.loc[conflict, "in_atu"].any()
    assert nar.loc[conflict, "in_text"].all(), "label conflicts stay in the text cohort"
    assert (nar.loc[nar["in_atu"], "atu_ids"].map(len) == 1).all()


def test_model_input_is_narrative_text_only():
    need(PROCESSED / "narratives.parquet")
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    leaked = nar[nar["text"].str.contains(LEAK)]
    assert leaked.empty, f"classification or site text left in: {leaked['narrative_id'].tolist()[:5]}"


def test_unknown_geography_stays_unknown_and_coordinates_valid():
    need(PROCESSED / "narratives.parquet")
    pm = pd.read_csv(ROOT / "data/mappings/provenance_map.csv", dtype=str, keep_default_na=False)
    nogeo = pm["entity_kind"].isin(["author", "collection", "unknown"])
    assert (pm.loc[nogeo, ["place_label", "broad_region", "latitude"]] == "").all().all()
    aesop = pm[pm["raw_provenance"] == "Aesop"].iloc[0]
    grimm = pm[pm["raw_provenance"] == "Jacob and Wilhelm Grimm"].iloc[0]
    assert aesop["place_label"] == "" and grimm["place_label"] == "", "authors are not story-origin places"
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    outside = nar[nar["in_atu"] & ~nar["in_joint"]]
    assert len(outside) > 0 and (outside["geo_status"] != "unique").all(), "tales left out for geography must lack a unique place"
    assert outside["latitude"].isna().all(), "no coordinates for tales without defensible geography"
    lat, lon = nar["latitude"].dropna(), nar["longitude"].dropna()
    assert lat.between(-90, 90).all() and lon.between(-180, 180).all()
    assert nar.loc[nar["in_distance"], "latitude"].notna().all()
