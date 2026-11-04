"""Stage 4a: lexical representation (one TF-IDF space fitted on the text cohort)."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from .common import INTERIM, OUTPUTS, PROCESSED, load_config, write_json

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


def run() -> dict:
    cfg = load_config()
    lcfg = cfg["lexical"]
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    ids = nar["narrative_id"].tolist()
    texts = nar["text"].tolist()
    vec, X, docs = fit(texts, lcfg)
    vocab = vec.get_feature_names_out()
    assert X.shape[0] == len(ids)
    assert not any(t in vocab for t in ("aarne", "ashliman", "folktexts")), "metadata vocabulary leaked into features"

    # name-masked sensitivity space
    names = name_like_words(texts, lcfg["name_masking_sensitivity"]["threshold"])
    vec_n, Xn, _ = fit(texts, lcfg, extra_stop=names)

    sp.save_npz(INTERIM / "lexical_tfidf.npz", X.tocsr())
    sp.save_npz(INTERIM / "lexical_tfidf_names_masked.npz", Xn.tocsr())
    pd.DataFrame({"term": vocab, "idf": vec.idf_}).to_parquet(INTERIM / "lexical_vocab.parquet", index=False)
    pd.Series(ids).to_frame("narrative_id").to_parquet(INTERIM / "lexical_order.parquet", index=False)

    tok = re.compile(lcfg["token_pattern"])
    lengths = np.array([len(tok.findall(d)) for d in docs])
    nnz = np.diff(X.tocsr().indptr)
    stats = {
        "documents": len(ids),
        "vocabulary_size": int(len(vocab)),
        "vocabulary_size_names_masked": int(len(vec_n.get_feature_names_out())),
        "name_like_words_removed": int(len(names)),
        "name_like_terms_in_vocabulary": int(len(set(vocab) & names)),
        "name_like_examples": [str(v) for v in vocab[np.argsort(vec.idf_)] if v in names][:30],
        "stop_words": len(stopwords(lcfg)),
        "negation_words_kept": lcfg["negation_words_kept"],
        "tokens_per_doc_median": float(np.median(lengths)),
        "distinct_terms_per_doc_median": float(np.median(nnz)),
        "lowest_idf_terms": [str(v) for v in vocab[np.argsort(vec.idf_)[:20]]],
        "settings": {k: v for k, v in lcfg.items() if k != "name_masking_sensitivity"},
    }
    write_json(OUTPUTS / "metrics" / "lexical_vocabulary.json", stats)
    print(f"  TF-IDF: {X.shape[0]} docs x {X.shape[1]} terms; name-masked {Xn.shape[1]} terms ({len(names)} name-like words)")
    return stats


if __name__ == "__main__":
    run()
