"""Parse the downloaded Jataka table (ancient-buddhist-texts.net) into rows; report keyword coverage."""
import collections
import csv
import html
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
raw = open(sys.argv[1], encoding="utf-8").read().replace("\r", "")
cells = re.findall(r"<tr><td>(.*?)</td></tr>", raw, flags=re.S)


def text(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


rows = []
for c in cells:
    paras = [text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", c, flags=re.S)]
    if not paras or not paras[0].startswith("Ja "):
        continue
    head = paras[0].split("\n")
    m = re.match(r"Ja (\d+)\S*\s*(.*)", head[0])
    if not m:
        print("unparsed head:", head[0][:80])
        continue
    num, pali = int(m.group(1)), m.group(2).strip()
    eng = head[1].strip() if len(head) > 1 else ""
    syn = next((p for p in paras if p.startswith("In the present") or p.startswith("In the past")), "")
    ident = [p for p in paras if "=" in p and "Bodhisatta" in p]
    kw = next((p for p in paras if p.startswith("Keywords:")), "")
    kws = [k.strip(" .") for k in kw[len("Keywords:"):].split(",") if k.strip(" .")]
    par = [p for p in paras if re.match(r"(Past|Present|Quoted|Parallel|Compare|Similar|Text|Story)\b", p)]
    rows.append(dict(ja=num, pali=pali, english_title=eng, synopsis=syn, n_syn_words=len(syn.split()),
                     identifications=" | ".join(ident).replace("\n", " "), parallels=" | ".join(par).replace("\n", " "),
                     keywords="; ".join(kws), aesop_mentioned="Aesop" in c or "Æsop" in c))

with open(sys.argv[2], "w", encoding="utf-8", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

TAGS = {"Animals", "Birds", "Fish", "Devas", "Women", "Nāgas", "Yakkhas", "Snakes", "Insects", "Supernormal Powers"}
cnt = collections.Counter(k for r in rows for k in r["keywords"].split("; ") if k)
moral = collections.Counter({k: v for k, v in cnt.items() if k not in TAGS})
print(f"rows parsed: {len(rows)} (Ja {min(r['ja'] for r in rows)}-{max(r['ja'] for r in rows)}); unique numbers {len({r['ja'] for r in rows})}")
print(f"with synopsis: {sum(bool(r['synopsis']) for r in rows)}; synopsis words median {sorted(r['n_syn_words'] for r in rows)[len(rows)//2]}")
print(f"with keywords: {sum(bool(r['keywords']) for r in rows)}; with Bodhisatta identification: {sum(bool(r['identifications']) for r in rows)}")
print(f"with parallels listed: {sum(bool(r['parallels']) for r in rows)}; mentioning Aesop: {sum(r['aesop_mentioned'] for r in rows)}")
print(f"distinct keywords: {len(cnt)}; distinct non-category keywords: {len(moral)}")
per = [len([k for k in r['keywords'].split('; ') if k and k not in TAGS]) for r in rows]
print("non-category keywords per story:", dict(sorted(collections.Counter(per).items())))
print("top category tags:", [(k, cnt[k]) for k in TAGS if cnt[k]])
print("top 45 non-category keywords:", moral.most_common(45))
print("keywords used once:", sum(1 for v in moral.values() if v == 1))
for n in (1, 38, 136, 144, 189, 215, 316, 381, 468):
    r = next((x for x in rows if x["ja"] == n), None)
    if r:
        print(f"\nJa {n} {r['pali']} | {r['english_title']}\n  synopsis: {r['synopsis'][:330]}\n  keywords: {r['keywords']}\n  parallels: {r['parallels'][:200]}")
