# Once Upon a World

A DTU 02805 *Social Graphs and Interactions* course project (hand-in 27 November 2026). The repository holds two pipelines that share one corpus and one set of core functions:

| | Command | What it is for |
| --- | --- | --- |
| **Paper pipeline** | `python -m ouaw.run --stage all` | Every number and figure of the paper: the folklore map and the parables placed on it |
| Website pipeline | `python -m analysis all` | The interactive site at <https://chrisd314.github.io/reIMAGINE/> (type versus place on the joint cohort) |

This repository holds code and results, not the paper. Read `results/RESULTS.md` for the numbers and DECISIONS.md for every judgement call behind them.

## The paper pipeline

**Question.** Do religious parables tell the same kinds of stories as the world's folktales, and do parables from different religions land in the same part of world folklore?

- **Part A, the map.** A text-similarity network of 1,462 folktales, its communities, what they are, and whether they follow tale type or region.
- **Part B, parables.** 281 parables from five traditions are each compared with all folktales, scored for how folktale-like they are, and attached to the map.

### Run it

Requirements: [uv](https://docs.astral.sh/uv/) with Python 3.11. About 2 GB of disk for PyTorch and the sentence encoder.

```bash
uv sync                                          # environment, versions pinned in uv.lock

uv run python -m ouaw.run --stage all            # everything, on the full data
uv run python -m ouaw.run --stage partB checks   # single stages, always run in pipeline order
uv run python -m ouaw.run --stage all --sample 100   # fast development run; writes to results/_sample and figures/_sample

uv run pytest                                    # unit tests and checks on the website outputs
```

| Stage | Module | What it does | Time on a laptop |
| --- | --- | --- | --- |
| `data` | `ouaw/corpus.py` | Splits the cleaned corpus into 1,462 folktales and 36 calibration versions. Nothing is re-cleaned | seconds |
| `parables` | `ouaw/parables/` | Segments the parables and cuts length-matched baseline passages; writes `data/processed/parables.csv` | 6 s from the cache |
| `partA` | `ouaw/part_a.py` | Graphs at 5%, 10%, 15% density; Louvain; modularity against degree-preserving shuffles; community words; LDA; type versus region; PageRank; layout | 15 min first time, 2 min after |
| `partB` | `ouaw/part_b.py` | Folk-closeness, tradition ranking with bootstrap intervals, both baselines, attachment to communities with shuffle nulls, distinctive words | 1 min |
| `checks` | `ouaw/checks.py` | Calibration gate, second method, length, hubness, masking, hand-label template | 3 to 20 min first time (masked embeddings), 1 min after |
| `figures` | `ouaw/figures.py`, `ouaw/report.py` | `figures/fig1`–`fig4` (PDF and PNG) and `results/RESULTS.md` | seconds |

Embeddings and shuffle nulls are cached by content, so a rerun only recomputes what changed. All seeds are fixed (`paper.yaml`, `config.yaml`).

### What it writes

| Path | Content |
| --- | --- |
| `results/RESULTS.md` | Every headline number next to its null or baseline, with the file it came from |
| `results/*.csv`, `*.json` | All tables: `partA_*` (map), `partB_ranking.csv` (each text with its 10 nearest folktales), `partB_traditions.csv`, `partB_attachment*.csv`, `calibration*.csv`, `checks_*.csv`, `top_pairs.csv`, `parables_*.csv` |
| `figures/fig1_map`, `fig2_closeness`, `fig3_placement`, `fig4_calibration` | The four figures, PDF and PNG |
| `data/processed/parables.csv` | The parables and baseline passages: `id, tradition, kind, source, translator, year, title, text, n_tokens, url, retrieved_at, segment_note` |
| `labeling/segmentation_check.csv` | 20 random parables per tradition with their first and last 30 words, for a hand check of the segmentation |
| `labeling/hand_labels_template.csv` | The top-1 parable–folktale pair of 100 parables, with empty `coder1` and `coder2` columns |

### Hand labels

1. Copy `labeling/hand_labels_template.csv` to `labeling/hand_labels.csv`.
2. Two people fill `coder1` and `coder2` independently with `same_plot`, `shared_motif`, `theme_only` or `unrelated`.
3. `uv run python -m ouaw.agreement` writes raw agreement, Cohen's κ, the confusion table and precision to `results/`.
4. `uv run python -m ouaw.run --stage figures` puts the precision into Figure 4 and RESULTS.md.

The pipeline never fills a label. Until `hand_labels.csv` exists, Figure 4 shows "pending".

### Data sources

| Data | Edition | Where from | Retrieved | Status |
| --- | --- | --- | --- | --- |
| Folktales (1,498 versions) | Hagedorn & Darányi (2022), *Annotated Folktales*, from D. L. Ashliman's *Folktexts* | github.com/j-hagedorn/trilogy, commit `d57c2ce` | 2026-11-11 | CC BY-NC-SA 4.0 by the more restrictive of two statements in the repository (LICENSE_NOTES.md) |
| Christian parables and baseline | World English Bible | ebible.org, `engwebp_vpl.zip` | 2026-11-11 | Public domain, as stated in the archive |
| Buddhist parables | *The Jātaka*, ed. E. B. Cowell, 6 vols (1895–1907); *Saddharma-Puṇḍarīka*, tr. H. Kern, SBE 21 (1884) | sacred-texts.com | 2026-11-11 | Published before 1908; see the note below |
| Buddhist baseline | *The Dhammapada*, tr. F. Max Müller, SBE 10 (1881) | sacred-texts.com | 2026-11-11 | as above |
| Jewish parables and baseline | S. Rapaport, *Tales and Maxims from the Midrash* (1907); C. Taylor, *Sayings of the Jewish Fathers* (1897) | sacred-texts.com | 2026-11-11 | as above |
| Sufi parables and baseline | *Masnavi i Ma'navi*, tr. and abridged E. H. Whinfield (1898) | sacred-texts.com | 2026-11-11 | as above |
| Taoist parables and baseline | *The Texts of Taoism*, tr. J. Legge, SBE 39–40 (1891): the Zhuangzi and the Tao Te Ching | sacred-texts.com | 2026-11-11 | as above |

Every downloaded page is logged with its URL, time and SHA-256 in `data/raw/parables/fetch_log.csv`. The raw pages are cached in `data/raw/parables/` and are not committed.

**Note on sacred-texts.com.** The books are public-domain works published between 1881 and 1907 (public domain in the United States; the life-plus-70 status of each translator was not checked). The site's own terms of use ask users "not to … scrape … the service outside its documented interfaces", while its `robots.txt` allows all paths. The pages were collected on 11 November 2026 at one request per second before the terms were read. For that reason:

- downloading is **off by default**. The `parables` stage works from the cache; if the cache is missing it keeps the committed `parables.csv` and says so;
- `--fetch` switches downloading on. Decide first whether to keep this source, ask the site, or replace it with another copy of the same editions;
- nothing from the site's own markup, design or commentary is stored in `parables.csv`.

### Settings and layout

```text
paper.yaml             settings of the paper pipeline (seeds, shuffles, targets, masking, figure sizes)
config.yaml            frozen text and graph settings shared with the website pipeline
ouaw/                  paper pipeline: run.py, corpus.py, reps.py, part_a.py, part_b.py, checks.py,
                       agreement.py, figures.py, report.py, parables/ (one module per tradition)
analysis/              data stages (fetch, clean, cohorts), core functions (TF-IDF, embeddings, networks,
                       metrics) and the website pipeline
data/mappings/         calibration_set.csv (the 36 versions), parables/*.yaml (verse ranges, anchors)
data/processed/        narratives.parquet (folktales, git-ignored), parables.csv
results/, figures/, labeling/   outputs of the paper pipeline
legacy/                the dropped lesson study (kept, never run)
tests/                 test_ouaw.py (paper pipeline, toy inputs); the other files test the website pipeline
```

Documents: AUDIT.md (state of the repository before this work), DECISIONS.md (every judgement call), PROGRESS.md (status and how to resume), `results/RESULTS.md` (the numbers).

## The website pipeline

*Do folktales form communities around where they were recorded, or around the kind of story they tell?* The site explores this on the 1,133 tales that have both an ATU type and a mapped place. It is not extended any more; it is kept working.

```bash
uv run python -m analysis all      # fetch -> clean -> audit -> cohorts -> TF-IDF -> embeddings -> graphs
                                   # -> modularity null -> distance -> validation sample -> layouts -> web export
uv run python scripts/summarise_run.py

cd web
npm ci
npm run dev        # development server: http://localhost:5173/
npm run build      # type-check + production build into web/dist
npm run preview    # serve the production build: http://localhost:4173/
```

Node.js ≥ 20.19 is needed for the site (Node 24 LTS was used). If Node is not installed system-wide, a portable Node can be placed in `.tools/` (git-ignored). On Windows: `$env:PATH = "$PWD\.tools\node-v24.22.2-win-x64;$env:PATH"`.

Re-runs skip stages whose inputs (config section and content hashes of upstream files) are unchanged; add `--force` to rerun. Browser checks, with a server running: `uv run python tests/browser/journey.py http://localhost:4173/ outputs/browser/journey-desktop`, plus `--mobile`, `--keyboard`, `--reduced`.

| Stage | Module | Main outputs |
| --- | --- | --- |
| fetch | `analysis/fetch.py` | `data/raw/` (immutable) and `data/raw/source_manifest.json` (URL, commit, SHA-256, licence, role) |
| clean | `analysis/clean.py` | `data/interim/records.parquet`, `outputs/audit/cleaning_log.csv` |
| audit | `analysis/audit.py` | `outputs/audit/raw_audit.json` |
| cohorts | `analysis/cohorts.py` | `data/processed/narratives.parquet`, `cohorts.csv`, `outputs/audit/inclusion_ledger.csv` |
| lexical | `analysis/lexical.py` | one TF-IDF space (negation kept) and a name-masked variant |
| semantic | `analysis/semantic.py` | MiniLM chunk and tale vectors (chunks of at most 200 tokens, cached by content hash) |
| analyze | `analysis/analyze.py` | graphs at 5/10/15%, Louvain (seeds 42/7/19), NMI, assortativity and neighbour checks with 1,000 label shuffles |
| modnull | `analysis/modnull.py` | degree-preserving null for modularity |
| distance | `analysis/distance.py` | haversine distance against similarity, whole-location shuffles |
| validation | `analysis/validation.py` | blind stratified review sample; the summary stays *pending* until annotations exist |
| layouts | `analysis/layouts.py` | display-only layouts and PCA |
| export | `analysis/export.py` | `web/public/data/` (one `run_id` on every payload) |

**Deployment.** `.github/workflows/deploy-pages.yml` runs the website pipeline and the tests, builds `web/` and deploys `web/dist` on every push to `master` that touches the analysis, the data or the site. The public build is excerpt-only: the workflow sets `OUAW_PUBLIC_BUILD=1`, which ships the first 120 words of each tale instead of full texts (LICENSE_NOTES.md). To reproduce it locally: `OUAW_PUBLIC_BUILD=1 uv run python -m analysis export`, then `cd web && npm run build && npm run preview`.

**Validation page.** A blind annotation tool. Export its CSVs to `outputs/validation/annotations/`, then run `uv run python -m analysis validation export`. Until then the status is *pending*.

Website documents: ANALYSIS_PLAN.md (frozen plan and change log), METHOD_MAP.md, INTERACTION_SPEC.md, LIMITATIONS.md, LICENSE_NOTES.md, SOURCES.md, AI_METHODS.md, STATUS.md.

## Licence

The folktale dataset is treated as CC BY-NC-SA 4.0 (LICENSE_NOTES.md). Full folktale texts are shown only in the local preview of the site. The code licence is not yet chosen.
