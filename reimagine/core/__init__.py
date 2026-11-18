"""Data preparation and core functions shared by every stage of the pipeline.

Data preparation (`prepare`): fetch the pinned folktale corpus, clean it, audit it and build the cohort table
`data/processed/narratives.parquet`. Core functions: TF-IDF (`lexical`), sentence embeddings (`semantic`),
similarity graphs and Louvain (`networks`), label agreement and shuffles (`metrics`), paths and hashing (`common`).
"""
from __future__ import annotations

import time

from .common import INTERIM, MAPPINGS, RAW, content_hash, load_config, read_json, stable_hash, write_json

STAMPS = INTERIM / "stamps"
STEPS = ["fetch", "clean", "audit", "cohorts"]


def _inputs(step: str, cfg: dict) -> dict:
    """Configuration and upstream files that determine a step's outputs."""
    aft = RAW / "trilogy" / "aft.csv"
    deps = {
        "fetch": ({"sources": cfg["sources"]}, []),
        "clean": ({"cleaning": cfg["cleaning"]}, [aft, MAPPINGS / "text_review.csv"]),
        "audit": ({}, [aft, INTERIM / "records.parquet"]),
        "cohorts": ({"cohorts": cfg["cohorts"]}, [INTERIM / "records.parquet", MAPPINGS / "provenance_map.csv"]),
    }
    c, files = deps[step]
    return {"config": stable_hash(c), "files": {p.name: content_hash(p) for p in files if p.exists()}}


def prepare(force: bool = False) -> None:
    """Fetch, clean, audit and build cohorts. A step is skipped when its inputs are unchanged since its last run."""
    from . import audit, clean, cohorts, fetch
    run = {"fetch": fetch.run, "clean": clean.run, "audit": audit.run, "cohorts": cohorts.run}
    STAMPS.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    for step in STEPS:
        stamp = STAMPS / f"{step}.json"
        current = _inputs(step, cfg)
        if not force and step != "audit" and stamp.exists() and read_json(stamp).get("inputs") == current:
            print(f"  {step}: inputs unchanged, skipped")
            continue
        print(f"  {step}")
        t0 = time.time()
        run[step]()
        write_json(stamp, {"inputs": _inputs(step, cfg), "seconds": round(time.time() - t0, 1)})
