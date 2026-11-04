"""Hash every project file (excluding environments, caches and the audit directory) for a before/after comparison."""
import csv, hashlib, os, sys
root, out = sys.argv[1], sys.argv[2]
SKIP_DIRS = {".git", ".venv", "node_modules", ".tools", ".cache", "__pycache__", ".pytest_cache", ".vite", "audits"}
rows = []
for dp, dns, fns in os.walk(root):
    dns[:] = [d for d in dns if d not in SKIP_DIRS]
    for fn in fns:
        p = os.path.join(dp, fn)
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b)
        rows.append((os.path.relpath(p, root).replace(os.sep, "/"), os.path.getsize(p), h.hexdigest()))
rows.sort()
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["path", "bytes", "sha256"]); w.writerows(rows)
print(f"{len(rows)} files, {sum(r[1] for r in rows)/1e6:.1f} MB hashed")
