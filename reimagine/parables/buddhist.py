"""Buddhist parables: Jātaka birth stories (Cowell, ed., 1895-1907) and the parables of the
Lotus Sutra (Kern 1884). Baseline: the Dhammapada (Müller 1881). All from sacred-texts.com.

A Jātaka has a "story of the present" (why the Buddha told it), the "story of the past" (the tale)
and a closing identification of the births. Only the story of the past is kept when its opening
and its end can both be located. Otherwise the whole text is kept and `segment_note` says so.
"""
from __future__ import annotations

import random
import re

import yaml

from ..common import REFS, n_tokens
from .html import Block
from .http import Fetcher
from .sacred import Book, join_lines

TRADITION = "Buddhist"
JATAKA = {  # volume: (translator, year)
    1: ("Robert Chalmers", "1895"), 2: ("W. H. D. Rouse", "1895"), 3: ("H. T. Francis and R. A. Neil", "1897"),
    4: ("W. H. D. Rouse", "1901"), 5: ("H. T. Francis", "1905"), 6: ("E. B. Cowell and W. H. D. Rouse", "1907")}
N_JATAKA = 547

SEPARATOR = re.compile(r"_{20,}")                       # printed rule around the story of the past (volumes 1-2)
PALI_PAGE = re.compile(r"\[\d+\.?\]\s*")                # page of the Pali edition
OPENING = re.compile(r"Once (?:up)?on a time|In (?:days|times) (?:gone by|of (?:old|yore)|past)|In bygone days|Long ago")
CLOSING = re.compile(
    r"(?:lesson|discourse|story|teaching|address|exposition)\b[^.]{0,60}\b(?:ended|end|concluded)\b"
    r"|\b(?:ended|concluded|finished) (?:his|this|the) (?:lesson|discourse|story|teaching)"
    r"|identif(?:ied|ying) the Birth|she?wed the connexion|made the connexion|summed up the (?:Birth|Jātaka)")
EDITOR_NOTE = re.compile(r"^\[(?:Note|Cf\.|Compare|See)\b")
LOTUS_STOP = re.compile(r"^(?:He proceeded: )?(?:In the same manner|Even so|Such, [^,]{1,40}, is the parable"
                        r"|Now, [^.?!]{0,60}what is (?:thy|your) opinion)")


def segment_jataka(blocks: list[Block]) -> tuple[str, str]:
    """(text, segment_note) for one Jātaka page: the story of the past, or the whole text with a note."""
    body = []
    for b in blocks:
        if b.tag.startswith("h"):
            continue
        # a printed rule can share a block with the text after it: make it an item of its own
        for piece in re.split(r"(_{20,})", PALI_PAGE.sub("", b.text)):
            if piece.strip():
                body.append(piece.strip())
    while body and EDITOR_NOTE.match(body[-1]):
        body.pop()
    start = next((k for k, t in enumerate(body) if OPENING.match(t)), None)
    if start is None:
        whole = [t for t in body if not SEPARATOR.fullmatch(t)]
        return join_lines(" ".join(whole)), "whole text kept: no opening of a story of the past found"
    rule = next((k for k in range(start + 1, len(body)) if SEPARATOR.fullmatch(body[k])), None)
    close = next((k for k in range(start + 1, len(body)) if CLOSING.search(body[k])), None)
    ends = [k for k in (rule, close) if k is not None]
    if not ends:
        whole = [t for t in body if not SEPARATOR.fullmatch(t)]
        return join_lines(" ".join(whole)), "whole text kept: end of the story of the past not found"
    story = [t for t in body[start:min(ends)] if not SEPARATOR.fullmatch(t)]
    return join_lines(" ".join(story)), ""


def jataka_title(h1: str) -> tuple[str, int | None]:
    m = re.match(r"No\.\s*(\d+)\.?:?\s*(.*)", h1)
    if not m:
        return h1, None
    return f"{m.group(2).strip(' .')} (Jātaka {m.group(1)})", int(m.group(1))


def collect_jataka(ctx, fetcher: Fetcher, is_duplicate, known_numbers: set[int]):
    pc = ctx.analysis["parables"]
    where = {}                                                  # Jātaka number -> (volume, book, chapter slug)
    for v in JATAKA:
        book = Book(fetcher, "buddhist", f"j{v}", f"https://www.sacred-texts.com/bud/j{v}/index.htm").open()
        for c in book.chapters:
            m = re.match(r"no-(\d+)(?:-|$)", c)
            if m and 1 <= int(m.group(1)) <= N_JATAKA:
                where.setdefault(int(m.group(1)), (v, book, c))
    order = sorted(where)
    random.Random(ctx.seed).shuffle(order)                      # a seeded random draw from all birth stories
    target = pc["targets"]["buddhist_jataka"] if not ctx.sample else min(8, pc["targets"]["buddhist_jataka"])
    parables, skipped = [], []
    for number in order:
        if len(parables) >= target:
            break
        v, book, chap = where[number]
        if number in known_numbers:
            skipped.append(dict(tradition=TRADITION, item=f"Jātaka {number}", reason="same birth story as a calibration version"))
            continue
        blocks = book.blocks(chap)
        heading = next((b.text for b in blocks if b.tag == "h1"), chap)
        title, _ = jataka_title(heading)
        text, note = segment_jataka(blocks)
        n = n_tokens(text)
        if not pc["min_tokens"] <= n <= pc["max_tokens"]:
            skipped.append(dict(tradition=TRADITION, item=title, reason=f"{n} tokens (outside {pc['min_tokens']}-{pc['max_tokens']})"))
            continue
        dup = is_duplicate(title, text)
        if dup:
            skipped.append(dict(tradition=TRADITION, item=title, reason=dup))
            continue
        translator, year = JATAKA[v]
        parables.append(dict(tradition=TRADITION, source=f"The Jātaka, vol. {v} (ed. E. B. Cowell)", translator=translator,
                             year=year, key=f"jataka-{number:03d}", title=title, text=text, segment_note=note,
                             **book.source(chap)))
    return parables, skipped


def lotus_parable(blocks: list[Block], start: str) -> str:
    k = next(i for i, b in enumerate(blocks) if b.text.startswith(start))
    out = []
    for b in blocks[k:]:
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", b.text):
            if out and LOTUS_STOP.match(s):
                return " ".join(out)
            out.append(s)
    return " ".join(out)


def collect_lotus(ctx, fetcher: Fetcher):
    refs = yaml.safe_load((REFS / "buddhist_lotus_refs.yaml").read_text(encoding="utf-8"))["parables"]
    book = Book(fetcher, "buddhist", "lotus", "https://www.sacred-texts.com/bud/lotus/index.htm").open()
    out = []
    for k, r in enumerate(refs[:2] if ctx.sample else refs):
        chap = f"chapter-{r['chapter']}"
        text = lotus_parable(book.blocks(chap), r["start"])
        out.append(dict(tradition=TRADITION, source="Saddharma-Puṇḍarīka, or the Lotus of the True Law (Sacred Books of the East 21)",
                        translator="H. Kern", year="1884", key=f"lotus-{k:02d}", title=f"{r['title']} (Lotus Sutra, ch. {r['chapter']})",
                        text=text, segment_note="prose parable up to the speaker's application", **book.source(chap)))
    return out


def dhammapada_units(ctx, fetcher: Fetcher) -> list[dict]:
    book = Book(fetcher, "buddhist", "dhp", "https://www.sacred-texts.com/bud/sbe10/index.htm").open()
    chapters = [c for c in book.chapters if re.match(r"chapter-[ivxl]+-", c)]       # the 26 chapters of the Dhammapada
    units = []
    for c in (chapters[:3] if ctx.sample else chapters):
        for b in book.blocks(c):
            m = re.match(r"(\d+)\.\s+(.*)", b.text)
            if b.tag == "p" and m:
                units.append(dict(tradition=TRADITION, source="The Dhammapada (Sacred Books of the East 10)", translator="F. Max Müller",
                                  year="1881", group="dhammapada", label=f"Dhammapada {m.group(1)}", text=m.group(2), **book.source(c)))
    return units


def collect(ctx, fetcher: Fetcher, is_duplicate, known_numbers: set[int]):
    jataka, skipped = collect_jataka(ctx, fetcher, is_duplicate, known_numbers)
    return jataka + collect_lotus(ctx, fetcher), dhammapada_units(ctx, fetcher), skipped
