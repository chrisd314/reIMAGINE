"""Shared paths, configuration, hashing and I/O helpers."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
MAPPINGS = DATA / "mappings"
AUDIT = ROOT / "results" / "corpus_audit"   # audit tables of the data preparation (cleaning log, inclusion ledger, ...)


def load_config(path: Path | None = None) -> dict:
    with open(path or ROOT / "config.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def content_hash(path: Path) -> str:
    """SHA-256 of a file's content. For .npz archives, of the arrays themselves.

    Hashing names, dtypes, shapes and raw bytes keeps stamps and run IDs independent of
    how an archive was written (compression, zip metadata, library version).
    """
    if path.suffix != ".npz":
        return sha256_file(path)
    h = hashlib.sha256()
    with np.load(path, allow_pickle=False) as z:
        for key in sorted(z.files):
            a = np.ascontiguousarray(z[key])
            h.update(f"{key}|{a.dtype.str}|{a.shape}".encode())
            h.update(a.tobytes())
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_hash(obj: Any, length: int = 12) -> str:
    """Hash of a JSON-serialisable object, independent of dict ordering."""
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:length]


def _json_default(o: Any):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return None if math.isnan(v) else v
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, Path):
        return o.as_posix()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def _nan_to_none(obj: Any):
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: _nan_to_none(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_nan_to_none(v) for v in obj]
    return obj


def write_json(path: Path, obj: Any, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    obj = _nan_to_none(obj)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        if compact:
            json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"), default=_json_default, allow_nan=False)
        else:
            json.dump(obj, fh, ensure_ascii=False, indent=2, default=_json_default, allow_nan=False)
            fh.write("\n")


def read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
