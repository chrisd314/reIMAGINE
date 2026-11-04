"""Count, per Jataka, editor/translator notes that cite Western or Indian fable parallels (data only)."""
import collections
import html
import re
import sys
import zipfile

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
z = zipfile.ZipFile(sys.argv[1])
PAR = re.compile(r"Aesop|Æsop|Esop|Babrius|Phaedrus|La Fontaine|Lafontaine|Panchatantra|Pañcatantra|Pancatantra|Benfey|Hitopadesa|Hitopadeśa|Kalilah|Bidpai|Pilpay|Gesta Romanorum|Arabian Nights|Thousand and One|1001 Nights|Grimm|Jacobs", re.I)
HEAD = re.compile(r"Ja\s?(\d{1,3})\b")
rows = []
for n in sorted(z.namelist()):
    if not n.endswith(("htm", "html", "xhtml")):
        continue
    h = z.read(n).decode("utf-8", "replace")
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"\s+", " ", t)
    heads = [(m.start(), int(m.group(1))) for m in re.finditer(r"(?:^|\s)Ja (\d{1,3}) [A-ZĀĪŪṬḌṆÑṄṀa-zāīūṭḍṇñṅṁ]+jātaka", t)]
    for m in PAR.finditer(t):
        cur = [j for p, j in heads if p <= m.start()]
        rows.append(dict(file=n, ja=cur[-1] if cur else None, term=m.group(0), ctx=t[max(0, m.start() - 120): m.end() + 80]))
df = pd.DataFrame(rows)
df.to_csv(sys.argv[2], index=False)
per = df.dropna(subset=["ja"]).groupby("ja").term.apply(lambda x: sorted(set(s.lower() for s in x)))
print(f"mentions: {len(df)}; attributed to a Jataka: {df.ja.notna().sum()}; distinct Jatakas with a cited parallel: {per.shape[0]}")
fam = collections.Counter()
for terms in per:
    s = " ".join(terms)
    fam["Aesop/Babrius/Phaedrus/La Fontaine"] += bool(re.search(r"aesop|æsop|esop|babrius|phaedrus|fontaine", s))
    fam["Panchatantra/Hitopadesa/Kalilah/Bidpai/Benfey"] += bool(re.search(r"tantra|benfey|hitopade|kalilah|bidpai|pilpay", s))
    fam["Gesta/Arabian Nights/Grimm/Jacobs"] += bool(re.search(r"gesta|arabian|thousand|1001|grimm|jacobs", s))
print(dict(fam))
print("unattributed examples:", df[df.ja.isna()].ctx.head(3).tolist())
print(df.dropna(subset=["ja"]).drop_duplicates("ja").head(12)[["ja", "term", "ctx"]].to_string(max_colwidth=150))
