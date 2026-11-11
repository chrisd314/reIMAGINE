"""The Aesop for Children (1919, Project Gutenberg #19994): fables with their printed morals.

Used only for the hidden-moral check of the lesson coder: the narrative is shown without the
moral, and the coder's inferred lesson is then compared with the moral the book prints.
"""
from __future__ import annotations

import random
import re

from .common import RAW

SOURCE = RAW / "aesop" / "pg19994.txt"
TITLE = re.compile(r"^[A-Z][A-Z ,'\-]{4,}$")


def load_fables() -> list[dict]:
    """Every fable that has a narrative and exactly one printed (italic) moral."""
    text = SOURCE.read_text(encoding="utf-8").replace("\r\n", "\n")
    start, end = text.index("*** START OF"), text.index("*** END OF")
    lines = text[start:end].split("\n")[1:]
    # titles occur once in the list of fables and once above each fable: keep the later occurrence
    heads = [i for i, ln in enumerate(lines) if TITLE.match(ln.strip()) and not ln.startswith(" ")]
    last = {}
    for i in heads:
        last[lines[i].strip()] = i
    order = sorted(last.items(), key=lambda kv: kv[1])
    fables = []
    for k, (title, i) in enumerate(order):
        stop = order[k + 1][1] if k + 1 < len(order) else len(lines)
        paras = [re.sub(r"\s+", " ", p).strip() for p in "\n".join(lines[i + 1:stop]).split("\n\n")]
        paras = [p for p in paras if p and not p.startswith("[Illustration")]
        morals = [p.strip("_").strip() for p in paras if p.startswith("_") and p.endswith("_")]
        body = " ".join(p for p in paras if not (p.startswith("_") and p.endswith("_")))
        if len(morals) == 1 and len(body.split()) >= 50:
            fables.append(dict(title=title.title(), body=body, moral=morals[0], n_words=len(body.split())))
    return fables


def check_sample(n: int, seed: int) -> list[dict]:
    """The seeded sample of fables used for the hidden-moral check, in presentation order."""
    fables = sorted(load_fables(), key=lambda f: f["title"])
    picked = random.Random(seed).sample(fables, n)
    for k, f in enumerate(picked, 1):
        f["handle"] = f"a{k:02d}"
    return picked
