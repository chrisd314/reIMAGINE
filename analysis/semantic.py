"""Stage 4b: semantic representation with a pinned pretrained sentence encoder.

Tales are cut into non-overlapping chunks along sentence boundaries, measured
with the model's own tokenizer (special tokens included). Every chunk is
asserted to fit the model limit, so nothing is silently truncated. Chunk
vectors are cached by content hash, model identity and chunker settings.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from .common import INTERIM, OUTPUTS, PROCESSED, load_config, sha256_text, stable_hash, write_json, Timer

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


def run() -> dict:
    from sentence_transformers import SentenceTransformer

    cfg = load_config()
    scfg = cfg["semantic"]
    nar = pd.read_parquet(PROCESSED / "narratives.parquet")
    ids = nar["narrative_id"].tolist()
    with Timer("load model"):
        model = SentenceTransformer(scfg["model"], revision=scfg["revision"], device="cpu")
    assert model.max_seq_length == scfg["model_max_tokens"], model.max_seq_length
    dim = model.get_embedding_dimension() if hasattr(model, "get_embedding_dimension") else model.get_sentence_embedding_dimension()

    results, chunk_tables = {}, []
    for setting, max_tok in (("c200", scfg["chunk_max_tokens"]), ("c128", scfg["alt_chunk_max_tokens"])):
        assert max_tok <= scfg["model_max_tokens"]
        ch = Chunker(model.tokenizer, max_tok, scfg["min_tail_tokens"])
        rows = []
        with Timer(f"chunk {setting}"):
            for i, (nid, text) in enumerate(zip(ids, nar["text"])):
                for c in ch.chunks(text):
                    rows.append(dict(narrative_id=nid, owner=i, setting=setting, **c))
        tab = pd.DataFrame(rows)
        assert (tab["n_tokens"] <= scfg["model_max_tokens"]).all()
        key = stable_hash({"model": scfg["model"], "revision": scfg["revision"], "max_tokens": max_tok,
                           "min_tail": scfg["min_tail_tokens"], "chunker": "sentence-pack-v1"})
        with Timer(f"encode {setting} ({len(tab)} chunks)"):
            vecs = encode_cached(model, tab["text"].tolist(), key, scfg["batch_size"])
        assert vecs.shape == (len(tab), dim) and np.isfinite(vecs).all()
        assert np.allclose(np.linalg.norm(vecs, axis=1), 1.0, atol=1e-4), "chunk vectors are expected to be unit length"
        owners = tab["owner"].to_numpy()
        results[f"{setting}_mean"] = pool(vecs, owners, len(ids))
        if setting == "c200":
            results["c200_tokw"] = pool(vecs, owners, len(ids), weights=tab["n_tokens"].to_numpy() - 2)
            np.save(INTERIM / "semantic_chunk_vectors_c200.npy", vecs.astype(np.float32))
        tab["cache_key"] = key
        chunk_tables.append(tab.drop(columns=["text"]))

    chunks = pd.concat(chunk_tables, ignore_index=True)
    chunks.to_parquet(INTERIM / "semantic_chunks.parquet", index=False)
    np.savez(INTERIM / "semantic_vectors.npz", narrative_id=np.array(ids), **results)
    c200 = chunks[chunks.setting == "c200"]
    per = c200.groupby("narrative_id").size()
    stats = {
        "model": scfg["model"], "revision": scfg["revision"], "dimension": int(dim),
        "model_max_tokens": scfg["model_max_tokens"],
        "chunk_vectors_unit_length": True,
        "settings": {s: {"max_tokens": int(m), "chunks": int((chunks.setting == s).sum()),
                         "max_observed_tokens": int(chunks.loc[chunks.setting == s, "n_tokens"].max()),
                         "median_tokens": float(chunks.loc[chunks.setting == s, "n_tokens"].median()),
                         "tales_single_chunk": int((chunks[chunks.setting == s].groupby("narrative_id").size() == 1).sum()),
                         "merged_tails": int(chunks.loc[chunks.setting == s, "merged_tail"].sum())}
                     for s, m in (("c200", scfg["chunk_max_tokens"]), ("c128", scfg["alt_chunk_max_tokens"]))},
        "chunks_per_tale_c200": {"median": float(per.median()), "max": int(per.max())},
        "pooling": {"primary": "equal-weight mean of unit chunk vectors, then L2 normalisation",
                    "sensitivity": "mean weighted by chunk content tokens, then L2 normalisation"},
    }
    write_json(OUTPUTS / "metrics" / "semantic_representation.json", stats)
    print(f"  semantic: {len(ids)} tales; c200 chunks={stats['settings']['c200']['chunks']} (max {stats['settings']['c200']['max_observed_tokens']} tokens)")
    return stats


if __name__ == "__main__":
    run()
