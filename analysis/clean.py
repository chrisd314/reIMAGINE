"""Stage 2: clean the pinned aft.csv into traceable records.

Every raw row keeps its original strings. Cleaning only removes identifiable
non-narrative material (navigation, source citations, classification notes,
footnote markers, editorial notes) by documented rules, logs every removed
span, and applies the agent-reviewed decisions in data/mappings/text_review.csv.
Stories are never paraphrased or summarised.
"""
from __future__ import annotations

import re
import unicodedata

import ftfy
import pandas as pd

from .common import INTERIM, MAPPINGS, OUTPUTS, RAW, load_config, sha256_text

MISSING = "NA"  # the R export writes missing values as the literal string NA

# Abbreviations whose full stop does not end a sentence (bibliographic and honorific)
ABBREV = {"vol", "vols", "no", "nos", "pp", "p", "ed", "eds", "trans", "tr", "mr", "mrs", "ms", "dr", "st", "co",
          "rev", "esq", "ltd", "jr", "sr", "nr", "s", "cf", "repr", "orig", "comp", "illus", "c", "ca", "viz",
          "vs", "etc", "v", "bd", "hrsg", "ff", "fig", "chap", "ch", "sec", "pt", "bk", "n", "nf", "aufl"}

# Markers that something after them is not narrative. Mode "segment" markers
# open a new segment, so the cut starts at the marker itself; mode "sentence"
# markers sit inside a bibliographic or editorial sentence whose start is found
# by walking back to the previous sentence boundary.
STRONG_MARKERS = [
    ("source_line", "segment", r"\bSources?(?: \([^)]{0,40}\))?:"),
    ("citation", "sentence", r"\((?:[A-Z][\w.'\-]*(?: [\w.'\-]+){0,4}(?:, [\w.'\- ]+)?): [^()]{2,140}?\[?\d{4}\]?\)"),
    ("page_reference", "sentence", r"\bpp\. \d+|\bp\. \d+(?:[-–]\d+)?\.|\bvol\. \d+[,)]"),
    ("navigation", "segment", r"Return to:? (?:D\. ?L\. Ashliman|the table of contents|Folklore and Mythology)|\bReturn to:?\s*$|\bLinks? to\b|Related links|\bSee also\b|An essay by D\. ?L\. Ashliman"),
    ("translator_credit", "sentence", r"\b[Tt]ranslated (?:by|from)\b"),
    ("revised_stamp", "segment", r"\bRevised (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}"),
    ("classification", "sentence", r"Aarne[-–‑ ]Thompson|\bATU\b|\bPerry Index\b|\b[Tt]ales? of types? \d|\bclassified as type\b|\btypes? \d{1,4}[A-Z]?\*?(?:[,.;:) ]|$)|\b[Ff]olktale types?\b|\b[Tt]ale[- ]types?\b"),
    ("copyright", "segment", r"©|&copy|\bcopyright\b|\bCopyright\b"),
    ("translator_note", "segment", r"Translated by D\. ?L\. Ashliman|Translation revised by|Retold by D\. ?L\. Ashliman|\bNote by D\. ?L\. Ashliman"),
    ("editorial_notes", "segment", r"\bNotes?:\s|\bBibliography\b|Other sources for this (?:fable|tale)|\bPerry titles\b|\*?Footnote:|Notes and bibliography|Translator's footnote"),
]
NEW_TALE_START = re.compile(r"\b(Once upon a time|There was once|There once (?:was|lived)|Once there (?:was|lived)|Long, long ago|In olden times)\b")
FOOTNOTE_INLINE = [
    ("footnote_block", re.compile(r"\[\s*Footnote:[^\]]{0,800}\]", re.I)),
    ("footnote_marker", re.compile(r"\[\s*footnote\s*\d*\s*\]|\{\s*footnote\s*\d*\s*\}", re.I)),
]
CONNECTIVE_START = re.compile(
    r"^(And|But|So|Then|However|Thereupon|At last|Finally|Meanwhile|Upon this|After this|After that|"
    r"On (?:his|her|their) return|Whereupon|Hereupon|Afterwards|This,|Now when)\b")
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def fix_display(s: str) -> str:
    """Repair mojibake (latin-1/cp1252 double encoding) and normalise to NFC."""
    if s is None:
        return s
    return unicodedata.normalize("NFC", ftfy.fix_encoding(s))


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def sentence_start_before(text: str, pos: int) -> int:
    """Index where the sentence containing `pos` begins (abbreviation-aware)."""
    for m in reversed(list(re.finditer(r"[.!?]['\"’”)\]]*\s+", text[:pos]))):
        dot = m.start()
        if text[dot] == ".":
            tok = re.search(r"([A-Za-zÀ-ÿ]+)$", text[:dot])
            word = tok.group(1) if tok else ""
            if word.lower() in ABBREV or (len(word) == 1 and word.isupper()):
                continue
        return m.end()
    return 0


def first_marker(text: str, min_rel: float):
    """Earliest strong post-narrative marker at or after min_rel of the text."""
    best = None
    for name, mode, pat in STRONG_MARKERS:
        for m in re.finditer(pat, text):
            if m.start() / max(len(text), 1) < min_rel:
                continue
            if best is None or m.start() < best[1]:
                best = (name, m.start(), m.group(0), mode)
            break
    return best


def early_markers(text: str, max_rel: float):
    hits = []
    for name, _mode, pat in STRONG_MARKERS:
        for m in re.finditer(pat, text):
            if m.start() / max(len(text), 1) < max_rel:
                hits.append((name, m.start(), m.group(0)))
    return hits


def collapse_repetition(text: str):
    """If the text is an exact repeat (A A), keep one copy."""
    head = text[:80]
    k = text.find(head, 80)
    while k != -1:
        a, b = text[:k].strip(), text[k:].strip()
        if a == b:
            return a, True
        k = text.find(head, k + 1)
    return text, False


def load_review() -> pd.DataFrame:
    path = MAPPINGS / "text_review.csv"
    if not path.exists():
        return pd.DataFrame(columns=["record_id", "action", "pattern", "reason", "reviewer", "reviewed_on"])
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def clean_text(record_id: str, raw: str, review: dict, cfg: dict, log: list) -> tuple[str, list]:
    flags = []
    t = squash(fix_display(raw))
    rv = review.get(record_id, [])

    def logit(rule, removed, where):
        if removed.strip():
            log.append(dict(record_id=record_id, rule=rule, position=where, removed=removed.strip()))

    # 1. manual leading trims (editorial introductions confirmed by review)
    for r in rv:
        if r["action"] == "trim_before":
            k = t.find(r["pattern"])
            if k < 0:
                raise ValueError(f"{record_id}: trim_before pattern not found: {r['pattern']!r}")
            logit("manual_trim_before", t[:k], "start")
            t = t[k:]
    # 2. inline footnotes
    for name, rx in FOOTNOTE_INLINE:
        for m in list(rx.finditer(t)):
            logit(name, m.group(0), "inline")
        t = squash(rx.sub(" ", t))
    # 3. explicit page furniture anywhere
    for name, rx in [("navigation", re.compile(r"Return to D\. ?L\. Ashliman's folktexts, a library of folktales, folklore, fairy tales, and mythology\.?")),
                     ("revised_stamp", re.compile(rf"\bRevised (?:{MONTHS}) \d{{1,2}}, \d{{4}}\.?"))]:
        for m in list(rx.finditer(t)):
            logit(name, m.group(0), "inline")
        t = squash(rx.sub(" ", t))
    # 4. manual cut-from (applied before the automatic tail rule so it can pre-empt it)
    for r in rv:
        if r["action"] == "trim_from":
            k = t.find(r["pattern"])
            if k < 0:
                raise ValueError(f"{record_id}: trim_from pattern not found: {r['pattern']!r}")
            logit("manual_trim_from", t[k:], "end")
            t = t[:k].rstrip()
    # 5. automatic trailing cut at the first strong marker in the tail
    if not any(r["action"] == "no_auto_tail" for r in rv):
        hit = first_marker(t, cfg["tail_marker_min_relative_position"])
        if hit:
            name, pos, _, mode = hit
            cut = sentence_start_before(t, pos) if mode == "sentence" else pos
            tail = t[cut:]
            after = t[pos:]
            if NEW_TALE_START.search(after) and len(after.split()) > cfg["tail_review_max_words"]:
                flags.append("tail_contains_new_tale")
            logit(f"tail_cut:{name}", tail, "end")
            t = t[:cut].rstrip()
    # 6. manual removal of bibliographic residue left at the very end
    for r in rv:
        if r["action"] == "strip_suffix":
            t = t.rstrip()
            if not t.endswith(r["pattern"]):
                raise ValueError(f"{record_id}: strip_suffix pattern is not the text ending: {r['pattern']!r}")
            logit("manual_strip_suffix", r["pattern"], "end")
            t = t[: -len(r["pattern"])].rstrip()
    # 7. exact internal repetition
    t, rep = collapse_repetition(t)
    if rep:
        logit("exact_repetition", "(second copy of the text removed)", "end")
        flags.append("repetition_collapsed")
    t = squash(t)
    # residual non-narrative markers (should be none; reviewed if present)
    if early_markers(t, 1.01):
        flags.append("residual_marker")
    return t, flags


def run() -> pd.DataFrame:
    cfg = load_config()
    ccfg = cfg["cleaning"]
    commit = cfg["sources"]["trilogy_commit"]
    raw = pd.read_csv(RAW / "trilogy" / "aft.csv", dtype=str, keep_default_na=False, na_values=[], encoding="utf-8")
    review_df = load_review()
    review: dict[str, list] = {}
    for r in review_df.to_dict("records"):
        review.setdefault(r["record_id"], []).append(r)

    log: list = []
    rows = []
    for i, r in raw.iterrows():
        source_row = i + 1  # 1-based data row in the pinned CSV (header excluded)
        rid = f"aft-{commit[:7]}-{source_row:04d}"
        text_clean, flags = clean_text(rid, r["text"], review, ccfg, log)
        n_words = len(text_clean.split())
        if n_words < ccfg["short_text_words"]:
            flags.append("short_text")
        if CONNECTIVE_START.match(text_clean) or (text_clean[:1].islower()):
            flags.append("suspected_truncated_start")
        if text_clean[-1:] in (":", ",", ";") or (text_clean[-1:].isalpha()):
            flags.append("suspected_truncated_end")
        actions = {x["action"] for x in review.get(rid, [])}
        if "flag_fragment" in actions:
            flags.append("suspected_truncated_start")
        excluded = ""
        for x in review.get(rid, []):
            if x["action"] == "exclude":
                excluded = x["reason"]
        if not excluded and n_words < ccfg["min_words_after_cleaning"]:
            excluded = f"fewer than {ccfg['min_words_after_cleaning']} words after removing non-narrative material"
        rows.append(dict(
            record_id=rid, source_row=source_row, source_commit=commit,
            raw_row_sha256=sha256_text("\x1f".join(r[c] for c in raw.columns)),
            atu_id_raw=r["atu_id"], tale_title_raw=r["tale_title"], provenance_raw=r["provenance"],
            notes_raw=r["notes"], source_raw=r["source"], text_raw=r["text"], data_source=r["data_source"],
            date_obtained=r["date_obtained"],
            atu_id=None if r["atu_id"] == MISSING else r["atu_id"].strip(),
            title=fix_display(r["tale_title"]).strip(),
            provenance=None if r["provenance"] == MISSING else squash(fix_display(r["provenance"])),
            source=None if r["source"] == MISSING else squash(fix_display(r["source"])),
            notes=None if r["notes"] == MISSING else squash(fix_display(r["notes"])),
            text=text_clean, n_words_raw=len(r["text"].split()), n_words=n_words,
            mojibake_repaired=fix_display(r["text"]) != unicodedata.normalize("NFC", r["text"]),
            flags=";".join(sorted(set(flags))), excluded_reason=excluded,
        ))
    df = pd.DataFrame(rows)
    INTERIM.mkdir(parents=True, exist_ok=True)
    df.to_parquet(INTERIM / "records.parquet", index=False)
    (OUTPUTS / "audit").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(log, columns=["record_id", "rule", "position", "removed"]).to_csv(
        OUTPUTS / "audit" / "cleaning_log.csv", index=False, encoding="utf-8")
    print(f"  cleaned {len(df)} records; {len(log)} removals logged; "
          f"{(df.excluded_reason != '').sum()} records excluded as non-narrative")
    return df


if __name__ == "__main__":
    run()
