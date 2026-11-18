# reIMAGINE

A DTU 02805 *Social Graphs and Interactions* course project (hand-in 27 November 2026): where religious parables land in the world of folktales.

**Question.** Do parables from different religious traditions fall within folktale communities more than non-story text from the same translations does, and which folktale communities and tale types do they land in? ("Are parables just folktales with a moral attached?" is the motivation only: text similarity cannot measure a moral, so it is not tested.)

**Website:** <https://chrisd314.github.io/reIMAGINE/>, five pages, every one of them interactive:

- **Overview:** the question, the three steps, the main result, every check at once, and what can and cannot be answered.
- **Folktales** (parts 1 and 2):
  - the corpus and its ATU tale types;
  - text similarity and the network, with degrees and clustering against random graphs;
  - Louvain communities, and whether they follow story, place or book;
  - edge construction as a modelling choice, and PageRank.
- **Parables** (part 3):
  - the parables and their same-translation baseline;
  - a test of the method on 36 held-out retellings;
  - closeness to folktales, and where the parables land;
  - what the resemblance rests on, and the robustness checks.
- **Explore:** the whole network, zoomable. Search any folktale or parable, colour by community, tale type, region or book, size by links or PageRank, put a tradition's parables on the map, switch to embeddings.
- **Methods & sources:** every method with the course week that teaches it.

Every map zooms and pans, and every tale opens with its ten nearest folktales and the words behind each match. Two texts can be read side by side, and each links to its full text at the source (the D. L. Ashliman Folktexts page it was taken from; sacred-texts.com or eBible.org for the parables). The label test and the permutation test can be rerun in the browser on the same data as the pipeline. A switch on every section turns the whole site from TF-IDF to embeddings.

## What is in here

1. **Folklore: tale types.** 1,462 English folktales, each with its ATU tale type, recorded region and source book.
2. **Communities.** A text-similarity network (TF-IDF; embeddings as a second method), Louvain communities, and what they follow: tale type, region (location) or source book. Also how much of this depends on how edges are built.
3. **Parables into the communities.** 281 parables from five traditions against 168 non-story passages cut from the same translations (the baseline), with the parable/passage label shuffled within each tradition as the null. The robustness checks are length-matched folktale excerpts, nouns masked, names and formulae masked, hubs removed, other graphs and the other representation.

One command runs everything: `python -m reimagine.run --stage all`. It writes:

- every number, table and figure (`results/`, `figures/`);
- the report material (`report/`);
- the website's data (`data/site/story.json`, `network.json`, `near.json`).

No number on the site is typed by hand.

## Run it

Requirements: [uv](https://docs.astral.sh/uv/) with Python 3.11 (about 2 GB of disk for PyTorch and the sentence encoder), and Node.js ≥ 20.19 for the website.

```bash
uv sync --group paper                                # environment pinned in uv.lock; `paper` adds spaCy for the noun masking
uv run python -m reimagine.run --stage all           # everything on the full data, including the website build
uv run python -m reimagine.run --stage partB checks  # single stages, always run in pipeline order
uv run python -m reimagine.run --stage all --sample 100   # fast development run into results/_sample, figures/_sample
uv run pytest                                        # unit tests and checks on the outputs

cd web && npm ci && npm run dev                      # the website at http://localhost:5173/ (npm run build, npm run preview)
uv run python tests/browser/site_check.py            # with `npm run preview` running: every page and interaction, desktop and phone
```

If Node is not installed system-wide, a portable Node can sit in `.tools/` (git-ignored); the `site` stage finds it.

| Stage | Module | What it does | Time on a laptop |
| --- | --- | --- | --- |
| `data` | `reimagine/corpus.py`, `reimagine/core/` | Fetches the pinned corpus, cleans it and builds cohorts when needed (`core.prepare`). Splits the 1,462 folktales from the 36 held-out retellings and asserts no retelling or near-copy is in the pool. Adds source collection and translator | seconds after the first run |
| `parables` | `reimagine/parables/` | Segments the parables and cuts length-matched baseline passages; writes `data/processed/parables.csv` | 10 s from the cache |
| `partA` | `reimagine/part_a.py` | Graphs at 5%, 10%, 15% density; Louvain; modularity against degree-preserving shuffles; community words; LDA; type against region; PageRank; layout | 1 min (15 min the first time) |
| `partB` | `reimagine/part_b.py` | Folk-closeness, nearest folktales, tradition ranking, attachment to communities | seconds |
| `vocab` | `reimagine/vocab.py` | spaCy part-of-speech tags (cached); nouns masked; the words behind every top-1 match | 20 s (5 min the first time) |
| `headline` | `reimagine/headline.py` | Parables against the same-translation baseline, permutation within tradition, community profile, voted tale types | seconds |
| `length` | `reimagine/length.py` | Length-matched folktale excerpts, length regression, baseline length matching | seconds (4 min the first time) |
| `network` | `reimagine/network.py` | Edge-construction sweep (densities, kNN), within-collection shuffles, masked map, backbones, structure against random graphs, community table | 3–10 min |
| `checks` | `reimagine/checks.py` | Calibration on the held-out retellings (recall@10, type vote, nouns masked), second method, length, hubness, masking | 20 s |
| `robustness` | `reimagine/robustness.py` | Table 1: the headline under every check, with a fixed yes/partly/no rule | 20 s |
| `figures` | `reimagine/figures.py`, `reimagine/report.py` | Figures 1–3 and S1–S2; report material in `report/` | 10 s |
| `site` | `reimagine/site.py`, `reimagine/folktexts.py` | `data/site/story.json`, `network.json`, `near.json`, then `npm run build` | 15 s |

Embeddings, part-of-speech tags and shuffle nulls are cached by content, so a rerun only recomputes what changed. All seeds are fixed (`paper.yaml`, `config.yaml`).

## What it writes

| Path | Content |
| --- | --- |
| `results/*.csv`, `*.json` | All tables: `headline_*`, `length_*`, `match_drivers*`, `network_*`, `community_table.csv`, `collection_*`, `table1_robustness.csv`, `robustness_headline.csv`, `partA_*`, `partB_*`, `calibration*.csv`, `checks_*.csv`, `parables_*.csv` |
| `results/corpus_audit/` | Audit of the data preparation: cleaning log, inclusion ledger, near-duplicates, diagnostics of the raw file |
| `figures/` | `fig1_map`, `fig2_headline`, `fig3_validity`, `figS1_labels`, `figS2_headline_embedding` (PDF and PNG) |
| `report/` | Material for the paper. Written by the pipeline: `RESULTS.md` (every number in paper order), `numbers.tex` (a LaTeX macro for each), `table1.tex`, `community_table.tex`, `captions.md`, `short_update.md`. Kept by hand: `LIMITATIONS.md` |
| `data/site/` | The website's data: `story.json` (results of both representations, every parable, passage and retelling), `network.json` (both networks: layout, degrees at each threshold, Louvain seeds, the partitions of all 12 graphs, PageRank and its shuffles, the label-test arrays), `near.json` (the ten nearest folktales of every tale and text, the words behind each match, openings). Openings of at most 40 words, never full texts |
| `data/processed/parables.csv` | The parables and baseline passages with source, translator, year and URL |

## Data sources

| Data | Edition | Where from | Retrieved | Status |
| --- | --- | --- | --- | --- |
| Folktales (1,498 versions; 1,462 in the network, 36 held out) | Hagedorn & Darányi (2022), *Bearing a Bag-of-Tales: An Open Corpus of Annotated Folktales for Reproducible Research*, Journal of Open Humanities Data 8: 16, [doi:10.5334/johd.78](https://doi.org/10.5334/johd.78), built on D. L. Ashliman's *Folktexts* (University of Pittsburgh) | github.com/j-hagedorn/trilogy at commit `d57c2ce`: `aft.csv` (the corpus) and `atu_df.csv` (tale-type names); the repository's `README.md` and `LICENSE.md` and the Zenodo record are kept as licence records. Ashliman's two index pages (`folktexts.html`, `folktexts2.html`) are kept as attribution records and to link every tale to the page it was taken from | 2026-11-11 | CC BY-NC-SA 4.0, the more restrictive of two statements in the repository (LICENSE_NOTES.md) |
| Christian parables and baseline | World English Bible | ebible.org, `engwebp_vpl.zip` | 2026-11-11 | Public domain, as stated in the archive |
| Buddhist parables | *The Jātaka*, ed. E. B. Cowell, 6 vols (1895–1907); *Saddharma-Puṇḍarīka*, tr. H. Kern, SBE 21 (1884) | sacred-texts.com | 2026-11-11 | Published before 1908; see the note below |
| Buddhist baseline | *The Dhammapada*, tr. F. Max Müller, SBE 10 (1881) | sacred-texts.com | 2026-11-11 | as above |
| Jewish parables and baseline | S. Rapaport, *Tales and Maxims from the Midrash* (1907); C. Taylor, *Sayings of the Jewish Fathers* (1897) | sacred-texts.com | 2026-11-11 | as above |
| Sufi parables and baseline | *Masnavi i Ma'navi*, tr. and abridged E. H. Whinfield (1898) | sacred-texts.com | 2026-11-11 | as above |
| Taoist parables and baseline | *The Texts of Taoism*, tr. J. Legge, SBE 39–40 (1891): the Zhuangzi and the Tao Te Ching | sacred-texts.com | 2026-11-11 | as above |

Tale types follow Uther (2004), *The Types of International Folktales* (FF Communications 284–286). Regions are UN M49 sub-regions. The mapping from recorded places to regions (`data/mappings/provenance_map.csv`) was drafted once with Natural Earth country points (public domain) and then reviewed row by row; the Natural Earth files are not needed to run anything. The sentence encoder is `sentence-transformers/all-MiniLM-L6-v2` at revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (Apache-2.0).

Every downloaded file is listed with its URL, version, retrieval time and SHA-256 in `data/raw/source_manifest.json` (folktale corpus) and `data/raw/parables/fetch_log.csv` (parables). The raw parable pages are cached in `data/raw/parables/` and are not committed.

**Note on sacred-texts.com.** The books are public-domain works published between 1881 and 1907 (public domain in the United States; the life-plus-70 status of each translator was not checked). The site's own terms of use ask users "not to … scrape … the service outside its documented interfaces", while its `robots.txt` allows all paths. The pages were collected on 11 November 2026 at one request per second before the terms were read. For that reason:

- downloading is **off by default**. The `parables` stage works from the cache; if the cache is missing it keeps the committed `parables.csv` and says so;
- `--fetch` switches downloading on. Decide first whether to keep this source, ask the site, or replace it with another copy of the same editions;
- nothing from the site's own markup, design or commentary is stored in `parables.csv`.

## Layout

```text
README.md, LICENSE_NOTES.md   this file; licence notes for the data
config.yaml            sources, cleaning, cohorts, TF-IDF, embedding and graph settings (fixed 29 October)
paper.yaml             settings of each analysis stage (seeds, shuffles, masking, figure sizes)
reimagine/             the pipeline: run.py and one module per stage; parables/ (one module per tradition)
  core/                data preparation (fetch, clean, audit, cohorts) and core functions (TF-IDF, embeddings,
                       networks, metrics)
web/                   the website (Vite + React + TypeScript); scripts/copy-data.mjs copies data/site/ into the build
data/                  raw (pinned), mappings (reviewed decisions), processed, site
results/, figures/     analysis outputs
report/                material for the paper
proposition/           the submitted project proposal
tests/                 unit tests on toy inputs, checks on the data and the site's data file, browser/site_check.py
ai-assist/             everything about the AI coding assistant: decision log, progress notes, AI-use log
```

**Deployment.** `.github/workflows/deploy-pages.yml` builds the site from the committed `data/site/` files and deploys `web/dist` on every push to `master` that touches `data/site/` or `web/`. It refuses to deploy if any published opening is longer than the excerpt limit.

## Course and credits

DTU 02805 *Social Graphs and Interactions* (2026), Sune Lehmann: <https://sunelehmann.com/socialgraphs2026-web/index.html>. The website's Methods & sources page maps every method to the week that teaches it.

Software: Python 3.11 with pandas, NumPy, SciPy, scikit-learn, NetworkX, sentence-transformers, PyTorch, spaCy, ftfy, PyYAML, Matplotlib and Playwright. The website uses Node.js 24 with React 19, Vite 8 and TypeScript 5.9. Exact versions are in `uv.lock` and `web/package-lock.json`.

## Licence

The folktale dataset is treated as CC BY-NC-SA 4.0 (LICENSE_NOTES.md). The website shows only titles, labels and openings of at most 40 words. The code licence is not yet chosen.
