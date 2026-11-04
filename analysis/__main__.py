"""Command-line entry point: `python -m analysis <stage> [...]` or `python -m analysis all`.

Stages run in order. Expensive stages are skipped when a stamp file shows that
their inputs (relevant config section + upstream file hashes) are unchanged;
pass --force to rerun anyway.
"""
from __future__ import annotations

import argparse
import sys
import time

from .common import INTERIM, MAPPINGS, OUTPUTS, PROCESSED, RAW, content_hash, load_config, read_json, stable_hash, write_json

STAMPS = OUTPUTS / ".stamps"


def _hash_files(paths) -> dict:
    return {p.name: content_hash(p) for p in paths if p.exists()}


def _inputs(stage: str, cfg: dict) -> dict:
    """Configuration and upstream files that determine a stage's outputs."""
    aft = RAW / "trilogy" / "aft.csv"
    deps = {
        "fetch": ({"sources": cfg["sources"]}, []),
        "clean": ({"cleaning": cfg["cleaning"]}, [aft, MAPPINGS / "text_review.csv"]),
        "audit": ({}, [aft, INTERIM / "records.parquet"]),
        "cohorts": ({"cohorts": cfg["cohorts"]}, [INTERIM / "records.parquet", MAPPINGS / "provenance_map.csv"]),
        "lexical": ({"lexical": cfg["lexical"]}, [PROCESSED / "narratives.parquet"]),
        "semantic": ({"semantic": cfg["semantic"]}, [PROCESSED / "narratives.parquet"]),
        "analyze": ({"graphs": cfg["graphs"], "evaluation": cfg["evaluation"]},
                    [PROCESSED / "narratives.parquet", INTERIM / "lexical_tfidf.npz", INTERIM / "semantic_vectors.npz"]),
        "modnull": ({"graphs": cfg["graphs"]}, [OUTPUTS / "metrics" / "graphs.json"]),
        "distance": ({"distance": cfg["distance"]}, [PROCESSED / "narratives.parquet", INTERIM / "semantic_vectors.npz"]),
        "validation": ({"validation": cfg["validation"]}, [PROCESSED / "narratives.parquet", INTERIM / "semantic_vectors.npz"]),
        "layouts": ({"graphs": cfg["graphs"]}, [OUTPUTS / "metrics" / "graphs.json"]),
        "export": ({"export": cfg.get("export", {})}, []),
    }
    c, files = deps[stage]
    return {"config": stable_hash(c), "files": _hash_files(files)}


def _run_stage(stage: str):
    from . import (analyze, audit, clean, cohorts, distance, export, fetch, layouts, lexical, modnull, semantic,
                   validation)
    return {"fetch": fetch.run, "clean": clean.run, "audit": audit.run, "cohorts": cohorts.run, "lexical": lexical.run,
            "semantic": semantic.run, "analyze": analyze.run, "modnull": modnull.run, "distance": distance.run,
            "validation": validation.run, "layouts": layouts.run, "export": export.run}[stage]()


ORDER = ["fetch", "clean", "audit", "cohorts", "lexical", "semantic", "analyze", "modnull", "distance", "validation",
         "layouts", "export"]
ALWAYS = {"audit", "validation", "export"}  # cheap, or they must reflect files added since the last run


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m analysis", description=__doc__)
    ap.add_argument("stages", nargs="+", help=f"'all' or any of: {', '.join(ORDER)}")
    ap.add_argument("--force", action="store_true", help="rerun stages even when their inputs are unchanged")
    args = ap.parse_args(argv)
    stages = ORDER if args.stages == ["all"] else args.stages
    unknown = set(stages) - set(ORDER)
    if unknown:
        ap.error(f"unknown stage(s): {', '.join(sorted(unknown))}")
    STAMPS.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    for stage in [s for s in ORDER if s in stages]:
        stamp = STAMPS / f"{stage}.json"
        current = _inputs(stage, cfg)
        if not args.force and stage not in ALWAYS and stamp.exists() and read_json(stamp).get("inputs") == current:
            print(f"== {stage}: inputs unchanged, skipped (use --force to rerun)")
            continue
        print(f"== {stage}")
        t0 = time.time()
        _run_stage(stage)
        write_json(stamp, {"inputs": _inputs(stage, cfg), "seconds": round(time.time() - t0, 1)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
