# legacy/

Work that is no longer part of the project. Nothing here is run by `python -m ouaw.run` or by `python -m analysis`.

## lesson_study/ (dropped 2026-11-11)

The "lesson study" asked whether a religious teaching collection keeps a folktale's plot and changes its lesson. It needed hand or machine codes for every version's lesson. The revised proposal of 11 November drops the lesson coding and places parables on the folklore map instead.

The folder mirrors the paths the files had in the repository:

| Path under `lesson_study/` | What it was |
| --- | --- |
| `analysis/frame.py` | built the annotation frame (religious-collection versions plus sampled other versions per tale type) |
| `analysis/aesop.py` | parsed *The Aesop for Children* for the hidden-moral check of the coder |
| `scripts/coding.py` | coding sheets and validation of coded lines |
| `scripts/draft_framing_review.py` | wrote `framing_review.csv` (64 religious-collection versions) |
| `data/annotations/` | codebook (version 1) and the machine codes entered so far (first pass and Aesop check, both incomplete) |
| `data/mappings/framing_review.csv` | the 64 versions with tradition, collection and how each was found |
| `data/processed/lesson_frame.csv`, `outputs/audit/lesson_frame*` | the frame and its summary |
| `data/raw/aesop/pg19994.txt` | Project Gutenberg #19994 |
| `config_sections.yaml` | the `frame` and `lessons` sections that had been added to `config.yaml` |
| `ANALYSIS_PLAN_lesson_study.md` | section 10 and the three change-log rows that had been added to ANALYSIS_PLAN.md |

None of these files had been committed. `config.yaml` and `ANALYSIS_PLAN.md` were returned to their committed state; the removed lines are kept in the two files above.

**What the new pipeline still uses.** The 36 calibration versions in `data/mappings/calibration_set.csv` are the rows of `framing_review.csv` found by the audit screen of 4 November. The other 28 rows (found by a wider screen on 11 November) are not used.

**To run it again**, copy the tree back over the repository root and append `config_sections.yaml` to `config.yaml`.
