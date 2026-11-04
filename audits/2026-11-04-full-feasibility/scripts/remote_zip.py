"""List or extract members of a large remote ZIP with HTTP range requests (no full download).

Usage:
  python -I -B remote_zip.py URL list OUT_CSV
  python -I -B remote_zip.py URL extract OUT_DIR MANIFEST_CSV SOURCE_ID MEMBER [MEMBER ...]
Extracted members are written as data only and logged in the source manifest with their SHA-256.
"""
import csv
import hashlib
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

import requests

UA = "OnceUponAWorld-feasibility-audit/1.0 (DTU 02805 student project; range requests)"
url, mode = sys.argv[1], sys.argv[2]
s = requests.Session()
s.headers["User-Agent"] = UA


def rng(a, b):
    r = s.get(url, headers={"Range": f"bytes={a}-{b}"}, timeout=300)
    assert r.status_code == 206, r.status_code
    return r.content


head = s.get(url, headers={"Range": "bytes=0-0"}, timeout=120)
total = int(head.headers["Content-Range"].split("/")[1])
tail = rng(max(0, total - 70000), total - 1)
i = tail.rfind(b"PK\x05\x06")
_, _, _, _, n_total, cd_size, cd_off, _ = struct.unpack("<IHHHHIIH", tail[i:i + 22])
if cd_off == 0xFFFFFFFF or n_total == 0xFFFF or cd_size == 0xFFFFFFFF:
    j = tail.rfind(b"PK\x06\x07")
    _, _, z64_off, _ = struct.unpack("<IIQI", tail[j:j + 20])
    z = rng(z64_off, z64_off + 55)
    cd_size, cd_off = struct.unpack("<QQ", z[40:56])
cd = rng(cd_off, cd_off + cd_size - 1)
entries, p = [], 0
while p < len(cd) and cd[p:p + 4] == b"PK\x01\x02":
    (_, _, flag, method, _, _, crc, csize, usize, fnlen, exlen, cmlen, _, _, _, lho) = struct.unpack(
        "<HHHHHHIIIHHHHHII", cd[p + 4:p + 46])
    raw = cd[p + 46:p + 46 + fnlen]
    name = raw.decode("utf-8" if flag & 0x800 else "cp437")
    extra = cd[p + 46 + fnlen:p + 46 + fnlen + exlen]
    q = 0
    while q + 4 <= len(extra):
        hid, hsz = struct.unpack("<HH", extra[q:q + 4])
        data, k = extra[q + 4:q + 4 + hsz], 0
        if hid == 1:
            if usize == 0xFFFFFFFF:
                usize = struct.unpack("<Q", data[k:k + 8])[0]; k += 8
            if csize == 0xFFFFFFFF:
                csize = struct.unpack("<Q", data[k:k + 8])[0]; k += 8
            if lho == 0xFFFFFFFF:
                lho = struct.unpack("<Q", data[k:k + 8])[0]; k += 8
        q += 4 + hsz
    entries.append(dict(name=name, method=method, csize=csize, usize=usize, lho=lho, crc=crc))
    p += 46 + fnlen + exlen + cmlen

if mode == "list":
    with open(sys.argv[3], "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "usize", "csize", "method", "lho", "crc"])
        w.writeheader()
        w.writerows(entries)
    print(f"{len(entries)} members, archive {total} bytes")
    for e in entries:
        print(f"{e['usize']:>12d}  {e['name']}")
else:
    out, manifest, sid = Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
    want = sys.argv[6:]
    by = {e["name"]: e for e in entries}
    for m in want:
        e = by[m]
        h = rng(e["lho"], e["lho"] + 29)
        fnlen, exlen = struct.unpack("<HH", h[26:30])
        start = e["lho"] + 30 + fnlen + exlen
        comp = rng(start, start + e["csize"] - 1) if e["csize"] else b""
        data = zlib.decompressobj(-15).decompress(comp) if e["method"] == 8 else comp
        assert len(data) == e["usize"] and (zlib.crc32(data) & 0xFFFFFFFF) == e["crc"], m
        dest = out / Path(m).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        row = dict(source_id=sid, url=f"{url.split('?')[0]}#member={m}", final_url="(range request)",
                   retrieved_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                   http_status=206, content_type="zip member", bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                   local_file=dest.relative_to(out.parent.parent).as_posix())
        with open(manifest, "a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=list(row)).writerow(row)
        print(f"extracted {m} ({len(data)} bytes, CRC ok)")
