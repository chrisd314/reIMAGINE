"""Draft of data/mappings/framing_review.csv: which story versions come from a religious teaching collection.

"Religious framing" is a property of the COLLECTION a version was printed in, never of the
people who told the tale. A version is coded `religious` when the corpus attributes its text to

  (a) scripture or canonical religious literature (Jataka, Udana, the Tibetan Kangyur,
      the Chinese Tripitaka, the Hebrew Bible, the Talmud, the Mahabharata), or
  (b) a collection compiled for preaching or religious instruction (Gesta Romanorum,
      Jacques de Vitry's sermon exempla, Pauli's Schimpf und Ernst, Geiler's and Purselt's
      sermons, Petrus Alfonsi's Disciplina Clericalis, Luther's Table Talk, Rumi's Masnavi,
      Sri Ramakrishna's Teachings).

`mediated` marks versions that reach the corpus through a later secular retelling or a
scholarly paraphrase (for example Joseph Jacobs retelling a Jataka). They stay in the
primary analysis and are dropped in a sensitivity check.

How the candidates were found (2026-11-11): two regular-expression screens over the
provenance, source, title and notes fields (the audit's screen of 2026-11-04, then a wider
one for Buddhist, Hindu, Jewish, Islamic and Christian collection names). Every hit was read
in its metadata; 62 were accepted and the rest left as `other`. A third check, made while
coding, listed the source field of every sampled `other` version in the frame and read all of
them: it added two (Sana'i's Sufi poem and an account of Jesus from Arabic religious writers),
decided from the source field alone, for 64 in all. Rejected on reading,
for example: 'The Bible and Key Trial' and 'The Fable of the Flying Dutchman' (folk texts
that mention a Bible), Uncle Remus tales ('Rabbit' matches 'Rabbi'), monkey tales ('Monk'),
the Panchatantra, Hitopadesa and Kalila wa Dimna (statecraft and wisdom books, not religious
instruction), Nasreddin Hodja jests, Friedlander's Jewish Fairy Book and Lang's 'The Lion and
the Saint' (children's retellings whose corpus source is not a religious work).

These are the coding agent's decisions. Every row says so and waits for a human check.

    uv run python scripts/draft_framing_review.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# collection key -> (tradition, collection name, basis)
COLLECTIONS = {
    "jataka": ("Buddhist", "Jātaka", "scripture"),
    "udana": ("Buddhist", "Udāna (Pali canon)", "scripture"),
    "kangyur": ("Buddhist", "Kangyur (Schiefner, Tibetan Tales)", "scripture"),
    "tripitaka": ("Buddhist", "Chinese Tripiṭaka (Book of the Hundred Apologues)", "scripture"),
    "gesta": ("Christian", "Gesta Romanorum", "teaching collection"),
    "vitry": ("Christian", "Jacques de Vitry, sermon exempla", "teaching collection"),
    "pauli": ("Christian", "Johannes Pauli, Schimpf und Ernst", "teaching collection"),
    "geiler": ("Christian", "Geiler von Kaysersberg, sermons", "teaching collection"),
    "purselt": ("Christian", "Conrad Purselt, Sunday sermons", "teaching collection"),
    "alfonsi": ("Christian", "Petrus Alfonsi, Disciplina Clericalis", "teaching collection"),
    "luther": ("Christian", "Martin Luther, Table Talk", "teaching collection"),
    "kings": ("Jewish", "Hebrew Bible (1 Kings)", "scripture"),
    "talmud": ("Jewish", "Talmud", "scripture"),
    "rumi": ("Islamic (Sufi)", "Rumi, Masnavi", "teaching collection"),
    "sanai": ("Islamic (Sufi)", "Sana'i, Hadiqat al-Haqiqa", "teaching collection"),
    "qisas": ("Islamic", "Arabic legends of Jesus (stories of the prophets)", "teaching collection"),
    "mahabharata": ("Hindu", "Mahābhārata", "scripture"),
    "ramakrishna": ("Hindu", "Sri Ramakrishna's Teachings", "teaching collection"),
}

DECISIONS = {
    "jataka": "0218 0224 0225 0260 0296 0484 0562 0713 0774 0858 0938 0939 1019 1140 1144 1175 1221 1233",
    "gesta": "0029 0094 0098 0410 0465 0599 0682 0736 0747 0940 1171 1311",
    "vitry": "0011 0855",
    "rumi": "0345 0413 0417 0563",
    "talmud": "1109",
    "udana": "0114",
    "ramakrishna": "0112",
    "kings": "0222",
    "kangyur": "0215 0602 0778 0948 1069 1230 1247",
    "pauli": "0872 0900 0941 1081 1303",
    "geiler": "0135",
    "purselt": "0676",
    "luther": "0370 0878 0897 0899 1329",
    "mahabharata": "0511",
    "alfonsi": "0412",
    "tripitaka": "1063",
    "sanai": "0113",
    "qisas": "1225",
}

# Versions that reach the corpus through a later retelling or a scholar's paraphrase.
MEDIATED = {
    "tale-1144": "retold by Joseph Jacobs in Indian Fairy Tales (1892)",
    "tale-1109": "paraphrased by W. A. Clouston in Flowers from a Persian Garden (1890)",
    "tale-0412": "retold by P. F. Baum in a journal article (1917)",
    "tale-1063": "quoted in W. Norman Brown's article on the silence-wager stories (1922)",
    "tale-1225": "summarised from Arabic writers by M. C. Siddi Lebbe in The Orientalist (1884)",
}

FOUND_BY_AUDIT_SCREEN = set(
    "0011 0029 0094 0098 0218 0224 0225 0260 0296 0345 0410 0413 0417 0465 0484 0562 0563 0599 0682 0713 0736 0747 0774 "
    "0855 0858 0938 0939 0940 1019 1109 1140 1144 1171 1175 1221 1233".split())


def main() -> None:
    nar = pd.read_parquet(ROOT / "data/processed/narratives.parquet").set_index("narrative_id")
    rows = []
    for key, ids in DECISIONS.items():
        tradition, collection, basis = COLLECTIONS[key]
        for short in ids.split():
            nid = f"tale-{short}"
            r = nar.loc[nid]
            rows.append(dict(
                narrative_id=nid, atu_id=r["atu_id"], title=r["title"], framing="religious", tradition=tradition,
                collection=collection, basis=basis, mediated=nid in MEDIATED, mediated_note=MEDIATED.get(nid, ""),
                found_by=("audit screen 2026-11-04" if short in FOUND_BY_AUDIT_SCREEN else
                          "source check of sampled versions 2026-11-11" if key in ("sanai", "qisas") else "wider screen 2026-11-11"),
                source=r["source"] if isinstance(r["source"], str) else "",
                review_status="agent-reviewed from metadata; human check pending"))
    out = pd.DataFrame(rows).sort_values("narrative_id")
    assert out["narrative_id"].is_unique
    path = ROOT / "data/mappings/framing_review.csv"
    out.to_csv(path, index=False, lineterminator="\n")
    print(f"wrote {path.relative_to(ROOT)}: {len(out)} religious-collection versions, "
          f"{out['collection'].nunique()} collections, {int(out['mediated'].sum())} mediated")
    print(out.groupby(["tradition", "collection"]).size().to_string())


if __name__ == "__main__":
    main()
