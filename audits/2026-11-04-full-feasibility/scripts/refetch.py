"""Re-download every source logged in source_manifest_files.csv into a fresh folder and compare SHA-256 values.

Usage (from the audit folder): python -I -B scripts/refetch.py OUT_DIR [LIMIT]   (LIMIT: test with the first N plain URLs only)
Zip members read by range requests are re-extracted with remote_zip.py. Pages that are regenerated on the
server (course pages, D-PLACE, eBible) can legitimately differ; the report lists every mismatch.
"""
import hashlib
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import requests

UA = "OnceUponAWorld-feasibility-audit/1.0 (DTU 02805 student project; single polite requests)"
out = Path(sys.argv[1])
limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
m = pd.read_csv("source_manifest_files.csv")
ok = m[m.http_status.astype(str).isin(["200", "206"])]
rows = []
plain = ok[~ok.url.str.contains("#member=")]
for _, r in (plain.head(limit) if limit else plain).iterrows():
    dest = out / r.local_file
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        body = requests.get(r.url, headers={"User-Agent": UA}, timeout=180).content
        dest.write_bytes(body)
        h = hashlib.sha256(body).hexdigest()
    except requests.RequestException as e:
        h = f"error: {type(e).__name__}"
    rows.append(dict(url=r.url, recorded=r.sha256, now=h, same=h == r.sha256))
    time.sleep(1.0)
members = ok[ok.url.str.contains("#member=")]
if len(members) and not limit:
    base = members.url.iloc[0].split("#member=")[0]
    names = [u.split("#member=")[1] for u in members.url]
    tmp_manifest = out / "member_manifest.csv"
    subprocess.run([sys.executable, "-I", "-B", "scripts/remote_zip.py", base, "extract", str(out / "dataverse_mx/extracted"),
                    str(tmp_manifest), "dataverse_mx", *names], check=True)
    got = pd.read_csv(tmp_manifest, header=None).iloc[:, [1, 7]]
    for (_, r), (_, g) in zip(members.iterrows(), got.iterrows()):
        rows.append(dict(url=r.url, recorded=r.sha256, now=g.iloc[1], same=g.iloc[1] == r.sha256))
rep = pd.DataFrame(rows)
rep.to_csv(out / "refetch_report.csv", index=False)
print(f"{int(rep.same.sum())} of {len(rep)} files identical; differing: {rep[~rep.same].url.tolist()}")
