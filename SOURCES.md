# Sources

Every downloaded file is listed with its URL, version, retrieval time, SHA-256, size, format, citation, stated licence and role in `data/raw/source_manifest.json`. The website's Sources page shows the same manifest.

## Data

1. **Annotated Folktales (AFT)**: Hagedorn, J. & Darányi, S. (2022). *Bearing a Bag-of-Tales: An Open Corpus of Annotated Folktales for Reproducible Research.* Journal of Open Humanities Data 8: 16. https://doi.org/10.5334/johd.78
   - Repository: https://github.com/j-hagedorn/trilogy, **pinned commit `d57c2cefd0b216c8ce5c251f618c3e931c732d0a`** (2024-05-27, “Merge pull request #54 … clean-motifs”). The default branch has moved since then (last push 2025-05-21); the pinned version is used throughout.
   - Archived release described in the paper: Zenodo 10.5281/zenodo.6575263 (v1.1, 2022-05-24; concept DOI 10.5281/zenodo.5835161). The pinned commit is **later** than this release.
   - Files used: `data/aft.csv` (corpus), `docs/data_dictionary.md`, `README.md`, `LICENSE.md`, and as references only `atu_df.csv`, `atu_seq.csv`, `atu_combos.csv` and `tmi.csv`. `fetch/fetch_ashliman.R` and the paper's `.Rmd` source were read as documentation and never executed.
2. **Underlying collection**: Ashliman, D. L. (1996–). *Folktexts: A library of folktales, folklore, fairy tales, and mythology.* University of Pittsburgh. https://sites.pitt.edu/~dash/folktexts.html. A single snapshot of the index page was saved for its attribution notice; the site was **not** crawled.
3. **Tale-type index**: Uther, H.-J. (2004). *The Types of International Folktales: A Classification and Bibliography* (FF Communications 284–286). Source of the ATU numbering and the chapter ranges used for colouring.
4. **Motif index** (reference table only): Thompson, S. (1955–58). *Motif-Index of Folk-Literature.* Indiana University Press, via the trilogy `tmi.csv`.
5. **Geography**: Natural Earth 1:50m Admin-0 countries and map subunits, v5.1.2 (public domain), used for label points and UN sub-regions; world-atlas 2.0.2 (Natural Earth 1:110m) for drawn maps. UN M49 standard: https://unstats.un.org/unsd/methodology/m49/

## Model

- `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` (Apache-2.0). https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

## Course

- DTU 02805 *Social Graphs and Interactions* (2026), Sune Lehmann: https://sunelehmann.com/socialgraphs2026-web/index.html, weeks 2–8 (content CC BY-SA 4.0). Section-level references are in METHOD_MAP.md.
- Course textbooks referenced by the course pages: Coscia, *The Atlas for the Aspiring Network Scientist*; Jurafsky & Martin, *Speech and Language Processing* (3rd ed. draft).

## Software

Python 3.11 (pandas, NumPy, SciPy, scikit-learn, NetworkX, sentence-transformers, PyTorch, ftfy, PyYAML, Matplotlib, Playwright for browser checks); Node.js 24 LTS with React 19, Vite 8, TypeScript 5.9, d3 7.9 and topojson-client. Exact versions are in `uv.lock` and `web/package-lock.json`, and the run metadata is in `outputs/metrics/run.json`.
