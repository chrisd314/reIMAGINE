"""Christian parables: the parables of Jesus in the World English Bible (public domain).

Verse ranges come from data/mappings/parables/christian_refs.yaml. Where a parable is told in
several Gospels, the longest telling is kept. Baseline: verses of Proverbs and the Epistles.
"""
from __future__ import annotations

import io
import re
import zipfile

import yaml

from ..common import REFS, n_tokens
from .http import Fetcher

URL = "https://ebible.org/Scriptures/engwebp_vpl.zip"
NAME = "engwebp_vpl.zip"
META = dict(tradition="Christian", source="World English Bible (eBible.org, engwebp)",
            translator="World English Bible editors (M. P. Johnson, ed.)", year="2020")
BOOK_NAMES = {"MAT": "Matthew", "MAR": "Mark", "LUK": "Luke", "PRO": "Proverbs", "ROM": "Romans", "1CO": "1 Corinthians",
              "2CO": "2 Corinthians", "GAL": "Galatians", "EPH": "Ephesians", "PHI": "Philippians", "COL": "Colossians",
              "1TH": "1 Thessalonians", "2TH": "2 Thessalonians", "1TI": "1 Timothy", "2TI": "2 Timothy", "TIT": "Titus",
              "PHM": "Philemon", "HEB": "Hebrews", "JAM": "James", "1PE": "1 Peter", "2PE": "2 Peter", "1JO": "1 John",
              "2JO": "2 John", "3JO": "3 John", "JUD": "Jude"}
REF = re.compile(r"^([A-Z0-9]{3}) (\d+):(\d+)(?:-(\d+))?$")


def load_verses(fetcher: Fetcher) -> dict[tuple[str, int, int], str]:
    data = fetcher.get("christian", NAME, URL, binary=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        text = z.read(next(n for n in z.namelist() if n.endswith("_vpl.txt"))).decode("utf-8-sig")
    verses = {}
    for line in text.splitlines():
        m = re.match(r"^([A-Z0-9]{3}) (\d+):(\d+) (.*)$", line)
        if m:
            verses[(m.group(1), int(m.group(2)), int(m.group(3)))] = m.group(4).strip()
    return verses


def passage(verses: dict, ref: str) -> str:
    book, chapter, first, last = REF.match(ref).groups()
    return " ".join(verses[(book, int(chapter), v)] for v in range(int(first), int(last or first) + 1))


def pretty(ref: str) -> str:
    book, rest = ref.split(" ", 1)
    return f"{BOOK_NAMES[book]} {rest}"


def collect(ctx, fetcher: Fetcher):
    refs = yaml.safe_load((REFS / "christian_refs.yaml").read_text(encoding="utf-8"))
    verses = load_verses(fetcher)
    info = fetcher.info("christian", NAME)
    src = dict(url=info["final_url"], retrieved_at=info["retrieved_at"])
    parables = []
    for k, p in enumerate(refs["parables"]):
        texts = {ref: passage(verses, ref) for ref in p["versions"]}
        best = max(texts, key=lambda r: (n_tokens(texts[r]), -p["versions"].index(r)))
        others = [pretty(r) for r in p["versions"] if r != best]
        note = f"{pretty(best)}" + (f"; longest of {len(texts)} tellings (not used: {', '.join(others)})" if others else "")
        parables.append(dict(**META, **src, key=f"{k:03d}", title=f"{p['title']} ({pretty(best)})", text=texts[best],
                             segment_note=note))
    units = [dict(**META, **src, group=book, label=f"{BOOK_NAMES[book]} {c}:{v}", text=t)
             for (book, c, v), t in verses.items() if book in set(refs["baseline_books"])]
    return parables, units
