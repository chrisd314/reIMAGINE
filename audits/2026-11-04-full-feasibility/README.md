# Full feasibility audit, 2026-11-04

Start with **[AUDIT.md](AUDIT.md)**. It opens with the decision and the evidence behind it, then gives the component verdicts, the data audit, the three pilots and the recommended plan.

This folder holds only audit materials. Nothing outside it was changed; see [Repository status](#repository-status) below.

## Contents

| Path | What it is |
| --- | --- |
| [AUDIT.md](AUDIT.md) | The full audit |
| [feasibility_matrix.csv](feasibility_matrix.csv) | Component-by-component verdicts (also §2 of the audit) |
| [source_manifest.csv](source_manifest.csv) | One row per source: purpose, URL, version, licence, access method, unit, fields, scope, missingness, usable counts, inspection status |
| [source_manifest_files.csv](source_manifest_files.csv) | Every request made: URL, final URL, UTC time, HTTP status, bytes, SHA-256, local file. It is a copy of `source_manifest_raw.csv`, the log that `scripts/fetch.py` appends to |
| [crosswalk/](crosswalk/) | Pilot A. `crosswalk_candidates.csv`: every candidate link with its route and evidence. `crosswalk_candidate_pairs_screened.csv`: pairs with the rule screen. `review_sample_keys.csv` / `review_sample_evidence.csv`: the 30 sampled links. **`crosswalk_reviewed.csv`: the hand-reviewed links with decisions and reasons.** `final_sample_rule_screen.csv`: the rule-screened final sample |
| [pilots/a_join/](pilots/a_join/) | Pilot A summary: rule-vs-hand agreement, coverage funnel, region × religion table, overlap diagnostic |
| [pilots/b_text_morals/](pilots/b_text_morals/) | Pilot B: items and segmentation, four similarity matrices, pre-declared pairs with passages, nearest neighbours, **provisional readings**, summary |
| [pilots/c_history/](pilots/c_history/) | Pilot C: evidence ladder for the two cases, similarity with controls |
| [evidence/](evidence/) | Existing-corpus profile; annotation frame (29 tale types; 36 religious-collection versions); SCCS religion tables; Jātaka table and cited parallels; course pages as text and the course method map; repository snapshots and git status before and after |
| [scripts/](scripts/) | Everything that produced the files above |
| `downloads/` | Raw third-party downloads and full pilot texts. **Git-ignored** ([.gitignore](.gitignore)) because rights differ by source: the Jātaka revision has no stated licence, ETCSL is copyrighted, and SCCS is CC BY-NC |

**Status of the judgements.** All crosswalk decisions, story readings and case assessments are the coding agent's and have not been checked by a person. They are labelled as such in each file. No human ratings, agreement statistics or accuracies were produced or implied.

## Repository status

- **Before the audit** (2026-11-04 11:40 UTC): branch `master` with no commits; 19 untracked top-level entries ([git_status_before.txt](evidence/git_status_before.txt)). 3,413 project files hashed, excluding `.git`, `.venv`, `node_modules`, `.tools`, caches and this folder ([snapshot_before.csv](evidence/snapshot_before.csv)).
- **After the audit:** all 3,413 files have identical SHA-256 hashes, with none added or removed ([snapshot_after.csv](evidence/snapshot_after.csv)). `git status` differs only by the new untracked `audits/` folder ([git_status_after.txt](evidence/git_status_after.txt)).
- The project's Python environment was used read-only, with `-B` so no bytecode was written.
- The existing site was served from `web/dist` and its desktop journey test was run, with screenshots written outside the repository. Its preview server was then stopped.

## Reproduce

Run from this folder with the project's environment. Use `-I` so downloaded files can never shadow Python modules, and `-B` so nothing is written into the repository.

```bash
PY=../../.venv/Scripts/python.exe      # Windows; ../../.venv/bin/python elsewhere
ROOT=../..                             # project root

# 1. Sources: compare a fresh download with the recorded hashes (the original downloads are in downloads/)
$PY -I -B scripts/refetch.py downloads_refetch

# 2. Pilot A: joining folklore traditions to religion-coded records
$PY -I -B scripts/sccs_religion.py
$PY -I -B scripts/crosswalk_candidates.py .
$PY -I -B scripts/crosswalk_sample.py          # reuses the frozen 30-link draw in crosswalk/review_sample_keys.csv
$PY -I -B scripts/crosswalk_review.py          # attaches the recorded hand decisions
$PY -I -B scripts/crosswalk_funnel.py

# 3. Existing corpus, Jātaka table, annotation frame
$PY -I -B scripts/corpus_profile.py $ROOT evidence/existing_corpus_profile.txt
$PY -I -B scripts/annotation_frame.py $ROOT
$PY -I -B scripts/jataka_table.py downloads/jataka/000-Jataka-Table.htm evidence/jataka_table.csv
$PY -I -B scripts/jataka_epub_parallels.py downloads/jataka/The-Jataka.epub evidence/jataka_cited_parallels.csv

# 4. Pilots B and C (the MiniLM model is read from the local Hugging Face cache)
HF_HUB_OFFLINE=1 $PY -I -B scripts/pilot_b.py . $ROOT
HF_HUB_OFFLINE=1 $PY -I -B scripts/pilot_c.py . $ROOT

# 5. Authored tables and the curated manifest
$PY -I -B scripts/write_tables.py .
$PY -I -B scripts/build_manifest.py .

# 6. Repository check
$PY -I -B scripts/repo_snapshot.py $ROOT evidence/snapshot_after.csv
```

**Notes on reproducing:**

- The original downloads were made with `scripts/fetch.py`, one URL per call with one-second pauses. The 209 MB Dataverse zip was never downloaded whole: `scripts/remote_zip.py` read 8 members by HTTP range requests and checked each one's CRC.
- Some sources regenerate their pages (course site, D-PLACE, eBible, the Jātaka EPUB), so the re-fetch report may show differing hashes. The analysis uses the copies in `downloads/`.
- Pilot B's TF-IDF uses the project's own `analysis.lexical.fit` and settings, fitted on the 1,498 existing narratives plus the pilot texts. Its embeddings use the project's pinned MiniLM revision and chunker.
