"""Text representations shared by Part A and Part B.

Both spaces are fitted on the folktales only. Every other text (parable, baseline passage,
calibration version) is projected into the fitted space, so adding parables never changes the map.

  tfidf      one TF-IDF space with negations kept (settings: config.yaml `lexical`)
  embedding  all-MiniLM-L6-v2, 200-token chunks, mean per text (settings: config.yaml `semantic`)

Embeddings are cached twice in data/interim/cache/: per chunk (existing cache of the website
pipeline) and per text. Both are keyed by model, revision, chunker settings and a hash of the text,
so an unchanged text is never encoded again.
"""
from __future__ import annotations

import re

import numpy as np

from analysis import semantic
from analysis.common import INTERIM, sha256_text, stable_hash
from analysis.lexical import fit as fit_tfidf
from analysis.lexical import name_like_words, preprocess
from analysis.networks import similarity_matrix

_MODEL = None


def _model(scfg: dict):
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer(scfg["model"], revision=scfg["revision"], device="cpu")
        assert _MODEL.max_seq_length == scfg["model_max_tokens"], _MODEL.max_seq_length
    return _MODEL


def embed(texts: list[str], scfg: dict) -> np.ndarray:
    """Unit-length text vectors: equal-weight mean of the text's chunk vectors, then L2 normalisation."""
    key = stable_hash({"model": scfg["model"], "revision": scfg["revision"], "max_tokens": scfg["chunk_max_tokens"],
                       "min_tail": scfg["min_tail_tokens"], "chunker": "sentence-pack-v1"})   # same key as analysis.semantic
    path = INTERIM / "cache" / f"texts_{key}.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    hashes = [sha256_text(t)[:24] for t in texts]
    store: dict[str, np.ndarray] = {}
    if path.exists():
        with np.load(path, allow_pickle=False) as z:
            store = dict(zip(z["hashes"].tolist(), z["vectors"]))
    todo = sorted({h: i for i, h in enumerate(hashes) if h not in store}.values())
    if todo:
        model = _model(scfg)
        chunker = semantic.Chunker(model.tokenizer, scfg["chunk_max_tokens"], scfg["min_tail_tokens"])
        chunks, owners = [], []
        for j, i in enumerate(todo):
            for c in chunker.chunks(texts[i]):
                chunks.append(c["text"])
                owners.append(j)
        vecs = semantic.encode_cached(model, chunks, key, scfg["batch_size"])
        pooled = semantic.pool(vecs, np.array(owners), len(todo))
        for j, i in enumerate(todo):
            store[hashes[i]] = pooled[j]
        keys = sorted(store)
        np.savez(path, hashes=np.array(keys), vectors=np.stack([store[h] for h in keys]))
    return np.stack([store[h] for h in hashes]).astype(np.float64)


class TfidfSpace:
    kind = "lexical"

    def __init__(self, folk_texts: list[str], cfg: dict):
        self.lcfg = cfg["lexical"]
        self.vec, F, _ = fit_tfidf(folk_texts, self.lcfg)      # vocabulary and IDF from the folktales only
        self.F = F.tocsr()
        self.vocab = self.vec.get_feature_names_out()

    def transform(self, texts: list[str]):
        return self.vec.transform([preprocess(t, self.lcfg) for t in texts]).tocsr()

    def sim(self, Q) -> np.ndarray:
        """Cosine of every query row to every folktale (rows are L2-normalised; an empty row gives 0)."""
        return np.asarray((Q @ self.F.T).todense())

    def folk_sim(self) -> np.ndarray:
        return similarity_matrix("lexical", np.arange(self.F.shape[0]), self.F, None)


class EmbeddingSpace:
    kind = "semantic"

    def __init__(self, folk_texts: list[str], cfg: dict):
        self.scfg = cfg["semantic"]
        self.F = embed(folk_texts, self.scfg)

    def transform(self, texts: list[str]) -> np.ndarray:
        return embed(texts, self.scfg)

    def sim(self, Q) -> np.ndarray:
        return Q @ self.F.T

    def folk_sim(self) -> np.ndarray:
        return similarity_matrix("semantic", np.arange(self.F.shape[0]), None, self.F)


def build_space(rep: str, folk_texts: list[str], cfg: dict):
    return {"tfidf": TfidfSpace, "embedding": EmbeddingSpace}[rep](folk_texts, cfg)


class Masker:
    """Sensitivity variant: collection formulae and name-like words are replaced by a placeholder.

    A word is name-like when it is capitalised in more than `threshold` of its occurrences over
    all texts of the study (course week 6, "take the names out"). One-letter words are kept.
    The placeholder is empty by default, so masked words are removed.
    """

    def __init__(self, texts: list[str], mcfg: dict):
        self.placeholder = mcfg["placeholder"]
        self.names = {w for w in name_like_words(texts, mcfg["name_threshold"]) if len(w) > 1}
        self.formulae = [re.compile(p, flags=re.IGNORECASE) for p in mcfg["formulae"] + mcfg.get("translator_formulae", [])]
        self._word = re.compile(r"[^\W\d_]+")
        ph = re.escape(self.placeholder)
        self._runs = re.compile(rf"\b{ph}(?:(?:\s+|-){ph}\b)+") if self.placeholder else None

    def masked_share(self, text: str) -> float:
        """Share of a text's words that are name-like (formulae not counted)."""
        words = self._word.findall(text)
        return sum(w.lower() in self.names for w in words) / max(len(words), 1)

    def mask(self, text: str) -> str:
        for f in self.formulae:
            text = f.sub(self.placeholder, text)
        text = self._word.sub(lambda m: self.placeholder if m.group(0).lower() in self.names else m.group(0), text)
        if self._runs:
            text = self._runs.sub(self.placeholder, text)
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)            # no space left before punctuation
        return re.sub(r"[ \t]{2,}", " ", text).strip()
