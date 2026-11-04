"""Stage 3: narratives, labels and cohorts.

One node per distinct cleaned narrative text. Exact duplicates (after the
conservative whitespace normalisation already applied in cleaning) are merged;
every member record keeps its ID and metadata. Label conflicts inside a
duplicate group are preserved and only exclude the narrative from analyses
that need that label.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import CountVectorizer

from .common import MAPPINGS, OUTPUTS, PROCESSED, RAW, INTERIM, load_config, write_json

KINDS = {"country", "region", "community", "author", "collection", "mixed", "unknown"}
CONF = {"high", "medium", "low", "none"}

ATU_CHAPTERS = [  # top-level ATU ranges (Uther 2004)
    (1, 299, "Animal Tales"), (300, 749, "Tales of Magic"), (750, 849, "Religious Tales"),
    (850, 999, "Realistic Tales (Novelle)"), (1000, 1199, "Tales of the Stupid Ogre"),
    (1200, 1999, "Anecdotes and Jokes"), (2000, 2399, "Formula Tales"),
]


def atu_number(atu: str) -> int:
    m = re.match(r"(\d+)", atu)
    return int(m.group(1)) if m else -1


def atu_chapter(atu: str) -> str:
    n = atu_number(atu)
    for lo, hi, name in ATU_CHAPTERS:
        if lo <= n <= hi:
            return name
    return "Outside ATU ranges"


def load_provenance_map(records: pd.DataFrame) -> pd.DataFrame:
    pm = pd.read_csv(MAPPINGS / "provenance_map.csv", dtype=str, keep_default_na=False)
    assert pm["raw_provenance"].is_unique, "provenance_map has duplicate raw strings"
    assert set(pm["entity_kind"]) <= KINDS, set(pm["entity_kind"]) - KINDS
    assert set(pm["confidence"]) <= CONF, set(pm["confidence"]) - CONF
    raw_strings = set(records["provenance_raw"])
    missing = raw_strings - set(pm["raw_provenance"])
    assert not missing, f"raw provenance strings without a mapping row: {sorted(missing)[:5]}"
    has_coord = pm["latitude"] != ""
    lat = pd.to_numeric(pm.loc[has_coord, "latitude"])
    lon = pd.to_numeric(pm.loc[has_coord, "longitude"])
    assert lat.between(-90, 90).all() and lon.between(-180, 180).all(), "coordinate out of range"
    assert (pm.loc[has_coord, "place_label"] != "").all(), "coordinates without a place label"
    # unknown geography must stay unknown: no coordinates or regions for kinds without a place
    nogeo = pm["entity_kind"].isin(["author", "collection", "unknown"])
    assert (pm.loc[nogeo, "latitude"] == "").all() and (pm.loc[nogeo, "place_label"] == "").all()
    return pm


def source_key(src: str | None) -> str:
    """Coarse bibliographic grouping: the author/editor segment of the source string."""
    if not isinstance(src, str) or not src:
        return "(no source)"
    s = re.sub(r"^Source[s]?(?: \([^)]*\))?[:,]?\s*", "", src)
    s = re.sub(r"'[^']{0,200}?,'", " ", s)        # drop quoted tale titles 'Title,'
    s = re.sub(r"\(.*$", "", s)                     # cut at the imprint parenthesis
    head = s.split(",")[0]
    head = re.sub(r"[^\w\s&]", " ", head.lower())
    head = re.sub(r"\b(?:ed|eds|edited|by|trans|translated|and|the|of|retold)\b", " ", head)
    head = re.sub(r"\b\w\b", " ", head)             # initials
    head = re.sub(r"\s+", " ", head).strip()
    return head or "(unparsed)"


def near_duplicates(texts: list[str], ids: list[str], n: int, threshold: float) -> pd.DataFrame:
    vec = CountVectorizer(analyzer="word", ngram_range=(n, n), lowercase=True, binary=True,
                          token_pattern=r"(?u)\b\w+\b", dtype=np.int32)
    X = vec.fit_transform(texts)
    sizes = np.asarray(X.sum(axis=1)).ravel()
    inter = (X @ X.T).tocoo()
    rows = []
    for i, j, v in zip(inter.row, inter.col, inter.data):
        if i < j and v > 0:
            jac = v / (sizes[i] + sizes[j] - v)
            if jac >= threshold:
                rows.append((ids[i], ids[j], round(float(jac), 4)))
    return pd.DataFrame(rows, columns=["narrative_a", "narrative_b", "jaccard_word5"])


def run() -> dict:
    cfg = load_config()
    ccfg = cfg["cohorts"]
    rec = pd.read_parquet(INTERIM / "records.parquet")
    pm = load_provenance_map(rec)
    atu_df = pd.read_csv(RAW / "trilogy" / "atu_df.csv", dtype=str, keep_default_na=False, encoding="utf-8")
    atu_names = dict(zip(atu_df["atu_id"], atu_df["tale_name"]))

    pmi = pm.set_index("raw_provenance")
    rec = rec.join(pmi[["normalised_label", "entity_kind", "place_label", "place_kind", "place_detail",
                        "broad_region", "country_code_if_applicable", "latitude", "longitude", "confidence",
                        "coordinate_meaning"]], on="provenance_raw")
    ok_conf = set(ccfg["geo_min_confidence"])
    rec["geo_ok"] = (rec["place_label"] != "") & (rec["broad_region"] != "") & rec["confidence"].isin(ok_conf)
    rec["source_key"] = rec["source"].map(source_key)
    rec["atu_valid"] = rec["atu_id"].isin(atu_names.keys())

    usable = rec[rec["excluded_reason"] == ""].copy()
    first_row = usable.groupby("text")["source_row"].transform("min")
    usable["narrative_id"] = first_row.map(lambda r: f"tale-{r:04d}")
    rec = rec.merge(usable[["record_id", "narrative_id"]], on="record_id", how="left")

    narratives = []
    for nid, g in usable.sort_values("source_row").groupby("narrative_id", sort=True):
        lead = g.iloc[0]
        atus = sorted(set(g.loc[g["atu_valid"], "atu_id"]))
        geo = g[g["geo_ok"]]
        places = sorted(set(zip(geo["place_label"], geo["broad_region"])))
        atu_status = "unique" if len(atus) == 1 else ("conflict" if len(atus) > 1 else "missing")
        geo_status = "unique" if len(places) == 1 else ("conflict" if len(places) > 1 else "unknown")
        gl = geo.iloc[0] if len(places) == 1 else None
        coords = None
        if gl is not None:
            c = geo[geo["latitude"] != ""]
            if len(set(zip(c["latitude"], c["longitude"]))) == 1:
                coords = (float(c.iloc[0]["latitude"]), float(c.iloc[0]["longitude"]))
        narratives.append(dict(
            narrative_id=nid, record_ids=list(g["record_id"]), n_records=len(g),
            title=lead["title"], titles=list(dict.fromkeys(g["title"])),
            text=lead["text"], n_words=int(lead["n_words"]),
            atu_id=atus[0] if atu_status == "unique" else None, atu_ids=atus, atu_status=atu_status,
            atu_name=atu_names.get(atus[0]) if atu_status == "unique" else None,
            atu_chapter=atu_chapter(atus[0]) if atu_status == "unique" else None,
            provenance_raw=list(dict.fromkeys(g["provenance_raw"])),
            provenance_label=list(dict.fromkeys(g["normalised_label"])),
            entity_kind=list(dict.fromkeys(g["entity_kind"])),
            geo_status=geo_status,
            place_label=gl["place_label"] if gl is not None else None,
            place_kind=gl["place_kind"] if gl is not None else None,
            place_detail=gl["place_detail"] if gl is not None else None,
            broad_region=gl["broad_region"] if gl is not None else None,
            country_code=gl["country_code_if_applicable"] if gl is not None else None,
            geo_confidence=gl["confidence"] if gl is not None else None,
            latitude=coords[0] if coords else None, longitude=coords[1] if coords else None,
            coordinate_meaning=gl["coordinate_meaning"] if (gl is not None and coords) else None,
            source=lead["source"], sources=list(dict.fromkeys(s for s in g["source"] if s)),
            source_key=lead["source_key"], notes=lead["notes"],
            flags=sorted(set(";".join(g["flags"]).split(";")) - {""}),
        ))
    nar = pd.DataFrame(narratives)

    # near duplicates (edition reuse or near-identical copies) among distinct narratives
    nd = near_duplicates(nar["text"].tolist(), nar["narrative_id"].tolist(),
                         ccfg["near_duplicate"]["shingle_words"], ccfg["near_duplicate"]["jaccard_threshold"])
    partners: dict[str, list] = {}
    for a, b, _ in nd.itertuples(index=False):
        partners.setdefault(a, []).append(b)
        partners.setdefault(b, []).append(a)
    nar["near_duplicates"] = nar["narrative_id"].map(lambda x: sorted(partners.get(x, [])))
    # near-duplicate-reduced subset: keep the lowest ID of each connected component
    ids = nar["narrative_id"].tolist()
    idx = {k: i for i, k in enumerate(ids)}
    if len(nd):
        m = sp.coo_matrix((np.ones(len(nd)), ([idx[a] for a in nd.narrative_a], [idx[b] for b in nd.narrative_b])),
                          shape=(len(ids), len(ids)))
        _, comp = sp.csgraph.connected_components(m, directed=False)
    else:
        comp = np.arange(len(ids))
    keep = pd.Series(ids).groupby(comp).transform("min")
    nar["near_dup_representative"] = keep.values == np.array(ids)

    fragment = nar["flags"].map(lambda f: "suspected_truncated_start" in f)
    nar["suspected_fragment"] = fragment

    # cohorts
    nar["in_text"] = True
    nar["in_atu"] = nar["atu_status"] == "unique"
    nar["in_joint"] = nar["in_atu"] & (nar["geo_status"] == "unique")
    nar["in_distance"] = nar["in_joint"] & nar["latitude"].notna()

    def reasons(r):
        out = []
        if r["atu_status"] == "conflict":
            out.append("ATU labels conflict across identical copies: " + ", ".join(r["atu_ids"]))
        elif r["atu_status"] == "missing":
            out.append("no valid ATU label")
        if r["geo_status"] == "conflict":
            out.append("geographical labels conflict across identical copies")
        elif r["geo_status"] == "unknown":
            out.append("no defensible place and broad region (" + "; ".join(r["entity_kind"]) + ")")
        if r["in_joint"] and not r["in_distance"]:
            out.append("place has no documented coordinates (e.g. community or multi-country region)")
        return " | ".join(out)
    nar["exclusion_reasons"] = nar.apply(reasons, axis=1)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    nar.to_parquet(PROCESSED / "narratives.parquet", index=False)
    nd.to_csv(OUTPUTS / "audit" / "near_duplicates.csv", index=False)
    cohort_cols = ["narrative_id", "in_text", "in_atu", "in_joint", "in_distance", "suspected_fragment",
                   "near_dup_representative", "exclusion_reasons"]
    nar[cohort_cols].to_csv(PROCESSED / "cohorts.csv", index=False)

    # per-record inclusion ledger
    led = rec[["record_id", "source_row", "title", "atu_id", "provenance_raw", "normalised_label", "entity_kind",
               "geo_ok", "excluded_reason", "narrative_id", "flags"]].copy()
    led = led.merge(nar[["narrative_id", "in_text", "in_atu", "in_joint", "in_distance", "exclusion_reasons"]],
                    on="narrative_id", how="left")
    for c in ["in_text", "in_atu", "in_joint", "in_distance"]:
        led[c] = led[c].fillna(False).astype(bool)
    led["duplicate_of"] = np.where(led["narrative_id"].notna() &
                                   (led["narrative_id"] != led["source_row"].map(lambda r: f"tale-{r:04d}")),
                                   led["narrative_id"], "")
    led.to_csv(OUTPUTS / "audit" / "inclusion_ledger.csv", index=False)

    counts = {
        "raw_records": int(len(rec)),
        "records_excluded_non_narrative": int((rec["excluded_reason"] != "").sum()),
        "records_usable": int(len(usable)),
        "exact_duplicate_records_merged": int(len(usable) - len(nar)),
        "text_cohort": int(nar["in_text"].sum()),
        "atu_conflicts": int((nar["atu_status"] == "conflict").sum()),
        "atu_cohort": int(nar["in_atu"].sum()),
        "geo_unknown_in_atu_cohort": int((nar["in_atu"] & (nar["geo_status"] == "unknown")).sum()),
        "geo_conflict_in_atu_cohort": int((nar["in_atu"] & (nar["geo_status"] == "conflict")).sum()),
        "joint_cohort": int(nar["in_joint"].sum()),
        "distance_cohort": int(nar["in_distance"].sum()),
        "near_duplicate_pairs": int(len(nd)),
        "near_dup_reduced_text_cohort": int(nar["near_dup_representative"].sum()),
        "suspected_fragments_text_cohort": int(fragment.sum()),
        "joint_distinct_atu": int(nar.loc[nar["in_joint"], "atu_id"].nunique()),
        "joint_distinct_place": int(nar.loc[nar["in_joint"], "place_label"].nunique()),
        "joint_distinct_region": int(nar.loc[nar["in_joint"], "broad_region"].nunique()),
    }
    write_json(OUTPUTS / "audit" / "cohort_counts.json", counts)
    print("  " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    return counts


if __name__ == "__main__":
    run()
