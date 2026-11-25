"""TF-IDF representation: preprocessing, stop words, name-like words and the fitted vectoriser."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer


CONTRACTIONS = [
    (r"\bwon['’]t\b", "will not"), (r"\bcan['’]t\b", "can not"), (r"\bshan['’]t\b", "shall not"),
    (r"\bain['’]t\b", "am not"), (r"n['’]t\b", " not"), (r"\bcannot\b", "can not"),
]


def preprocess(text: str, cfg: dict) -> str:
    t = unicodedata.normalize(cfg["unicode_normalisation"], text)
    if cfg["lowercase"]:
        t = t.lower()
    if cfg["expand_negated_contractions"]:
        for pat, rep in CONTRACTIONS:
            t = re.sub(pat, rep, t)
    return t


def stopwords(cfg: dict) -> list[str]:
    keep = set(cfg["negation_words_kept"])
    # guard against YAML turning a bare `no` into False (which once silently dropped "no")
    assert all(isinstance(w, str) for w in keep), f"negation words must be strings: {keep}"
    assert "no" in keep and "not" in keep
    return sorted(w for w in ENGLISH_STOP_WORDS if w not in keep)


def name_like_words(texts: list[str], threshold: float) -> set[str]:
    """Course week 6 rule: a word capitalised in most of its uses is treated as a name."""
    seen, cap = Counter(), Counter()
    for text in texts:
        for w in re.findall(r"[^\W\d_]+", text):
            lw = w.lower()
            seen[lw] += 1
            cap[lw] += w[0].isupper()
    return {w for w in seen if cap[w] > seen[w] * threshold}


def fit(texts: list[str], cfg: dict, extra_stop: set[str] | None = None):
    sw = stopwords(cfg)
    if extra_stop:
        sw = sorted(set(sw) | extra_stop)
    vec = TfidfVectorizer(lowercase=False, preprocessor=None, token_pattern=cfg["token_pattern"],
                          stop_words=sw, min_df=cfg["min_df"], sublinear_tf=cfg["sublinear_tf"],
                          norm=cfg["norm"], smooth_idf=cfg["smooth_idf"], dtype=np.float64)
    docs = [preprocess(t, cfg) for t in texts]
    X = vec.fit_transform(docs)
    return vec, X, docs
