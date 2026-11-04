"""Profile the project's existing corpus (read-only) for the proposed folklore/religion/morals components."""
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
P = Path(sys.argv[1])  # project root
d = pd.read_parquet(P / "data/processed/narratives.parquet")
rec = pd.read_parquet(P / "data/interim/records.parquet")


def joined(v):
    if isinstance(v, str):
        return v
    try:
        return " | ".join(str(x) for x in v if isinstance(x, str))
    except TypeError:
        return ""


d["prov"] = d.provenance_raw.map(joined)
d["src"] = d.source.map(joined)
d["meta"] = d.prov + " || " + d.src + " || " + d.title.fillna("")
out = []
out.append(f"Unit: one narrative = one tale text from an Ashliman page (story version); {len(rec)} raw records -> {len(d)} narratives "
           f"({int((d.n_records > 1).sum())} merged exact duplicates). Words: median {d.n_words.median():.0f}, IQR {d.n_words.quantile(.25):.0f}-{d.n_words.quantile(.75):.0f}; "
           f"<100 words {(d.n_words < 100).sum()}, <200 {(d.n_words < 200).sum()}; suspected fragments {int(d.suspected_fragment.sum())}; near-duplicate non-representatives {int((~d.near_dup_representative).sum())}.")

# ---- time information: years inside the source citation (publication/edition dates, not narrative dates)
def years(s):
    return [int(y) for y in re.findall(r"(?<!\d)(1[4-9]\d\d|20[0-2]\d)(?!\d)", s or "")]


d["src_years"] = d.src.map(years)
has = d.src_years.map(len) > 0
first = d.loc[has, "src_years"].map(min)
out.append(f"\nSource citation present: {(d.src.str.len() > 0).sum()}; with at least one 4-digit year: {has.sum()} "
           f"({has.mean():.0%}). Earliest year cited per narrative: median {first.median():.0f}; by century: "
           + str(first.floordiv(100).mul(100).value_counts().sort_index().to_dict()))
out.append("These are edition/translation/publication years of the source used by the editor; they do not date the narrative. "
           f"Raw 'date_obtained' values: {sorted(rec.date_obtained.dropna().astype(str).str[:4].unique().tolist())} (scrape dates).")

# ---- collections with a religious or didactic framing (metadata match)
COLL = [
    ("Aesop (all translators)", r"Aesop|Æsop|Babrius|Phaedrus|Avian|Anianus|Caxton|Estrange|Croxall|Bewick|Townsend|Vernon Jones", "fable (non-religious)"),
    ("La Fontaine / Bierce / Tolstoy / Krylov / Lessing / Marie de France", r"Fontaine|Bierce|Tolstoy|Krylov|Lessing|Marie de France", "fable (non-religious)"),
    ("Panchatantra / Bidpai / Kalilah / Hitopadesa / Anvar", r"Panchatantra|Pañcatantra|Bidpai|Pilpay|Kalilah|Hitopadesa|Anv[aá]r", "nīti / didactic"),
    ("Jataka", r"J[aā]taka", "Buddhist"),
    ("Gesta Romanorum", r"Gesta Romanorum", "Christian exemplum"),
    ("Sermon exempla (Jacques de Vitry, Odo, Etienne de Bourbon, Bromyard)", r"Vitry|Odo of Cheriton|Bourbon|Bromyard|exempl", "Christian exemplum"),
    ("Bible / Talmud / Midrash / Qur'an", r"\bBible\b|Testament|Genesis|Talmud|Midrash|Koran|Qur.an|Gospel", "scripture/commentary"),
    ("Sufi / Persian didactic (Rumi, Sa'di, Attar)", r"Rumi|Masnavi|Mathnawi|Sa.di|Gulistan|Bustan|Attar|Sufi", "Islamic (Sufi) didactic"),
]
out.append("\nCollections with a religious or didactic framing (provenance/source/title match; overlaps possible):")
for name, pat, kind in COLL:
    m = d.meta.str.contains(pat, regex=True)
    d[name] = m
    out.append(f"  {m.sum():4d}  {name} [{kind}]; ATU types {d.loc[m, 'atu_id'].nunique()}; median words {d.loc[m, 'n_words'].median() if m.any() else 0:.0f}")
relig = d[[c for c, _, k in COLL if k in ("Buddhist", "Christian exemplum", "scripture/commentary", "Islamic (Sufi) didactic")]].any(axis=1)
out.append(f"  religious-collection versions (Jataka, Gesta, exempla, scripture, Sufi): {relig.sum()}; ATU chapter 'Religious Tales' (750-849): {(d.atu_chapter == 'Religious Tales').sum()}")
types_rel = set(d.loc[relig, "atu_id"].dropna())
both = d[d.atu_id.isin(types_rel)].groupby("atu_id").apply(lambda g: pd.Series(dict(rel=int(relig[g.index].sum()), other=int((~relig[g.index]).sum()))))
both = both[(both.rel > 0) & (both.other > 0)]
out.append(f"  ATU types with at least one religious-collection version and one other version: {len(both)} types "
           f"({int(both.rel.sum())} religious-collection + {int(both.other.sum())} other versions)")
out.append("  NOTE: this is the raw metadata screen. On inspection 2 of the 3 'scripture' hits are folk texts that mention a Bible "
           "(tale-1375, tale-1388); the corrected frame (29 types, 36 + 257 versions) is in evidence/annotation_frame_types.csv.")

# ---- explicit lesson statements inside the stored text
PAT = {
    "labelled 'Moral'": r"\b(?:The )?Morals?\s*[:.\-–—]|\bMORAL\b",
    "'Application'/'Reflexion'": r"\bTHE APPLICATION\b|\bApplication[:.]|\bREFLEXION\b|\bReflexion[:.]",
    "'this story/fable shows/teaches'": r"\b(?:This|The|That) (?:fable|story|tale|parable|example) (?:shows|teaches|signifies|means|warns|proves|illustrates)",
    "'teaches us'/'we learn'/'learn from this'": r"\bteach(?:es)? us\b|\bwe (?:may )?learn\b|\blearn from this\b",
}
any_m = pd.Series(False, index=d.index)
out.append("\nExplicit lesson statements stored inside the narrative text (part of what the current TF-IDF and embeddings read):")
for k, p in PAT.items():
    m = d.text.str.contains(p, regex=True)
    any_m |= m
    out.append(f"  {m.sum():4d}  {k}")
out.append(f"  {any_m.sum():4d}  any of the above ({any_m.mean():.1%} of narratives); in religious-collection versions: {(any_m & relig).sum()}")
d["has_lesson"] = any_m
for t in ["280A", "275", "156"]:
    g = d[d.atu_id == t]
    out.append(f"\n  ATU {t}: {len(g)} versions, {int(g.has_lesson.sum())} with a stated lesson. Stated lessons (first 150 chars):")
    for _, r in g[g.has_lesson].iterrows():
        m = re.search("|".join(PAT.values()), r.text)
        out.append(f"     {r.narrative_id} {r.title[:42]!r}: {r.text[m.start(): m.start() + 150]!r}")

# ---- editorial notes that make historical claims
TR = r"derived from|borrowed|influence|origin(?:ated|al source)?\b|spread|travel(?:l)?ed|migrat|transmi|came to Europe|found (?:its|their) way|via (?:Persian|Arabic)|translation of"
nm = d.notes.map(joined)
hit = nm.str.contains(TR, case=False, regex=True)
out.append(f"\nEditor notes stored with the tales: non-empty {int((nm.str.len() > 0).sum())}; containing a transmission/origin claim word: {int(hit.sum())}. Examples:")
for _, r in d[hit].sample(5, random_state=1).iterrows():
    m = re.search(TR, nm[_], flags=re.I)
    out.append(f"     {r.narrative_id}: ...{nm[_][max(0, m.start() - 110): m.end() + 140]!r}")
flags = rec["flags"].map(lambda f: list(f) if f is not None and not isinstance(f, str) else ([f] if isinstance(f, str) else []))
out.append("\nCleaning flags on raw records: " + str(pd.Series([x for f in flags for x in f]).value_counts().head(12).to_dict()))
txt = "\n".join(out)
print(txt)
Path(sys.argv[2]).write_text(txt + "\n", encoding="utf-8")
