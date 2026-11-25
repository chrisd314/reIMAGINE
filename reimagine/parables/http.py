"""Polite, cached downloads for the parable sources.

One request per second at most. Every page is stored once, gzip-compressed, under
data/raw/parables/<tradition>/ and never requested again. Each download is logged in
data/raw/parables/fetch_log.csv with its URL, final URL, UTC time, HTTP status, size and SHA-256.
A page that cannot be downloaded raises SourceBlocked. Nothing is retried by another route.
Downloading is off unless it is switched on explicitly. Without it only the cache is read.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import time

import requests

from ..core.common import utc_now

from ..common import RAW_PARABLES

LOG = RAW_PARABLES / "fetch_log.csv"
FIELDS = ["tradition", "name", "url", "final_url", "retrieved_at", "http_status", "bytes", "sha256", "local_file"]


class SourceBlocked(RuntimeError):
    """A source page could not be downloaded."""


class CacheMiss(RuntimeError):
    """A page is not in the cache and downloading has not been switched on."""


class Fetcher:
    """`allow_fetch` must be switched on explicitly (python -m reimagine.run --fetch) before anything is
    downloaded. The terms of sacred-texts.com ask users not to scrape the site, so the default is to
    work from the cache only. See README.md, "Data sources"."""

    def __init__(self, user_agent: str, delay: float = 1.0, allow_fetch: bool = False):
        self.user_agent, self.delay, self._last, self.allow_fetch = user_agent, delay, 0.0, allow_fetch
        self._log: dict[tuple[str, str], dict] = {}
        if LOG.exists():
            with open(LOG, encoding="utf-8", newline="") as fh:
                self._log = {(r["tradition"], r["name"]): r for r in csv.DictReader(fh)}

    def _append(self, row: dict) -> None:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        new = not LOG.exists()
        with open(LOG, "a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
            if new:
                w.writeheader()
            w.writerow(row)
        self._log[(row["tradition"], row["name"])] = row

    def info(self, tradition: str, name: str) -> dict:
        """Log row of a cached page (final URL and retrieval time)."""
        return self._log[(tradition, name)]

    def get(self, tradition: str, name: str, url: str, binary: bool = False):
        """Content of `url`, from the cache when present. `name` is the cache file stem."""
        path = RAW_PARABLES / tradition / f"{name}.gz"
        if path.exists() and (tradition, name) in self._log:
            data = gzip.decompress(path.read_bytes())
            return data if binary else data.decode("utf-8", errors="replace")
        if not self.allow_fetch:
            raise CacheMiss(f"{tradition}/{name} is not in data/raw/parables/ and downloading is off ({url})")
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        try:
            r = requests.get(url, headers={"User-Agent": self.user_agent}, timeout=90, allow_redirects=True)
            status, final, body = r.status_code, r.url, r.content
        except requests.RequestException as e:
            status, final, body = f"error: {type(e).__name__}", url, b""
        self._last = time.monotonic()
        ok = status == 200 and len(body) > 0
        if ok:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.compress(body, mtime=0))
        self._append(dict(tradition=tradition, name=name, url=url, final_url=final, retrieved_at=utc_now(),
                          http_status=status, bytes=len(body), sha256=hashlib.sha256(body).hexdigest() if body else "",
                          local_file=path.relative_to(RAW_PARABLES).as_posix() if ok else ""))
        if not ok:
            raise SourceBlocked(f"{url} -> {status}")
        return body if binary else body.decode("utf-8", errors="replace")
