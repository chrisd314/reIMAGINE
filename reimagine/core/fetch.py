"""Stage 1: download pinned source files once, hash them, and record a manifest.

Raw files are immutable: an existing file whose SHA-256 matches the manifest is
kept as is. Nothing here executes downloaded content.
"""
from __future__ import annotations

import time

import requests

from .common import RAW, load_config, read_json, sha256_file, utc_now, write_json

MANIFEST = RAW / "source_manifest.json"
USER_AGENT = "reIMAGINE-course-project/1.0 (DTU 02805; polite single-file downloads)"


def _download(url: str, attempts: int = 3, timeout: int = 60) -> bytes:
    last = None
    for i in range(attempts):
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
            if r.status_code == 200:
                return r.content
            last = RuntimeError(f"HTTP {r.status_code} for {url}")
        except requests.RequestException as exc:  # network hiccup: bounded retry
            last = exc
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"failed to download {url}: {last}")


def run(force: bool = False) -> dict:
    cfg = load_config()
    src_cfg = cfg["sources"]
    commit = src_cfg["trilogy_commit"]
    old = {e["filename"]: e for e in read_json(MANIFEST)["files"]} if MANIFEST.exists() else {}

    entries = []
    for item in src_cfg["files"]:
        url = item["url"].replace("{commit}", commit)
        dest = RAW / item["filename"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        prev = old.get(item["filename"])
        if dest.exists() and prev and not force and sha256_file(dest) == prev["sha256"]:
            # descriptive fields come from config so documentation fixes propagate
            prev.update({k: item[k] for k in ("format", "role", "citation", "stated_licence")})
            entries.append(prev)
            print(f"  kept   {item['filename']} (hash verified)")
            continue
        content = _download(url)
        dest.write_bytes(content)
        entry = {
            "filename": item["filename"],
            "url": url,
            "version": commit if "{commit}" in item["url"] else item.get("version", "snapshot at retrieval time"),
            "retrieved_at": utc_now(),
            "sha256": sha256_file(dest),
            "bytes": dest.stat().st_size,
            "format": item["format"],
            "role": item["role"],
            "citation": item["citation"],
            "stated_licence": item["stated_licence"],
        }
        entries.append(entry)
        print(f"  fetched {item['filename']} ({entry['bytes']:,} bytes)")
        time.sleep(1.0)  # be gentle with the hosts

    manifest = {
        "description": "Immutable raw inputs for reIMAGINE. URLs pin the trilogy repository commit.",
        "trilogy_repository": src_cfg["trilogy_repository"],
        "trilogy_commit": commit,
        "files": entries,
    }
    write_json(MANIFEST, manifest)
    return manifest


if __name__ == "__main__":
    run()
