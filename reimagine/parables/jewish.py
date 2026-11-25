"""Jewish teaching tales: S. Rapaport, Tales and Maxims from the Midrash (1907), sacred-texts.com.

The book lists short passages, each closed by its source ("--Gen. Rabba 22."). A passage is one
item. Items that tell a story (reimagine.parables.narrative.is_story) are the parables. Short items
without action or speech are the book's maxims and, with the sayings of Pirqe Aboth (Taylor
1897), form the baseline. The two long retold legend cycles at the front of the book (Alexander
of Macedon, Ashmedai) carry no source citations to cut them by and are not used.
"""
from __future__ import annotations

import re

from .http import Fetcher
from .narrative import is_saying, is_story
from .sacred import Book

TRADITION = "Jewish"
REFERENCE = re.compile(r"\s*--\s*\.?([A-Z][\w .'’()&,]{2,70}?)\.?\s*$")
STORY_MIN_TOKENS = 60       # shorter cited items are sayings with a narrative clause, not stories
SKIP = {"title-page", "contents", "introduction", "alexander-of-macedon", "ashmedai-the-king-of-demons"}
MIDRASH = dict(tradition=TRADITION, source="Tales and Maxims from the Midrash", translator="Samuel Rapaport", year="1907")
AVOT = dict(tradition=TRADITION, source="Sayings of the Jewish Fathers (Pirqe Aboth)", translator="Charles Taylor", year="1897")


def midrash_items(paragraphs: list[str]) -> list[tuple[str, str]]:
    """(text, reference) per item. Paragraphs are joined until one ends with a source reference."""
    items, cur = [], []
    for p in paragraphs:
        m = REFERENCE.search(p)
        if m:
            cur.append(p[:m.start()].strip())
            items.append((" ".join(x for x in cur if x), m.group(1).strip()))
            cur = []
        else:
            cur.append(p)
    return items


def short_title(text: str, words: int = 8) -> str:
    w = text.split()
    return " ".join(w[:words]).rstrip(",;:") + ("…" if len(w) > words else "")


def collect(ctx, fetcher: Fetcher, is_duplicate):
    pc = ctx.analysis["parables"]
    book = Book(fetcher, "jewish", "midrash", "https://www.sacred-texts.com/jud/tmm/index.htm").open()
    chapters = [c for c in book.chapters if c not in SKIP]
    parables, units, skipped = [], [], []
    for c in (chapters[:3] if ctx.sample else chapters):
        src = None
        for k, (text, ref) in enumerate(midrash_items([b.text for b in book.blocks(c) if b.tag == "p"])):
            src = src or book.source(c)
            if is_story(text, max(STORY_MIN_TOKENS, pc["min_tokens"])) and len(text.split()) <= pc["max_tokens"]:
                title = f"{short_title(text)} ({ref})"
                dup = is_duplicate(title, text)
                if dup:
                    skipped.append(dict(tradition=TRADITION, item=title, reason=dup))
                    continue
                parables.append(dict(**MIDRASH, **src, key=f"{chapters.index(c):02d}-{k:03d}", title=title, text=text,
                                     segment_note="one cited item; story by the action/speech rule"))
            elif is_saying(text):
                units.append(dict(**MIDRASH, **src, group="midrash", label=ref, text=text))
    avot = Book(fetcher, "jewish", "avot", "https://www.sacred-texts.com/jud/sjf/index.htm").open()
    for c in [c for c in avot.chapters if re.fullmatch(r"chapter-[ivx]+", c)][:(2 if ctx.sample else None)]:
        for b in avot.blocks(c):
            m = re.match(r"(\d+)\.\s+(.*)", b.text)
            if b.tag == "p" and m:
                units.append(dict(**AVOT, **avot.source(c), group="avot", label=f"Aboth {c.split('-')[1].upper()}.{m.group(1)}",
                                  text=m.group(2)))
    return parables, units, skipped
