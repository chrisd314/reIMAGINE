"""Pilot C: text checks for two historical case studies (descriptive; similarity is not evidence of transmission).

C1  Mesopotamian flood narrative -> Genesis 6-9   (ETCSL t.1.7.4 translation vs World English Bible)
C2  Barlaam and Ioasaph apologue -> later Western versions of ATU 1678 in the existing corpus
Controls hold translation or collection constant while the story changes, to show how much of a cosine is style.
"""
import html
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
A, PROJECT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(PROJECT))
from analysis.common import load_config  # noqa: E402
from analysis.lexical import fit  # noqa: E402

D = A / "downloads"


def strip(h):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def web(chap, a, b):
    h = (D / f"web_bible/{chap}.htm").read_text(encoding="utf-8")
    h = re.sub(r'<a href="#FN\d+" class="notemark">.*?</a>', " ", h, flags=re.S)
    parts = re.split(r'<span class="verse" id="V(\d+)">\d+&#160;</span>', h)
    v = {int(parts[i]): strip(parts[i + 1].split("<ul class='tnav'>")[0].split('<div class="footnote">')[0]) for i in range(1, len(parts) - 1, 2)}
    return " ".join(v[i] for i in range(a, b + 1) if i in v)


etcsl = strip((D / "etcsl/t174_flood_story.html").read_text(encoding="utf-8"))
etcsl = etcsl[etcsl.find("Segment A"):]
etcsl = re.sub(r"approx\. \d+ lines missing|\d+ lines? fragmentary|Segment [A-Z]|\d+-\d+\.|……", " ", etcsl)
etcsl = re.sub(r"\s+", " ", etcsl).strip()
genesis = " ".join([web("GEN06", 5, 22), web("GEN07", 1, 24), web("GEN08", 1, 22), web("GEN09", 1, 17)])
rich_fool = web("LUK12", 16, 20)
bar = re.sub(r"\s+", " ", (D / "gutenberg_barlaam/pg749.txt").read_text(encoding="utf-8"))
k = bar.find("his son that had never seen a single object")
s0 = bar.rfind(". ", 0, k - 1200)
apologue = bar[s0 + 2: bar.find(". ", k + 900) + 1]
nar = pd.read_parquet(PROJECT / "data/processed/narratives.parquet").set_index("narrative_id")
texts = {
    "ETCSL Flood story (t.1.7.4, fragmentary)": etcsl,
    "Genesis 6:5-9:17 (WEB)": genesis,
    "CONTROL Luke 12:16-20 Rich Fool (WEB)": rich_fool,
    "Barlaam and Ioasaph: apologue of the king's son (Gutenberg #749)": apologue,
    "tale-0137 Boccaccio, Filippo Balducci (1350-55; retold by Ashliman)": nar.loc["tale-0137", "text"],
    "tale-0135 Geiler von Kaysersberg (c. 1510)": nar.loc["tale-0135", "text"],
    "tale-0136 Poggio, Facetiae (15th c.)": nar.loc["tale-0136", "text"],
    "CONTROL tale-0029 Gesta Romanorum, Of the Remembrance of Benefits": nar.loc["tale-0029", "text"],
}
names = list(texts)
cfg = load_config()
ref = nar.text.tolist()
vec, X, _ = fit(ref + list(texts.values()), cfg["lexical"])
Xt = X[len(ref):]
St = (Xt @ Xt.T).toarray()
os.environ["HF_HUB_OFFLINE"] = "1"
from sentence_transformers import SentenceTransformer  # noqa: E402
from analysis.semantic import Chunker, pool  # noqa: E402

sc = cfg["semantic"]
model = SentenceTransformer(sc["model"], revision=sc["revision"], device="cpu")
ch = Chunker(model.tokenizer, sc["chunk_max_tokens"], sc["min_tail_tokens"])
chunks, own = [], []
for i, t in enumerate(texts.values()):
    for c in ch.chunks(t):
        chunks.append(c["text"]); own.append(i)
E = pool(model.encode(chunks, normalize_embeddings=True, show_progress_bar=False), np.array(own), len(names))
Se = E @ E.T
PAIRS = [(0, 1, "C1 case: Sumerian flood vs Genesis flood (different translators)"),
         (1, 2, "C1 control: Genesis flood vs unrelated parable (same translation)"),
         (0, 2, "C1 control: Sumerian flood vs unrelated parable"),
         (3, 4, "C2 case: Barlaam apologue vs Boccaccio"), (3, 5, "C2 case: Barlaam apologue vs Geiler"),
         (3, 6, "C2 case: Barlaam apologue vs Poggio (combines ATU 1678 with 1686)"),
         (4, 5, "C2: Boccaccio vs Geiler (two later versions)"),
         (3, 7, "C2 control: Barlaam apologue vs unrelated Christian exemplum (same era of moralised tales)")]
rows = [dict(pair=w, a=names[i], b=names[j], words_a=len(texts[names[i]].split()), words_b=len(texts[names[j]].split()),
             tfidf=round(float(St[i, j]), 3), embedding=round(float(Se[i, j]), 3)) for i, j, w in PAIRS]
out = pd.DataFrame(rows)
out.to_csv(A / "pilots/c_history/pilot_c_similarity.csv", index=False)
print(out[["pair", "words_a", "words_b", "tfidf", "embedding"]].to_string(index=False))
print("\nApologue excerpt used (Gutenberg #749):", apologue[:700], "...")
