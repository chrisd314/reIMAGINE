# Licence notes

These are notes for a noncommercial educational project (DTU 02805). They are not legal advice. Nobody has been contacted on the project's behalf.

## 1. The dataset (trilogy repository, pinned commit `d57c2ce`)

| Where | What it says |
| --- | --- |
| `README.md` at the pinned commit | “This repository is licensed under a CC-BY-SA 4.0 open license. Its contents are either in the public domain, or permissions have been granted by the copyright holder for inclusion.” |
| `LICENSE.md` at the pinned commit | Full text of **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International** (CC BY-NC-SA 4.0) |
| Zenodo record 6575263 (release v1.1, 2022-05-24) | licence id `other-open` |

**The discrepancy is recorded, not resolved.** This project follows the more restrictive reading, CC BY-NC-SA 4.0:

- noncommercial use only
- attribution to the dataset and its sources (see SOURCES.md)
- share-alike terms for any adapted data we redistribute, such as `data/processed/` and the website payloads
- notices preserved: `data/raw/trilogy/README.md` and `LICENSE.md` are kept verbatim

## 2. The texts themselves

- The tales come from D. L. Ashliman's *Folktexts* (University of Pittsburgh), whose index page reads “edited and/or translated by D. L. Ashliman … © 1996-2026”. Many texts are public-domain translations; some are Ashliman's own translations. The dataset README says permissions were granted for inclusion, but the scope of any permission for third parties is not documented.
- Some tales from the National Folklore Collection's Schools' Collection (dúchas.ie) carry their own notice in the `notes` field: **CC BY-NC 4.0**.
- Other individual sources may have their own restrictions; the bibliographic `source` field of every record is kept and displayed.

## 3. What this means for the website

- **The local preview shows full texts for private study and annotation.** This is controlled by `export.include_full_texts` in `config.yaml`.
- **Before any public deployment**, which has not been done and was not authorised, the authors should:
  1. set `include_full_texts: false` (pages then show a short excerpt plus the source citation), **or**
  2. obtain confirmation from the rights holders that republication is covered.

  Either way, the CC BY-NC-SA attribution and share-alike terms apply to the derived data.
- Maps use Natural Earth (public domain) via world-atlas (ISC). Fonts are Source Serif 4 and Inter (SIL Open Font License, via @fontsource).

## 4. The model

`sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, Apache-2.0. Only vectors derived from it are exported; the model is not redistributed.

## 5. The software

The code in `analysis/`, `tests/`, `scripts/` and `web/src/` is the project's own work and is licensed **separately** from the data. A code licence has **not** been chosen yet; this is a decision for the authors (see STATUS.md). Until then the `pyproject.toml` licence field says “to be decided”.

## 6. Not reproduced

No song lyrics or unrelated copyrighted decorative content is used. Course material is cited by URL rather than copied.
