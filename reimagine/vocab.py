"""Stage `vocab`: shared vocabulary or shared story?

Text similarity picks up shared nouns (animals, kings, farmers) more than shared plot. Two checks:
  noun masking   every noun and proper noun (spaCy part-of-speech tags) is replaced by a placeholder that the
                 TF-IDF tokenizer ignores; verbs, adjectives, adverbs and function words stay. TF-IDF is refitted
                 on the masked folktales and every query is projected. The `headline` stage reruns the headline
                 on these neighbours (variant `tfidf_nouns_masked`) and the `checks` stage the calibration.
  match drivers  for the top-1 pair of every parable and baseline passage (unmasked TF-IDF), the 5 terms that
                 contribute most to the cosine (product of the two TF-IDF weights), whether they are nouns, and
                 the share of the whole cosine carried by nouns.
Part-of-speech tags are cached per text in data/interim/reimagine/pos_cache.json.
"""
from __future__ import annotations

import json
from collections import Counter

import numpy as np
import pandas as pd

from .core.common import sha256_text

from .common import INTERIM, TRADITIONS, Ctx, write_csv
from .corpus import load_corpus
from .part_b import leave_one_out, nearest
from .reps import TfidfSpace

NOUN_TAGS = ("NOUN", "PROPN")
SPACY_MODEL = "en_core_web_sm"


# ----------------------------------------------------------------- pure functions
def mask_nouns(tokens, placeholder: str) -> str:
    """Rebuild a text from tagged tokens (text, pos, trailing whitespace) with nouns and proper nouns replaced."""
    return "".join((placeholder if pos in NOUN_TAGS else tok) + ws for tok, pos, ws in tokens)


def noun_counts(tokens) -> dict[str, list[int]]:
    """word (lower case, letters only) -> [times tagged NOUN or PROPN, times seen]."""
    out: dict[str, list[int]] = {}
    for tok, pos, _ in tokens:
        w = tok.lower()
        if w.isalpha():
            c = out.setdefault(w, [0, 0])
            c[0] += pos in NOUN_TAGS
            c[1] += 1
    return out


def noun_lexicon(counts: list[dict], min_share: float = 0.5) -> set[str]:
    """Words tagged as a noun in at least `min_share` of their occurrences over all texts."""
    tot: dict[str, list[int]] = {}
    for c in counts:
        for w, (n, m) in c.items():
            t = tot.setdefault(w, [0, 0])
            t[0] += n
            t[1] += m
    return {w for w, (n, m) in tot.items() if m and n / m >= min_share}


def drivers(q_row, f_row, vocab: np.ndarray, k: int = 5) -> list[tuple[str, float]]:
    """The k terms contributing most to the cosine of two L2-normalised TF-IDF rows (sparse 1 x V)."""
    prod = q_row.multiply(f_row).tocsr()
    if not prod.nnz:
        return []
    order = np.argsort(-prod.data, kind="stable")[:k]
    return [(str(vocab[prod.indices[i]]), float(prod.data[i])) for i in order]


def noun_share_of_cosine(q_row, f_row, is_noun_term: np.ndarray) -> float:
    """Share of the cosine of two TF-IDF rows that comes from noun terms."""
    prod = q_row.multiply(f_row).tocsr()
    total = prod.data.sum()
    return float(prod.data[is_noun_term[prod.indices]].sum() / total) if total > 0 else np.nan


# ----------------------------------------------------------------- tagging (spaCy; cached)
def tag_all(ctx: Ctx, texts: list[str]) -> list[list[tuple[str, str, str]]]:
    path = INTERIM / "reimagine" / "pos_cache.json"          # shared by full and development runs (git-ignored)
    path.parent.mkdir(parents=True, exist_ok=True)
    import spacy
    key_model = f"{SPACY_MODEL}-{spacy.util.get_package_version(SPACY_MODEL)}-pos-v1"
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if cache.get("_model") != key_model:
        cache = {"_model": key_model}
    keys = [sha256_text(t)[:24] for t in texts]
    todo = sorted({k: i for i, k in enumerate(keys) if k not in cache}.values())
    if todo:
        nlp = spacy.load(SPACY_MODEL, disable=["parser", "ner", "lemmatizer"])
        nlp.max_length = max(nlp.max_length, max(len(texts[i]) for i in todo) + 1)
        print(f"    tagging {len(todo)} texts with spaCy {key_model}", flush=True)
        for i, doc in zip(todo, nlp.pipe((texts[i] for i in todo), batch_size=16)):
            cache[keys[i]] = [[t.text, t.pos_, t.whitespace_] for t in doc]
        path.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return [[tuple(x) for x in cache[k]] for k in keys]


# ----------------------------------------------------------------- the stage
def run(ctx: Ctx) -> dict:
    vc = ctx.paper["vocab"]
    corpus = load_corpus(ctx)
    folk, queries = corpus.folk, corpus.queries(ctx)
    tags_f = tag_all(ctx, folk["text"].tolist())
    tags_q = tag_all(ctx, queries["text"].tolist())
    nouns = noun_lexicon([noun_counts(t) for t in tags_f + tags_q], vc["noun_share"])
    def masked_share(tags) -> float:
        words = [pos in NOUN_TAGS for tok, pos, _ws in tags if any(c.isalpha() for c in tok)]
        return float(np.mean(words)) if words else 0.0

    # ---- noun-masked TF-IDF: neighbours for the headline and the calibration
    mf = [mask_nouns(t, vc["placeholder"]) for t in tags_f]
    mq = [mask_nouns(t, vc["placeholder"]) for t in tags_q]
    space = TfidfSpace(mf, ctx.cfg)
    S = space.sim(space.transform(mq))
    k = ctx.paper["partB"]
    idx, val = nearest(S, k["attach_k"])
    cal = (queries["kind"] == "calibration").to_numpy()
    loo_masked = leave_one_out(space.folk_sim(), k["closeness_k"])
    np.savez_compressed(ctx.work / "tfidf_nouns_masked.npz", query_ids=queries["id"].to_numpy(dtype=str), idx=idx, val=val,
                        closeness=val[:, :k["closeness_k"]].mean(axis=1), S_calibration=S[cal], loo=loo_masked)
    print(f"    noun-masked TF-IDF: {len(space.vocab):,} terms (unmasked map: see partA); {len(nouns):,} words are nouns "
          f"in at least {vc['noun_share']:.0%} of their uses")

    # ---- what drives each top-1 match (unmasked TF-IDF, the primary space)
    plain = TfidfSpace(folk["text"].tolist(), ctx.cfg)
    is_noun_term = np.array([w in nouns for w in plain.vocab])
    Q = plain.transform(queries["text"].tolist())
    zb = np.load(ctx.work / "partB_tfidf.npz", allow_pickle=False)
    assert zb["query_ids"].tolist() == queries["id"].tolist(), "rerun partB"
    top1 = zb["idx"][:, 0]
    z_masked = val[:, :k["closeness_k"]].mean(axis=1)
    rows = []
    for q in np.flatnonzero(queries["kind"].isin(["parable", "baseline"]).to_numpy()):
        f = int(top1[q])
        dr = drivers(Q[q], plain.F[f], plain.vocab, vc["driver_terms"])
        cos = float(Q[q].multiply(plain.F[f]).sum())
        rows.append(dict(id=queries.at[q, "id"], kind=queries.at[q, "kind"], tradition=queries.at[q, "tradition"],
                         title=queries.at[q, "title"], folktale_id=folk.at[f, "id"], folktale_title=folk.at[f, "title"],
                         folktale_atu=folk.at[f, "atu_id"], cosine=cos, driver_terms="; ".join(w for w, _ in dr),
                         driver_contributions="; ".join(f"{c:.4f}" for _, c in dr),
                         drivers_share_of_cosine=sum(c for _, c in dr) / cos if cos > 0 else np.nan,
                         driver_nouns="; ".join(w for w, _ in dr if w in nouns),
                         driver_noun_share=float(np.mean([w in nouns for w, _ in dr])) if dr else np.nan,
                         noun_share_of_cosine=noun_share_of_cosine(Q[q], plain.F[f], is_noun_term),
                         noun_share_of_text=masked_share(tags_q[q]),
                         folk_closeness=float(zb["closeness"][q]), folk_closeness_nouns_masked=float(z_masked[q])))
    md = pd.DataFrame(rows)
    write_csv(md, ctx.results / "match_drivers.csv")
    summ = []
    for trad in TRADITIONS:
        for kind in ("parable", "baseline"):
            m = md[(md["tradition"] == trad) & (md["kind"] == kind)]
            if not len(m):
                continue
            terms = Counter(w for s in m["driver_terms"] for w in s.split("; ") if w)
            summ.append(dict(tradition=trad, kind=kind, n=len(m),
                             top_driver_terms="; ".join(f"{w} ({c})" for w, c in terms.most_common(vc["summary_terms"])),
                             driver_noun_share=float(m["driver_noun_share"].mean()),
                             noun_share_of_cosine_median=float(m["noun_share_of_cosine"].median()),
                             noun_share_of_text_median=float(m["noun_share_of_text"].median()),
                             folk_closeness_median=float(m["folk_closeness"].median()),
                             folk_closeness_nouns_masked_median=float(m["folk_closeness_nouns_masked"].median()),
                             # raw closeness is not comparable across the two spaces (masking leaves a smaller, more
                             # common vocabulary, so every cosine rises); the folktales' own spread in each space is
                             percentile_among_folktales=float(100 * (zb["loo"] < m["folk_closeness"].median()).mean()),
                             percentile_among_folktales_nouns_masked=float(100 * (loo_masked < m["folk_closeness_nouns_masked"].median()).mean())))
    write_csv(pd.DataFrame(summ), ctx.results / "match_drivers_by_tradition.csv")
    pd.Series(sorted(nouns)).to_frame("noun").pipe(write_csv, ctx.work / "noun_lexicon.csv")
    return dict(nouns=len(nouns))
