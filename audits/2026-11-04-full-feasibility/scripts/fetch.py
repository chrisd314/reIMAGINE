"""Download one URL into downloads/<source_id>/ and append provenance to the source manifest.

Usage: python -I -B fetch.py DOWNLOADS_DIR MANIFEST_CSV SOURCE_ID URL [FILENAME]
Downloaded content is stored as data only; nothing downloaded is executed.
"""
import csv
import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

UA = "OnceUponAWorld-feasibility-audit/1.0 (DTU 02805 student project; single polite requests)"
dl, manifest, sid, url = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
name = sys.argv[5] if len(sys.argv) > 5 else (Path(urlparse(url).path).name or "index.html")
dest = dl / sid / name
dest.parent.mkdir(parents=True, exist_ok=True)
t = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
try:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=120, allow_redirects=True)
    status, ctype, final, body = r.status_code, r.headers.get("content-type", ""), r.url, r.content
except requests.RequestException as e:
    status, ctype, final, body = f"error: {type(e).__name__}", "", url, b""
if body:
    dest.write_bytes(body)
row = dict(source_id=sid, url=url, final_url=final, retrieved_utc=t, http_status=status, content_type=ctype,
           bytes=len(body), sha256=hashlib.sha256(body).hexdigest() if body else "", local_file=dest.relative_to(dl.parent).as_posix() if body else "")
new = not manifest.exists()
with open(manifest, "a", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(row))
    if new:
        w.writeheader()
    w.writerow(row)
print(f"{sid:22s} {status} {len(body):>9d} B  {name}")
time.sleep(1.0)
