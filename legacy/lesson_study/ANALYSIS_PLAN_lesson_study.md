## 10. Lesson study (frozen 2026-11-11, before any version was coded)

**Question.** When a religious teaching collection retells a folktale, does the plot stay while the lesson changes? The type-versus-place analysis above (sections 1–9) is unchanged and becomes the supporting result: text groups follow tale type.

**Frame** (`analysis/frame.py`, `data/mappings/framing_review.csv`). Framing is a property of the collection a version was printed in. The frame is every tale type with at least one religious-collection version and at least one other version, all its religious-collection versions, and up to 3 other versions per type (seed 2805; complete texts first, one per source where possible). The frame is built from metadata only. One type told only in religious collections of two traditions (ATU 243A) is coded for description and excluded from every test.

**Codes** (`data/annotations/codebook.yaml`, version 1). Per version: `outcome`, `behaviour` (the lesson the version itself teaches), `story_behaviour` (the lesson of the narrative alone), `mode`, `justification`, `lesson_place`, `confidence`, a one-sentence `lesson_text` and a verbatim `quote`.

**Who codes.** The codes analysed here are **machine codes**: the coding agent (Claude) read each version and applied the codebook. They are an instrument that has to be checked, in the sense of the course's Tool mode, and are never reported as human labels. Checks, in order of strength:

1. *Hidden-moral check.* For 30 fables of *The Aesop for Children* (seed 2805) the coder infers the lesson from the narrative with the printed moral removed. Score: the rank of the fable's own printed moral among all printed morals by embedding similarity to the inferred lesson, against the chance rank; and agreement between the behaviour code of the story and the behaviour code of the printed moral (coded separately, morals only, shuffled).
2. *Second pass.* 40 frame versions (seed 2805) are coded again without the first codes in view. Raw agreement and a confusion table per field.
3. *Verbatim quotes.* Every `quote` must be a substring of the stored text (automatic).
4. *Human check (pending until files exist).* The coding sheet on the website's Validation page records the same fields. When human files are in `data/annotations/human/`, the pipeline reports machine–human agreement per field and reruns every test on the human codes.

Long texts are shown to the coder in full up to 700 words, otherwise as the first 300 and last 400 words.

**Quantities.** Pairs are unordered pairs of frame versions of the same tale type; a pair is *across* (one religious, one other) or *within* (same framing).

| | Statistic | Reference (1,000 draws, seed 20261111) |
| --- | --- | --- |
| H1 | For each religious-collection version: is its nearest *other* version in the whole text cohort of the same tale type (share, TF-IDF and embeddings)? Mean cosine of same-type cross-framing pairs minus different-type cross-framing pairs in the frame | tale-type labels shuffled |
| H2 | D = share of *within* pairs with the same `behaviour` minus share of *across* pairs with the same `behaviour`; also for `story_behaviour` and for `outcome` | framing labels shuffled within tale type |
| H3 | Share of religious-collection versions with a `divine` or `karmic` justification minus the share among other versions | the same shuffles |
| H4 | Share of a version's 10 nearest frame neighbours that carry its `behaviour`; `behaviour` assortativity on the 10%-density text network restricted to the frame (TF-IDF and embeddings) | `behaviour` shuffled within tale type; a global shuffle is shown for scale |

One-sided p = (1 + #(null ≥ observed)) / (1 + N). A pair with a `none` code never matches. Tale types, not pairs, are the independent units, so results are descriptive for this corpus.

**Sensitivity, declared now:** macro-average over tale types instead of pooling pairs; dropping the 4 mediated versions; versions with confidence ≥ 2 only; types with at least two other versions only.

**Descriptive only:** which behaviour codes each collection uses; distinctive words of religious against other lesson quotes (week 6, section 3).

| 2026-11-11 | Lesson study added (section 10); new `frame` and `lessons` settings in `config.yaml`; *The Aesop for Children* added to the sources. | The project question was narrowed after the feasibility audit of 2026-11-04 (`audits/`). Sections 1–9 and their settings are untouched; run IDs change only because the configuration file gained sections. |
| 2026-11-11 | Religious-collection frame widened from the audit's 36 versions in 29 tale types to 61 versions in 43 tale types (plus one religious-only type). | The audit's metadata screen was hand-checked as planned. A wider screen found 26 more versions from religious teaching collections (Pauli, Luther's Table Talk, Geiler, the Kangyur, the Udāna, 1 Kings, the Mahābhārata and others). Decided from metadata before any lesson was coded. |
| 2026-11-11 | Lesson codes are machine codes checked by a hidden-moral test, a second pass and (pending) a human sample, instead of hand codes by the group. Valence is recorded as a teaching `mode` rather than as part of the match rule. | No human codes exist yet; the course treats a model's labels as an instrument to be checked (Tool mode; week 8, "Validate your choices"). The human coding sheet uses the same codebook, and the pipeline reruns on human codes when they exist. |
