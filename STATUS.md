# Status (project note for resuming work)

**Run:** see `outputs/metrics/run.json` (every web payload carries the same `run_id`).
**Last updated:** 2026-10-30.

## Done

- **Data:** pinned fetch with manifest; executable audit (all brief diagnostics reproduce); rule-based cleaning with 40 reviewed decisions; reviewable provenance mapping (406 strings); cohorts with ledger; near-duplicate and fragment flags.
- **Representations:** TF–IDF (negation kept; the YAML `no` defect is fixed and logged) and MiniLM chunk embeddings (no truncation; cached).
- **Networks and evaluation:** graphs at 5/10/15% for both representations; Louvain over three seeds; label shuffles (1,000) for NMI and assortativity; top-10 neighbour lifts with a same-source exclusion; an isolate-free check; degree-preserving modularity null; distance analysis with whole-location shuffles; all pre-declared sensitivity variants.
- **Validation:** blind stratified sample of 84 pairs and the annotation tool. Status: **pending** (no human labels).
- **Website** (React + TypeScript + Vite): Story (10 chapters, the 8 v1.1 scenes), Explore, Data & Methods, Validation, Sources; URL state, copy link, reset, CSV/PNG downloads; reduced motion; keyboard; mobile list view.
- **Tests:** `uv run pytest` covers metric equivalence and pipeline outputs. Browser journeys (desktop, mobile, keyboard + reduced motion, mobile + reduced motion) are in `tests/browser/journey.py`.

## Findings at a glance

Run `ouaw-20261030-ed9feb8a`. Reprint the numbers with `uv run python scripts/summarise_run.py`. Every statement is about this corpus (one editor's English selection) and these representations, not about world folklore.

- **Cohorts.** 1,518 raw records → 1,498 usable narratives → 1,493 with a non-conflicting ATU type → 1,133 in the joint cohort (type plus a mapped place: 164 types, 89 places, 13 regions) → 1,084 with coordinates for the distance analysis.
- **Main setting** (joint cohort, 10% density, Louvain seed 42). Each value is compared with 1,000 label shuffles on the fixed graph, and every label system beats all 1,000.

| Measure | Representation | ATU type | Place | Region |
| --- | --- | --- | --- | --- |
| NMI excess over shuffles | TF–IDF | 0.191 | 0.094 | 0.088 |
| NMI excess over shuffles | Embeddings | 0.163 | 0.024 | 0.034 |
| Assortativity r | TF–IDF | 0.028 | 0.030 | 0.062 |
| Assortativity r | Embeddings | 0.020 | 0.014 | 0.036 |
| Top-10 neighbour lift | TF–IDF | 31.3× | 3.8× | 2.2× |
| Top-10 neighbour lift | Embeddings | 24.0× | 2.6× | 1.9× |

- **Answer under the pre-declared rule.** ATU type has the largest NMI excess and the largest neighbour lift in all 45 robustness settings (densities × seeds, representation and cohort variants). Assortativity, which weighs every edge equally, is highest for broad region in all 45. The all-three-measures verdict is therefore *type over place* in 30 of 45 settings and mixed in the other 15 (place has the higher r), and *mixed* for type versus region in all 45.
- **Source dependence.** Excluding neighbours from the same bibliographic source barely changes the lifts (TF–IDF: type 31.0×, place 3.4×, region 2.1×).
- **Community structure.** Modularity is far above degree-preserving shuffles for all six main graphs (TF–IDF 10%: Q 0.138 vs 0.050 ± 0.001; embeddings 10%: 0.187 vs 0.044 ± 0.001). Lexical partitions are only moderately stable across seeds (seed-pair NMI 0.48–0.62 at 10%); semantic partitions are more stable (0.86–0.92).
- **Distance.** Similarity falls weakly with great-circle distance between recorded points (Spearman ρ −0.063 TF–IDF, −0.110 embeddings), outside the range of 1,000 whole-location shuffles (about −0.06 to 0.07). This is a weak association, not evidence of transmission.
- **Validation.** 84 blind items (24 development, 60 final) are ready. No human annotations exist, so no accuracy or agreement figure is reported.

## Verification (2026-10-30)

- **Reproducibility.** `python -m analysis all` was rerun from the pinned raw file. The cleaned narratives and TF–IDF matrix were byte-identical, every embedding came from the content-addressed cache, and all graph, agreement, neighbour, modularity-null and cohort outputs were identical to the previous run apart from the run ID.
- **Tests.** `uv run pytest` passes (unit equivalence tests and checks on the produced outputs).
- **Browser.** The uninterrupted journey in `tests/browser/journey.py` passes all 14 steps on the production build in four variants: desktop, 390 px, keyboard-only with reduced motion, and 390 px with reduced motion. The consoles are clean, and the NMI shown in the browser equals the pipeline value.

## Open items / decisions for the authors

1. Human review of `data/mappings/provenance_map.csv` (every row says `agent-drafted …; human review pending`) and of `data/mappings/text_review.csv`.
2. Collect human annotations on the Validation page (two people, overlapping items), then run `uv run python -m analysis validation export`.
3. Publication: decide on full-text display (`export.include_full_texts`) and resolve the licence questions in LICENSE_NOTES.md before any public deployment.
4. Choose a licence for the code.
5. Optional extensions not built: a type-level motif reference (the ATU type descriptions have unclear copyright), re-fetching truncated tale openings, and Glottolog points for communities without coordinates.

## How to resume

```bash
uv sync && uv run python -m analysis all   # unchanged stages are skipped
uv run pytest
cd web && npm ci && npm run build && npm run preview   # http://localhost:4173/
# with the preview running, from the project root (headless Edge via Playwright):
uv run python tests/browser/journey.py http://localhost:4173/ outputs/browser/journey [--mobile] [--keyboard] [--reduced]
```
