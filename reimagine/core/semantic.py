"""Sentence-embedding representation with a pinned pretrained encoder.

Tales are cut into non-overlapping chunks along sentence boundaries, measured
with the model's own tokenizer (special tokens included). Every chunk is
asserted to fit the model limit, so nothing is silently truncated. Chunk
vectors are cached by content hash, model identity and chunker settings.
"""
from __future__ import annotations

import re

import numpy as np

from .common import INTERIM, sha256_text

SENT_END = re.compile(r"[.!?]+['\"’”)\]]*\s+(?=['\"‘“(\[]?[A-Z0-9])")
ABBREV = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|St|Mt|Rev|Capt|Col|Gen|Lt|Sgt|Prof|Hon|Jr|Sr|Messrs|No|vol|pp|ca|cf|viz|etc)\.$")
CLAUSE = re.compile(r"(?<=[;:,—–])\s+")


def sentence_spans(text: str) -> list[tuple[int, int]]:
    spans, start = [], 0
    for m in SENT_END.finditer(text):
        end = m.end()
        if ABBREV.search(text[start:m.start() + 1]):
            continue
        spans.append((start, end))
        start = end
    if start < len(text):
        spans.append((start, len(text)))
    return [(a, b) for a, b in spans if text[a:b].strip()]


class Chunker:
    def __init__(self, tokenizer, max_tokens: int, min_tail: int):
        self.tok = tokenizer
        self.max_content = max_tokens - 2  # [CLS] and [SEP]
        self.max_tokens = max_tokens
        self.min_tail = min_tail

    def ntok(self, s: str) -> int:
        return len(self.tok(s, add_special_tokens=False)["input_ids"])

    def _split_long(self, text: str, a: int, b: int) -> list[tuple[int, int]]:
        """Split an over-long sentence at clause punctuation, then by word windows."""
        pieces, start = [], a
        for m in CLAUSE.finditer(text, a, b):
            pieces.append((start, m.start()))
            start = m.end()
        pieces.append((start, b))
        out = []
        for pa, pb in pieces:
            if self.ntok(text[pa:pb]) <= self.max_content:
                out.append((pa, pb))
                continue
            words = [(m.start(), m.end()) for m in re.finditer(r"\S+", text[pa:pb])]
            cur = None
            for ws, we in words:
                ws, we = ws + pa, we + pa
                if cur is None:
                    cur = [ws, we]
                elif self.ntok(text[cur[0]:we]) <= self.max_content:
                    cur[1] = we
                else:
                    out.append(tuple(cur))
                    cur = [ws, we]
            if cur:
                out.append(tuple(cur))
        # merge adjacent clause pieces greedily so that clauses are not needlessly tiny
        merged = []
        for pa, pb in out:
            if merged and self.ntok(text[merged[-1][0]:pb]) <= self.max_content:
                merged[-1] = (merged[-1][0], pb)
            else:
                merged.append((pa, pb))
        return merged

    def chunks(self, text: str) -> list[dict]:
        units = []
        for a, b in sentence_spans(text):
            if self.ntok(text[a:b]) <= self.max_content:
                units.append((a, b))
            else:
                units.extend(self._split_long(text, a, b))
        out, cur = [], None
        for a, b in units:
            if cur is None:
                cur = [a, b]
            elif self.ntok(text[cur[0]:b]) <= self.max_content:
                cur[1] = b
            else:
                out.append(cur)
                cur = [a, b]
        if cur:
            out.append(cur)
        merged_tail = False
        if len(out) > 1 and self.ntok(text[out[-1][0]:out[-1][1]]) < self.min_tail:
            if self.ntok(text[out[-2][0]:out[-1][1]]) <= self.max_content:
                out[-2][1] = out[-1][1]
                out.pop()
                merged_tail = True
        res = []
        for k, (a, b) in enumerate(out):
            s = text[a:b].strip()
            lead = len(text[a:b]) - len(text[a:b].lstrip())
            n_special = len(self.tok(s, add_special_tokens=True)["input_ids"])
            assert n_special <= self.max_tokens, f"chunk exceeds limit: {n_special}"
            res.append(dict(chunk_index=k, char_start=a + lead, char_end=a + lead + len(s), text=s,
                            n_tokens=n_special, merged_tail=merged_tail and k == len(out) - 1))
        return res


def encode_cached(model, texts: list[str], key: str, batch_size: int) -> np.ndarray:
    cache_dir = INTERIM / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"chunks_{key}.npz"
    hashes = np.array([sha256_text(t)[:16] for t in texts])
    store = {}
    if path.exists():
        z = np.load(path, allow_pickle=False)
        store = dict(zip(z["hashes"], z["vectors"]))
    todo = [i for i, h in enumerate(hashes) if h not in store]
    if todo:
        vecs = model.encode([texts[i] for i in todo], batch_size=batch_size, normalize_embeddings=False,
                            show_progress_bar=False, convert_to_numpy=True)
        for i, v in zip(todo, vecs):
            store[hashes[i]] = v.astype(np.float32)
        allh = np.array(list(store.keys()))
        np.savez(path, hashes=allh, vectors=np.stack([store[h] for h in allh]))
    print(f"    encoded {len(todo)} new chunks, {len(texts) - len(todo)} from cache")
    return np.stack([store[h] for h in hashes])


def pool(chunk_vecs: np.ndarray, owners: np.ndarray, n: int, weights: np.ndarray | None = None) -> np.ndarray:
    dim = chunk_vecs.shape[1]
    out = np.zeros((n, dim), dtype=np.float64)
    w = np.ones(len(owners)) if weights is None else weights.astype(np.float64)
    np.add.at(out, owners, chunk_vecs.astype(np.float64) * w[:, None])
    out /= np.bincount(owners, weights=w, minlength=n)[:, None]
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    assert (norms > 0).all()
    return out / norms
