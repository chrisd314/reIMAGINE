"""Pilot B: 30 real story versions across fables, Jataka, Gospel parables and the existing corpus.

Selection (fixed before any similarity was computed):
  Aesop for Children (Gutenberg #19994): 5 purposive (Tortoise and Ducks, Ass in the Lion's Skin, Goose and Golden
    Egg, Ants and Grasshopper, Lion and Mouse) + 3 random  [random.Random(2805) over the remaining parsed fables]
  Jataka (ABT revision of Cowell et al.): 5 purposive (Ja 38, 136, 189, 215, 316) + 3 random (Ja 144, 381, 468;
    random.Random(2805).sample of the other 542 numbers)
  World English Bible: 7 Gospel narrative parables with a plot and an outcome (purposive, covering wealth, mercy,
    forgiveness, reward and interpretation)
  Existing corpus: 4 purposive (tale-0293, tale-0057, tale-0027, tale-0029) + 3 random from the 34 narratives
    that state a lesson (tale-0098, tale-0567, tale-1196)
Pre-declared pair sets (independent of the similarity scores):
  KNOWN   same plot according to editors or tale type
  TOPIC   shared topic, possibly different or opposing lessons
  RANDOM  8 cross-collection pairs, random.Random(2805)
Narrative bodies exclude stated morals, applications, frames, verses' commentary and editor keywords.
"""
import html
import itertools
import json
import os
import random
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
A = Path(sys.argv[1])
PROJECT = Path(sys.argv[2])
sys.path.insert(0, str(PROJECT))
from analysis.common import load_config  # noqa: E402
from analysis.lexical import fit, preprocess  # noqa: E402

D = A / "downloads"
OUT = A / "pilots/b_text_morals"
items = []

# ---------------- Aesop for Children
txt = (D / "gutenberg_aesop/pg19994.txt").read_text(encoding="utf-8").replace("\r", "")
body = txt.split("*** START OF THE PROJECT GUTENBERG EBOOK")[1].split("*** END OF THE PROJECT GUTENBERG EBOOK")[0]
lines = body.split("\n")
heads = [i for i, l in enumerate(lines) if re.fullmatch(r"[A-Z][A-Z ,'’\-]+", l.strip()) and len(l.strip()) > 6 and l.strip() != "THE ÆSOP FOR CHILDREN"]
fables, no_moral = {}, []
for k, i in enumerate(heads):
    j = heads[k + 1] if k + 1 < len(heads) else len(lines)
    block = re.sub(r"\[Illustration[^\]]*\]", "", "\n".join(lines[i + 1:j]))
    paras = [re.sub(r"\s+", " ", p).strip() for p in block.split("\n\n") if p.strip()]
    if not paras:
        continue
    morals = [p for p in paras if re.fullmatch(r"_.+_", p)]
    narr = [p for p in paras if p not in morals]
    if narr and morals:
        fables[lines[i].strip()] = (" ".join(narr), " ".join(m.strip("_") for m in morals))
    elif narr:
        no_moral.append(lines[i].strip())
P_AE = ["THE TORTOISE AND THE DUCKS", "THE ASS IN THE LION'S SKIN", "THE GOOSE AND THE GOLDEN EGG", "THE ANTS AND THE GRASSHOPPER", "THE LION AND THE MOUSE"]
R_AE = random.Random(2805).sample(sorted(t for t in fables if t not in P_AE), 3)
for t in P_AE + R_AE:
    n, m = fables[t]
    items.append(dict(pid=f"aesop:{t.title().replace(chr(39) + 'S', chr(39) + 's')}", collection="Aesop for Children (1919)", framing="fable (no religious frame)",
                      selection="random" if t in R_AE else "purposive", title=t.title(), source_ref="Project Gutenberg #19994 (Rand McNally 1919, adapter unnamed)",
                      narrative=n, frame="", lesson=m, lesson_kind="epimythium printed in italics by the 1919 edition", editor_keywords=""))

# ---------------- Jataka (ABT)
TT = re.compile(r'<span class="TT"><span>.*?</span><sup[^>]*></sup></span>', re.S)
jt = pd.read_csv(A / "evidence/jataka_table.csv") if (A / "evidence/jataka_table.csv").exists() else None


def clean(s):
    s = re.sub(r"<br\s*/?>", " ", s)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"\[\d+\.\d+\]|\{\d+\.\d+\}", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def divs(h, cls):
    return re.findall(rf'<div class="{cls}">(.*?)</div>', h, flags=re.S)


jseg = []
for n, sel in [(38, "purposive"), (136, "purposive"), (189, "purposive"), (215, "purposive"), (316, "purposive"), (144, "random"), (381, "random"), (468, "random")]:
    h = TT.sub("", (D / f"jataka_pages/{n:03d}.htm").read_text(encoding="utf-8").replace("\r", ""))
    title = clean(re.search(r"<title>(.*?)</title>", h, re.S).group(1))
    analysis_block = " ".join(clean(x) for x in divs(h, "analysis"))
    kw = re.search(r"Keywords:\s*([^.]*)", analysis_block)
    verses = [clean(x) for x in divs(h, "versetrans")]
    comm_words = sum(len(clean(x).split()) for x in divs(h, "gathavannana"))
    for cls in ("analysis", "verse3", "versetrans", "gathavannana"):
        h = re.sub(rf'<div class="{cls}">.*?</div>', " ", h, flags=re.S)
    main = h.split('class="Heading3"', 1)[1].split("</p>", 1)[1] if 'class="Heading3"' in h else h
    main = main.split("<footer")[0]
    blocks = [clean(b) for b in re.findall(r"<p[^>]*>(.*?)</p>", main, flags=re.S)]
    blocks = [b for b in blocks if b and not b.startswith("last updated") and b != "toggle word commentary"]
    k = next(i for i, b in enumerate(blocks) if re.match(r"(Once upon a time,? )?In the past|Once upon a time", b))
    hits = [i for i, b in enumerate(blocks) if i > k and re.search(r"identified|identification|making the connection|was I myself|I was the|I myself was", b)]
    ident_i = max(hits) if hits else len(blocks)
    items.append(dict(pid=f"ja:{n}", collection="Jataka (ABT 2023 revision of Cowell 1895-1907)", framing="Buddhist birth story", selection=sel, title=title,
                      source_ref=f"ancient-buddhist-texts.net/English-Texts/Jataka/{n:03d}.htm", narrative=" ".join(blocks[k:ident_i]),
                      frame=" ".join(blocks[:k]) + " || " + " ".join(blocks[ident_i:]), lesson=" / ".join(verses),
                      lesson_kind="verses (gatha) spoken inside the story; story-of-the-present frame and identification kept apart",
                      editor_keywords=kw.group(1).strip() if kw else ""))
    jseg.append(dict(ja=n, past_words=len(" ".join(blocks[k:ident_i]).split()), frame_words=len(" ".join(blocks[:k]).split()),
                     ident_words=len(" ".join(blocks[ident_i:]).split()), verse_words=len(" ".join(verses).split()), commentary_words=comm_words,
                     identification_found=bool(hits)))


# ---------------- World English Bible
def verses_of(chap):
    h = (D / f"web_bible/{chap}.htm").read_text(encoding="utf-8").replace("\r", "")
    h = re.sub(r'<a href="#FN\d+" class="notemark">.*?</a>', " ", h, flags=re.S)
    h = re.sub(r'<span class="popup">.*?</span>', " ", h, flags=re.S)
    parts = re.split(r'<span class="verse" id="V(\d+)">\d+&#160;</span>', h)
    return {int(parts[i]): clean(parts[i + 1].split("<ul class='tnav'>")[0].split('<div class="footnote">')[0]) for i in range(1, len(parts) - 1, 2)}


PARABLES = [("LUK12", "The Rich Fool", "Luke 12:13-21", range(13, 16), range(16, 21), range(21, 22)),
            ("LUK10", "The Good Samaritan", "Luke 10:25-37", range(25, 30), range(30, 36), range(36, 38)),
            ("MAT18", "The Unforgiving Servant", "Matthew 18:21-35", range(21, 23), range(23, 35), range(35, 36)),
            ("MAT20", "The Labourers in the Vineyard", "Matthew 20:1-16", range(0), range(1, 16), range(16, 17)),
            ("MAT25", "The Talents", "Matthew 25:14-30", range(0), range(14, 31), range(0)),
            ("LUK15", "The Prodigal Son", "Luke 15:1-3, 11-32", range(1, 4), range(11, 33), range(0)),
            ("MRK04", "The Sower", "Mark 4:1-20", range(1, 3), range(3, 10), range(13, 21))]
for chap, title, ref, fr, nv, av in PARABLES:
    v = verses_of(chap)
    items.append(dict(pid=f"web:{title.replace('The ', '')}", collection="Gospels (World English Bible, public domain)", framing="Christian parable", selection="purposive",
                      title=f"{title} ({ref})", source_ref=f"ebible.org/engwebp/{chap}.htm", narrative=" ".join(v[i] for i in nv),
                      frame=" ".join(v[i] for i in fr), lesson=" ".join(v[i] for i in av),
                      lesson_kind="speaker's application in the following verses" if len(av) else "no application stated outside the story", editor_keywords=""))

# ---------------- existing corpus
nar = pd.read_parquet(PROJECT / "data/processed/narratives.parquet").set_index("narrative_id")
MARK = re.compile(r"\b(?:The )?Morals?\s*[:.\-–—]|\bMORAL\b|\bTHE APPLICATION\b|\bApplication[:.]|\bREFLEXION\b|\bReflexion[:.]|\b(?:This|The|That) (?:fable|story|tale|parable|example) (?:shows|teaches|signifies|means|warns|proves|illustrates)|\bteach(?:es)? us\b|\bwe (?:may )?learn\b|\blearn from this\b")
FRAMING = {"tale-0293": "Indian (Telugu) folklore, Pantulu 1906", "tale-0057": "satire (Bierce 1899)", "tale-0027": "Aesop retold (Jacobs 1894)",
           "tale-0029": "Christian exemplum (Gesta Romanorum)", "tale-0098": "Christian exemplum (Gesta Romanorum)", "tale-0567": "Aesop (L'Estrange 1692)",
           "tale-1196": "Aesop (Croxall 1722)"}
seg_issues = []
for nid, sel in [("tale-0293", "purposive"), ("tale-0057", "purposive"), ("tale-0027", "purposive"), ("tale-0029", "purposive"),
                 ("tale-0098", "random"), ("tale-0567", "random"), ("tale-1196", "random")]:
    r = nar.loc[nid]
    t = r.text
    m = MARK.search(t)
    if m:
        narr, les = t[:m.start()].strip(), t[m.start():].strip()
        if len(les.split()) > 120:
            what = {"tale-0293": "a second telling of the same tale follows the moral",
                    "tale-1196": "Croxall's 'Application' is a prose essay longer than the fable"}.get(nid, "not inspected")
            seg_issues.append(f"{nid}: {len(les.split())} words after the lesson marker ({what}); first sentence kept as the lesson for comparison")
            les = re.split(r"(?<=[.!?])\s", les, maxsplit=1)[0]
        if m.start() < 0.5 * len(t):
            seg_issues.append(f"{nid}: lesson marker at {m.start() / len(t):.0%} of the text (lesson precedes or interrupts the story)")
    else:
        narr, les = t, ""
    items.append(dict(pid=f"aft:{nid}", collection="Existing corpus (Ashliman / aft.csv)", framing=FRAMING[nid], selection=sel, title=r.title,
                      source_ref=f"{nid}; ATU {r.atu_id}", narrative=narr, frame="", lesson=les,
                      lesson_kind="statement stored in the existing text after a marker" if les else "none stated", editor_keywords=""))

df = pd.DataFrame(items)
for c in ("narrative", "frame", "lesson"):
    df[f"{c}_words"] = df[c].fillna("").str.split().str.len()
assert len(df) == 30 and df.pid.is_unique
(D / "derived").mkdir(exist_ok=True)
df.to_csv(D / "derived/pilot_b_texts.csv", index=False)  # full texts stay local (mixed reuse terms)
meta_cols = ["pid", "collection", "framing", "selection", "title", "source_ref", "narrative_words", "frame_words", "lesson_words", "lesson_kind", "editor_keywords"]
df[meta_cols].to_csv(OUT / "pilot_b_items.csv", index=False)
pd.DataFrame(jseg).to_csv(OUT / "jataka_segmentation.csv", index=False)

# ---------------- representations
cfg = load_config()
lcfg = cfg["lexical"]
ref_texts = nar.text.tolist()
vec, X_all, _ = fit(ref_texts + df.narrative.tolist(), lcfg)  # IDF from the 1,498 existing narratives plus the pilot
Xn = X_all[len(ref_texts):]
vec2, X2, _ = fit(ref_texts + (df.narrative + " " + df.lesson.fillna("")).tolist(), lcfg)
Xl = X2[len(ref_texts):]
S_t = (Xn @ Xn.T).toarray()
S_tl = (Xl @ Xl.T).toarray()
vocab = vec.get_feature_names_out()

os.environ["HF_HUB_OFFLINE"] = "1"
from sentence_transformers import SentenceTransformer  # noqa: E402
from analysis.semantic import Chunker, pool  # noqa: E402

scfg = cfg["semantic"]
model = SentenceTransformer(scfg["model"], revision=scfg["revision"], device="cpu")
ch = Chunker(model.tokenizer, scfg["chunk_max_tokens"], scfg["min_tail_tokens"])
chunks, owners = [], []
for i, t in enumerate(df.narrative):
    for c in ch.chunks(t):
        chunks.append(c["text"])
        owners.append(i)
CV = model.encode(chunks, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
owners = np.array(owners)
E = pool(CV, owners, len(df))
S_e = E @ E.T
has_lesson = df.lesson.fillna("").str.len() > 0
LV = model.encode([l if l else "-" for l in df.lesson.fillna("")], normalize_embeddings=True, show_progress_bar=False)
S_le = LV @ LV.T
ids = df.pid.tolist()
for name, S in [("similarity_tfidf_narrative.csv", S_t), ("similarity_tfidf_with_lesson.csv", S_tl), ("similarity_embedding_narrative.csv", S_e), ("similarity_embedding_lesson.csv", S_le)]:
    pd.DataFrame(np.round(S, 4), index=ids, columns=ids).to_csv(OUT / name)

coll = df.collection.tolist()
pairs = [(i, j) for i, j in itertools.combinations(range(len(df)), 2)]


def shared_terms(i, j, k=6):
    a, b = Xn[i].toarray().ravel(), Xn[j].toarray().ravel()
    c = a * b
    top = np.argsort(-c)[:k]
    return ", ".join(f"{vocab[t]} {c[t]:.3f}" for t in top if c[t] > 0)


def best_passage(i, j):
    ci, cj = np.where(owners == i)[0], np.where(owners == j)[0]
    M = CV[ci] @ CV[cj].T
    a, b = np.unravel_index(np.argmax(M), M.shape)
    cut = lambda s: " ".join(s.split()[:40]) + (" ..." if len(s.split()) > 40 else "")
    return float(M[a, b]), cut(chunks[ci[a]]), cut(chunks[cj[b]])


def rank_of(S, i, j, cross_only=False):
    cand = [k for k in range(len(df)) if k != i and (not cross_only or coll[k] != coll[i])]
    order = sorted(cand, key=lambda k: -S[i, k])
    return order.index(j) + 1 if j in order else None


KNOWN = [("aesop:The Tortoise And The Ducks", "ja:215", "editor-cited parallel (Ja 215 headnote cites Benfey's Panchatantra, Babrius, Phaedrus)"),
         ("aesop:The Ass In The Lion's Skin", "ja:189", "ABT headnote: 'This is Aesop's Ass in the Lion's Skin'"),
         ("aesop:The Goose And The Golden Egg", "ja:136", "same core plot: killing/plucking the source of gold (agent's prior identification, pre-declared)"),
         ("aft:tale-0293", "ja:38", "same tale type (ATU 231, crane carries the fish)"),
         ("aesop:The Ants And The Grasshopper", "aft:tale-0057", "same tale type (ATU 280A), Bierce's satirical inversion"),
         ("aft:tale-0027", "aft:tale-0029", "same tale type (ATU 156, Androcles and the lion)")]
TOPIC = [("aesop:The Ants And The Grasshopper", "web:Rich Fool", "storing the harvest: praised vs condemned?"),
         ("aesop:The Ants And The Grasshopper", "web:Labourers in the Vineyard", "reward by work vs reward by grace?"),
         ("aesop:The Ants And The Grasshopper", "web:Prodigal Son", "the idler turned away vs welcomed back?"),
         ("aesop:The Goose And The Golden Egg", "web:Rich Fool", "greed and wealth"),
         ("ja:316", "web:Good Samaritan", "giving to a stranger in need"),
         ("web:Unforgiving Servant", "aft:tale-0027", "a benefit received and repaid or not repaid")]
idx = {p: k for k, p in enumerate(ids)}
cross = [(i, j) for i, j in pairs if coll[i] != coll[j]]
declared = {tuple(sorted((idx[a], idx[b]))) for a, b, _ in KNOWN + TOPIC}
RANDOM = random.Random(2805).sample([p for p in cross if p not in declared], 8)
rows = []
for kind, plist in [("KNOWN", [(idx[a], idx[b], why) for a, b, why in KNOWN]), ("TOPIC", [(idx[a], idx[b], why) for a, b, why in TOPIC]),
                    ("RANDOM", [(i, j, "random cross-collection pair") for i, j in RANDOM])]:
    for i, j, why in plist:
        bp = best_passage(i, j)
        rows.append(dict(set=kind, a=ids[i], b=ids[j], why=why, tfidf=round(S_t[i, j], 3), tfidf_with_lesson=round(S_tl[i, j], 3),
                         embedding=round(float(S_e[i, j]), 3), lesson_embedding=round(float(S_le[i, j]), 3) if has_lesson[i] and has_lesson[j] else None,
                         rank_tfidf_of_b_for_a=rank_of(S_t, i, j), rank_embed_of_b_for_a=rank_of(S_e, i, j),
                         rank_embed_cross_only=rank_of(S_e, i, j, True), shared_terms=shared_terms(i, j), best_passage_cos=round(bp[0], 3),
                         passage_a=bp[1], passage_b=bp[2], lesson_a=str(df.lesson[i])[:200], lesson_b=str(df.lesson[j])[:200]))
P = pd.DataFrame(rows)
P.to_csv(OUT / "pairs_examined.csv", index=False)

top = []
for i in range(len(df)):
    for S, rep in [(S_t, "tfidf"), (S_e, "embedding")]:
        allk = sorted([k for k in range(len(df)) if k != i], key=lambda k: -S[i, k])[:3]
        crossk = sorted([k for k in range(len(df)) if coll[k] != coll[i]], key=lambda k: -S[i, k])[:1]
        top.append(dict(pid=ids[i], rep=rep, top3=" ; ".join(f"{ids[k]} {S[i, k]:.3f}" for k in allk),
                        top3_same_collection=sum(coll[k] == coll[i] for k in allk), best_cross=f"{ids[crossk[0]]} {S[i, crossk[0]]:.3f}"))
T = pd.DataFrame(top)
T.to_csv(OUT / "nearest_neighbours.csv", index=False)

# ---------------- summary
s = []
s.append(f"Aesop for Children: {len(fables)} fables parsed with a separable italic moral; {len(no_moral)} without one: {no_moral[:5]}. Random picks: {R_AE}")
s.append("Jataka segmentation (words): " + "; ".join(f"Ja {r['ja']}: past {r['past_words']}, frame {r['frame_words']}, verses {r['verse_words']}, word-commentary {r['commentary_words']}, identification found {r['identification_found']}" for r in jseg))
s.append("Existing-corpus segmentation issues: " + ("; ".join(seg_issues) if seg_issues else "none"))
s.append("Narrative words by collection: " + df.groupby("collection").narrative_words.agg(["min", "median", "max"]).to_string().replace("\n", " | "))
for S, rep in [(S_t, "TF-IDF narrative"), (S_tl, "TF-IDF narrative+lesson"), (S_e, "embedding narrative")]:
    w = [S[i, j] for i, j in pairs if coll[i] == coll[j]]
    b = [S[i, j] for i, j in pairs if coll[i] != coll[j]]
    s.append(f"{rep}: mean within-collection {np.mean(w):.3f} (n={len(w)}), between-collection {np.mean(b):.3f} (n={len(b)})")
for rep in ["tfidf", "embedding"]:
    t = T[T.rep == rep]
    s.append(f"{rep}: share of top-3 neighbours from the same collection {t.top3_same_collection.sum() / (3 * len(t)):.0%}")
s.append("\nPre-declared pairs (cosines; rank of b among a's 29 neighbours; embedding rank among cross-collection candidates):")
for _, r in P.iterrows():
    s.append(f"  [{r.set}] {r.a} ~ {r.b}: tfidf {r.tfidf} (rank {r.rank_tfidf_of_b_for_a}), +lesson {r.tfidf_with_lesson}; embedding {r.embedding} (rank {r.rank_embed_of_b_for_a}, cross-rank {r.rank_embed_cross_only}); lesson-emb {r.lesson_embedding}")
known = P[P.set == "KNOWN"]
s.append(f"\nKnown parallels whose partner is the top cross-collection match (embedding): {(known.rank_embed_cross_only == 1).sum()} of {len(known)}")
rnd = P[P.set == "RANDOM"]
s.append(f"Random cross-collection pairs: TF-IDF {rnd.tfidf.min():.3f}-{rnd.tfidf.max():.3f} (mean {rnd.tfidf.mean():.3f}); embedding {rnd.embedding.min():.3f}-{rnd.embedding.max():.3f} (mean {rnd.embedding.mean():.3f})")
txt = "\n".join(s)
print(txt)
(OUT / "pilot_b_summary.txt").write_text(txt + "\n", encoding="utf-8")
