"""Sufi teaching tales: Rumi's Masnavi in E. H. Whinfield's abridged translation (1898), sacred-texts.com.

Whinfield gives each story as a prose summary of the tale followed by translated couplets, most of
them the teaching that Rumi hangs on the tale, and by numbered notes. Per story:
  parable  = the prose summary (the long lines);
  baseline = the couplets (the short lines), later cut into length-matched passages;
  notes are dropped.
"""
from __future__ import annotations

import re

from .http import Fetcher
from .sacred import Book, join_lines, roman, strip_note_digits

TRADITION = "Sufi"
META = dict(tradition=TRADITION, source="Masnavi i Ma'navi, abridged", translator="E. H. Whinfield", year="1898")
STORY = re.compile(r"^STORY\s+([IVXLC]+)\.?\s*(.*)$")
OTHER_HEAD = re.compile(r"^(?:Epilogue|EPILOGUE|PROLOGUE|Prologue|Book\s+[IVX]+\.?|BOOK\s+[IVX]+\.?)")
NOTE = re.compile(r"^(?:NOTES?:?$|\d{1,3}\.\s)")
PROSE_MIN_WORDS = 23        # a line longer than a couplet line is prose


def stories(blocks) -> list[dict]:
    """One dict per story: number, title, prose lines and verse lines (notes removed)."""
    out, cur = [], None
    for b in blocks:
        lines = b.text.split("\n")
        m = STORY.match(lines[0])
        if m:
            title = m.group(2).strip() or (lines[1].strip() if len(lines) > 1 else "")
            cur = dict(number=m.group(1), title=title.rstrip("."), prose=[], verse=[])
            out.append(cur)
            lines = lines[1:] if m.group(2).strip() else lines[2:]
        elif OTHER_HEAD.match(lines[0]):
            cur = None
        if cur is None:
            continue
        in_notes = False
        for ln in lines:
            if NOTE.match(ln):
                in_notes = True
            if in_notes:            # notes close a block; text resumes in the next block
                continue
            (cur["prose"] if len(ln.split()) >= PROSE_MIN_WORDS else cur["verse"]).append(strip_note_digits(ln))
    return out


def collect(ctx, fetcher: Fetcher, is_duplicate, known_stories: set[tuple[int, int]] = frozenset()):
    pc = ctx.paper["parables"]
    book = Book(fetcher, "sufi", "masnavi", "https://www.sacred-texts.com/isl/masnavi/index.htm").open()
    parables, units, skipped = [], [], []
    for n, chap in enumerate(book.chapters[:1] if ctx.sample else book.chapters, start=1):
        book_no = ["I", "II", "III", "IV", "V", "VI"][n - 1]
        for s in stories(book.blocks(chap, lines=True)):
            where = f"Masnavi, Book {book_no}, Story {s['number']}"
            title = f"{s['title']} ({where})"
            text = join_lines(" ".join(s["prose"]))
            units += [dict(**META, **book.source(chap), group=f"book-{book_no}", label=where, text=v) for v in s["verse"]]
            if (n, roman(s["number"])) in known_stories:
                skipped.append(dict(tradition=TRADITION, item=title, reason="same story as a calibration version"))
                continue
            if not pc["min_tokens"] <= len(text.split()) <= pc["max_tokens"]:
                skipped.append(dict(tradition=TRADITION, item=title, reason=f"prose summary has {len(text.split())} tokens"))
                continue
            dup = is_duplicate(s["title"], text, join_lines(" ".join(s["prose"] + s["verse"])))
            if dup:
                skipped.append(dict(tradition=TRADITION, item=title, reason=dup))
                continue
            parables.append(dict(**META, **book.source(chap), key=f"{n}-{roman(s['number']):03d}", title=title, text=text,
                                 segment_note="Whinfield's prose summary of the tale; couplets and notes left out"))
    return parables, units, skipped
