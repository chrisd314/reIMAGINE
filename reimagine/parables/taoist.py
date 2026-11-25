"""Taoist parables: the Zhuangzi in James Legge's translation (Sacred Books of the East 39-40, 1891).
Baseline: the Tao Te Ching, same translator and volume. Both from sacred-texts.com.

Legge numbers the paragraphs of each of the 33 books ("1.", "2.", ...). One numbered paragraph,
with the unnumbered paragraphs that continue it, is one section. Sections that tell a story or
an anecdote with speech (reimagine.parables.narrative.is_story, without the exegesis test) are the
candidate parables; a seeded random draw of them is kept. Discursive sections are not used.
"""
from __future__ import annotations

import random
import re

from .http import Fetcher
from .narrative import features
from .sacred import Book, join_lines, roman

TRADITION = "Taoist"
ZHUANGZI = dict(tradition=TRADITION, source="The Writings of Kwang-dze (Sacred Books of the East 39-40)", translator="James Legge", year="1891")
TTC = dict(tradition=TRADITION, source="The Tâo Teh King (Sacred Books of the East 39)", translator="James Legge", year="1891")
NUMBERED = re.compile(r"^(\d{1,2})\.\s+(.*)$", re.S)
BOOK_SLUG = re.compile(r"^book-([ivxl]+)-")
BOOK_HEAD = re.compile(r"^BOOK\s+([IVXL]+)(?![A-Za-z])")
TRANSLATION = re.compile(r"^PART [IVX]+\. SECTION [IVX]+")        # heading carried by the translated books only

def sections(blocks) -> list[tuple[int, str]]:
    """(number, text) of each numbered section of one book of the Zhuangzi.

    A book that Legge does not divide (XXX and XXXI are one continuous story each) is one section.
    """
    out = []
    for b in blocks:
        if b.tag != "p":
            continue
        m = NUMBERED.match(b.text)
        if m:
            out.append([int(m.group(1)), m.group(2)])
        elif out:
            out[-1][1] += " " + b.text
        else:
            out.append([1, b.text])
    return [(n, join_lines(t)) for n, t in out]


def is_parable(text: str, min_tokens: int) -> bool:
    """A section with past-tense action and reported speech, or with a story opener and much action."""
    f = features(text)
    return f["tokens"] >= min_tokens and ((f["action"] >= 2.0 and f["speech"] >= 2) or (f["action"] >= 3.0 and f["openers"] >= 1))


def short_title(text: str, words: int = 9) -> str:
    w = text.split()
    return " ".join(w[:words]).rstrip(",;:-") + ("…" if len(w) > words else "")


def zhuangzi_sections(ctx, fetcher: Fetcher) -> list[dict]:
    out, seen = [], set()
    for key, url in (("sbe39", "https://www.sacred-texts.com/tao/sbe39/index.htm"),
                     ("sbe40", "https://www.sacred-texts.com/tao/sbe40/index.htm")):
        book = Book(fetcher, "taoist", key, url).open()
        for chap in [c for c in book.chapters if BOOK_SLUG.match(c)]:
            if ctx.sample and len(seen) >= 2:
                break
            blocks = book.blocks(chap)
            heads = [b.text for b in blocks if b.tag.startswith("h")]
            if not any(TRANSLATION.match(h) for h in heads):        # Legge's introductory notice of the book
                continue
            texts = heads + [b.text for b in blocks[:8]] + [chap.replace("-", " ").upper().replace("BOOK ", "BOOK ", 1)]
            number = next(roman(m.group(1).lower()) for t in texts if (m := BOOK_HEAD.match(t)))   # one slug is misnumbered
            if number in seen:
                continue
            seen.add(number)
            for n, text in sections(blocks):
                out.append(dict(book=number, section=n, text=text, **book.source(chap)))
    return sorted(out, key=lambda r: (r["book"], r["section"]))


def tao_te_ching_units(ctx, fetcher: Fetcher) -> list[dict]:
    """Numbered paragraphs of the 81 chapters; Legge's commentary under each chapter is left out."""
    book = Book(fetcher, "taoist", "sbe39", "https://www.sacred-texts.com/tao/sbe39/index.htm").open()
    units = []
    for chap in [c for c in book.chapters if re.fullmatch(r"chapter-\d+", c)][:(6 if ctx.sample else None)]:
        number = int(chap.split("-")[1])
        paragraphs = [b.text for b in book.blocks(chap) if b.tag == "p"]
        for k, text in enumerate(paragraphs):
            if k == 0:
                text = re.sub(r"^(?:Ch\. ?)?\d+\.\s*(?:\d{1,2}\.\s+)?", "", text)
            elif re.match(r"^\d{1,2}\.\s", text):
                text = re.sub(r"^\d{1,2}\.\s+", "", text)
            else:
                break               # the commentary on the chapter starts here
            units.append(dict(**TTC, **book.source(chap), group="ttc", label=f"Tâo Teh King {number}", text=join_lines(text)))
    return units


def collect(ctx, fetcher: Fetcher, is_duplicate):
    pc = ctx.paper["parables"]
    secs = zhuangzi_sections(ctx, fetcher)
    cand = [s for s in secs if is_parable(s["text"], pc["min_tokens"]) and len(s["text"].split()) <= pc["max_tokens"]]
    rng = random.Random(ctx.seed)
    target = min(len(cand), pc["targets"]["taoist"] if not ctx.sample else 5)
    keep = sorted(rng.sample(range(len(cand)), target))
    parables = [dict(**ZHUANGZI, url=s["url"], retrieved_at=s["retrieved_at"], key=f"{s['book']:02d}-{s['section']:02d}",
                     title=f"{short_title(s['text'])} (Zhuangzi, Book {s['book']}, section {s['section']})", text=s["text"],
                     segment_note=f"one numbered section; drawn from {len(cand)} story sections of {len(secs)}")
                for s in (cand[k] for k in keep)]
    skipped = [dict(tradition=TRADITION, item=f"{len(secs) - len(cand)} sections of the Zhuangzi",
                    reason="not a story by the action/speech rule (discursive), or outside the length limits"),
               dict(tradition=TRADITION, item=f"{len(cand) - len(keep)} story sections of the Zhuangzi",
                    reason=f"not drawn (seeded random draw of {target})")]
    return parables, tao_te_ching_units(ctx, fetcher), skipped
