"""Books on sacred-texts.com: chapter lists and chapter pages, through the polite cache."""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import html
from .http import Fetcher

SITE = "https://sacred-texts.com"


@dataclass
class Book:
    fetcher: Fetcher
    tradition: str      # cache folder
    key: str            # short name used in cache file names
    index_url: str      # the book's index address (old addresses redirect to /book/<slug>)
    slug: str = ""
    chapters: list[str] = None

    def open(self) -> "Book":
        """Resolve the book's address and read its chapter list from one reader page."""
        self.fetcher.get(self.tradition, f"{self.key}__index", self.index_url)
        final = self.fetcher.info(self.tradition, f"{self.key}__index")["final_url"]
        self.slug = final.split("/book/")[1].split("?")[0].strip("/")
        index = self.fetcher.get(self.tradition, f"{self.key}__index", self.index_url)
        first = html.chapter_slugs(index, self.slug)[0]
        self.chapters = html.chapter_slugs(self.page(first), self.slug)
        return self

    def name(self, chapter: str) -> str:
        return f"{self.key}__{chapter}"[:110]

    def url(self, chapter: str) -> str:
        return f"{SITE}/book/{self.slug}/{chapter}"

    def page(self, chapter: str) -> str:
        return self.fetcher.get(self.tradition, self.name(chapter), self.url(chapter))

    def blocks(self, chapter: str, lines: bool = False) -> list[html.Block]:
        return html.blocks(self.page(chapter), lines)

    def source(self, chapter: str) -> dict:
        """URL and retrieval time of a chapter page, for parables.csv."""
        info = self.fetcher.info(self.tradition, self.name(chapter))
        return dict(url=info["final_url"], retrieved_at=info["retrieved_at"])


def strip_note_digits(text: str) -> str:
    """Footnote numbers left glued to a word or a punctuation mark ('willing,1 we' -> 'willing, we')."""
    text = re.sub(r"(?<=[A-Za-z][,.;:!?'\"”’)])\d{1,2}(?=\s|$)", "", text)
    return re.sub(r"(?<=[.!?,;:\"'”’]) \d{1,2}(?=\s|$)", "", text)


def join_lines(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def roman(s: str) -> int:
    """Value of a Roman numeral (i, v, x, l, c; either case)."""
    vals = [{"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}[c] for c in s.lower()]
    return sum(-v if k + 1 < len(vals) and v < vals[k + 1] else v for k, v in enumerate(vals))
