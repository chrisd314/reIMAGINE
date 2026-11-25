"""Text blocks from a sacred-texts.com reader page (the 2026 site layout).

The book text is served inside <article data-slot="reader-content">. Footnotes sit in a
<section data-slot="reader-footnotes"> at its end. Footnote marks are pairs of anchors
(<a id="fr_13"></a><a href="...#fn_13">2</a>, or <a></a><a href="#fn-..." data-footnote-ref="164:2">2</a>).
Printed page numbers are paragraphs of their own (<p><a>p. 165</a></p>) that can cut a paragraph in
two. Advertising placeholders are empty divs. Only the standard library is used.
"""
from __future__ import annotations

import html
import re
from typing import NamedTuple

ARTICLE = re.compile(r'<article[^>]*data-slot="reader-content"[^>]*>(.*?)</article>', re.S)
FOOTNOTES = re.compile(r'<section[^>]*data-slot="reader-footnotes".*', re.S)
AD = re.compile(r'<div[^>]*data-ad-vro[^>]*>\s*<div[^>]*>\s*</div>\s*</div>', re.S)
FN_MARK = re.compile(r'(?:<a[^>]*>\s*</a>\s*)?<a[^>]*(?:href="[^"]*#fn[_-][^"]*"|data-footnote-ref="[^"]*")[^>]*>.*?</a>', re.S)
COMMENT = re.compile(r"<!--.*?-->", re.S)
BLOCK = re.compile(r"<(p|div|h[1-6]|blockquote|li|pre|td)\b[^>]*>(.*?)(?=<(?:p|div|h[1-6]|blockquote|li|pre|td|/div|/blockquote|/td|hr)\b|$)", re.S)
TAG = re.compile(r"<[^>]+>")
PAGE_NUMBER = re.compile(r"p\. [\divxlc]+")
SENTENCE_END = re.compile(r"""[.!?:;]['"’”)\]]*$""")


class Block(NamedTuple):
    tag: str        # p, div (verse), h1..h6, blockquote, li, pre, td
    text: str
    italic: bool    # the whole block is set in italics


def clean(fragment: str, lines: bool = False) -> str:
    s = re.sub(r"\s+", " ", fragment)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = html.unescape(TAG.sub("", s)).replace("\xa0", " ")
    s = re.sub(r"\[\s*p\.\s*[\divxlc]+\s*\]", " ", s)          # printed page numbers set inline
    if lines:
        return "\n".join(x for x in (re.sub(r"[ \t]+", " ", ln).strip() for ln in s.split("\n")) if x)
    return re.sub(r"\s+", " ", s).strip()


def article(page: str) -> str:
    m = ARTICLE.search(page)
    if not m:
        raise ValueError("no reader-content article in page")
    body = FOOTNOTES.sub("", m.group(1))
    for pat in (COMMENT, AD, FN_MARK):
        body = pat.sub(" ", body)
    return body


def blocks(page: str, lines: bool = False) -> list[Block]:
    """Non-empty text blocks of the book text, in reading order, without footnotes and note marks.

    A paragraph cut in two by a printed page number is joined again. With `lines`, the line
    breaks inside a block are kept as newlines (verse, or books set with <br> instead of <p>).
    """
    out, after_page = [], False
    for tag, inner in BLOCK.findall(article(page)):
        text = clean(inner, lines)
        if not text:
            continue
        if PAGE_NUMBER.fullmatch(text):
            after_page = True
            continue
        rest = re.sub(r"<(i|em)\b[^>]*>.*?</\1>", "", inner, flags=re.S)
        block = Block(tag.lower(), text, italic=not html.unescape(TAG.sub("", rest)).strip(" \n\t.,;:!?'\"()[]-—"))
        prev = out[-1] if out else None
        if after_page and prev and prev.tag == "p" and block.tag == "p" and (
                text[0].islower() or not SENTENCE_END.search(prev.text)):
            out[-1] = Block("p", prev.text + (" " if not lines else "\n") + text, prev.italic and block.italic)
        else:
            out.append(block)
        after_page = False
    return out


def chapter_slugs(page: str, book: str) -> list[str]:
    """Chapter slugs of `book`, in order, from the navigation that every reader page carries."""
    out = []
    for c in re.findall(r'href="/book/%s/([^"#?]+)' % re.escape(book), page):
        if c not in out and not c.startswith("read/"):
            out.append(c)
    return out


def title(page: str) -> str:
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    return clean(m.group(1)) if m else ""
