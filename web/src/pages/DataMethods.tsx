import { Fragment, useMemo, useState } from "react";
import { catalogueRows, useData } from "../data/load";
import type { CataloguePayload, MappingPayload, SummaryPayload } from "../data/types";
import { ErrorState, Loading, downloadText, toCsv } from "../components/ui";
import { fmt, int } from "../lib/format";
import type { Route } from "../lib/router";

const COURSE = "https://sunelehmann.com/socialgraphs2026-web/weeks/";
const METHODS: [string, string, string, string][] = [
  ["Document checks, tokenisation, stopwords", "Audit lengths and boilerplate; turn text into tokens", "week5.html#tokens", "Taught (week 5 §2, §4)"],
  ["TF–IDF and cosine similarity", "Lexical representation and similarity", "week6.html#tfidf", "Taught (week 6 §1)"],
  ["Removing names (sensitivity)", "Words capitalised in most uses treated as names", "week6.html#topics", "Taught rule (week 6 §3), applied as a sensitivity"],
  ["Sentence embeddings with chunking", "Semantic representation (all-MiniLM-L6-v2, 256-token limit)", "week7.html#corpus-atlas", "Taught (week 7 §1–2); token-based chunk sizing is a project refinement"],
  ["PCA projection", "2D drawing of embeddings (never used for similarity)", "week7.html#corpus-atlas", "Taught (week 7 §2)"],
  ["Passage retrieval", "Best-matching chunks between tales", "week7.html#semantic-search", "Taught (week 7 §6)"],
  ["Ten-nearest-neighbour check vs random", "Share of neighbours with the same label vs chance", "week6.html#tfidf", "Taught idea (weeks 5–7 explorables); applied to labels"],
  ["Weighted networks, global threshold", "Keep the strongest pairs as edges", "week4.html#backbones", "Taught (week 4 §7–8)"],
  ["Louvain, modularity, seed stability (NMI)", "Communities and their stability", "week4.html#louvain", "Taught (week 4 §3–4)"],
  ["Degree-preserving shuffle for Q", "Is modularity above what degrees alone give?", "week4.html#louvain", "Taught (week 2 §7, week 4 §4)"],
  ["NMI against labels", "How much communities know about recorded labels", "week4.html#louvain", "Taught (week 4 §4 'Ground truth revisited')"],
  ["Attribute assortativity + label shuffle", "Same-label edges beyond chance", "week3.html#mixing-patterns-do-the-important-stick-together", "Taught (week 3 §7 and Goodies)"],
  ["Permutation p-value (1 + k)/(1 + N)", "Reference distributions", "week2.html#shuffling-the-model-becomes-a-test", "Taught (week 2 §7 and Goodies)"],
  ["Great-circle distance (haversine)", "Distance between recorded points", "", "Supporting calculation, not course material"],
  ["Raw agreement for human labels", "Validation of similarity", "week8.html#question", "Taught practice (percentage agreement; week 7–8)"],
];
const GLOSSARY: [string, string][] = [
  ["Recorded tale", "One identifiable textual version with its source; one node in the network after identical copies are merged."],
  ["Tale type (ATU)", "A family of related stories in the Aarne–Thompson–Uther index (e.g. ATU 510A Cinderella). Here assigned by the page of Ashliman's site a tale appears on."],
  ["Motif", "A recurring narrative element (an animal helper, a forbidden room). Not annotated per tale in this corpus."],
  ["Provenance", "The place, community, author or collection recorded by the source. Not the place of invention."],
  ["Place label", "Country, constituent nation (England/Scotland/Wales), community or region used as the fine geographical label."],
  ["Broad region", "UN M49 sub-region of the place (e.g. Northern Europe); a coarse geographical label."],
  ["Textual similarity", "Cosine similarity under one representation; not a percentage of plot agreement or proof of shared ancestry."],
  ["Density", "Share of all tale pairs kept as edges (5%, 10%, 15%)."],
  ["Community", "A group found by Louvain modularity optimisation, without using any labels."],
  ["NMI", "Normalised mutual information between two labelings: 1 identical, 0 independent."],
  ["Label shuffle", "Randomly permuting a label across tales (category sizes kept) while the graph and communities stay fixed."],
  ["Lift", "Neighbour same-label rate divided by the rate expected from label frequencies."],
  ["Display displacement", "Spreading tales that share one map point on a small spiral, purely for drawing."],
];

export function DataMethods({ route, navigate }: { route: Route; navigate: (p: string, params?: Record<string, string | null | undefined>, replace?: boolean) => void }) {
  const summary = useData<SummaryPayload>("summary.json");
  const cat = useData<CataloguePayload>("catalogue.json");
  const map = useData<MappingPayload>("mapping.json");
  const [q, setQ] = useState(route.params.q ?? "");
  const [kind, setKind] = useState("");
  const [mq, setMq] = useState("");
  const rows = useMemo(() => (cat.data ? catalogueRows(cat.data) : []), [cat.data]);
  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    return rows.filter((r) => (!s || r.title.toLowerCase().includes(s) || (r.atu ?? "").toLowerCase() === s || (r.atu_name ?? "").toLowerCase().includes(s) || (r.place ?? "unknown").toLowerCase().includes(s) || r.provenance.toLowerCase().includes(s) || r.source_key.includes(s)));
  }, [rows, q]);
  const mapRows = useMemo(() => {
    if (!map.data) return [];
    const f = map.data.fields;
    const ix = (k: string) => f.indexOf(k);
    const s = mq.trim().toLowerCase();
    return map.data.rows.filter((r) => (!kind || r[ix("entity_kind")] === kind) && (!s || r.join(" ").toLowerCase().includes(s)));
  }, [map.data, kind, mq]);
  if (summary.error) return <div className="page"><ErrorState message={summary.error} /></div>;
  if (!summary.data) return <div className="page"><Loading /></div>;
  const s = summary.data;
  const c = s.counts;
  const mf = map.data?.fields ?? [];
  const col = (r: string[], k: string) => r[mf.indexOf(k)];
  return (
    <div className="page">
      <h1 style={{ fontSize: "clamp(2rem, 4vw, 3rem)" }}>Data &amp; Methods</h1>
      <nav className="row sans small" aria-label="On this page" style={{ marginBottom: 20 }}>
        {[["pipeline", "Pipeline"], ["cohorts", "Cohorts"], ["cleaning", "Cleaning"], ["mapping", "Provenance mapping"], ["catalogue", "Catalogue"], ["representations", "Representations"], ["course", "Course grounding"], ["glossary", "Glossary"]].map(([id, l]) => (
          <a key={id} href={`#/data`} onClick={(e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView(); }}>{l}</a>
        ))}
      </nav>

      <section id="pipeline" className="prose-wide">
        <h2>Pipeline</h2>
        <ol>
          <li><strong>Fetch</strong> pinned files (trilogy commit d57c2ce, Natural Earth v5.1.2), recording URL, SHA-256, size and licence in a manifest.</li>
          <li><strong>Audit</strong> the raw file: all diagnostics quoted in the brief reproduce exactly ({Object.values(s.audit).filter((x) => x.match).length}/{Object.keys(s.audit).length}).</li>
          <li><strong>Clean</strong> with documented rules and a reviewed decisions file; every removed span is logged.</li>
          <li><strong>Map provenance</strong> with a reviewable table; <strong>build cohorts</strong> with explicit exclusion reasons.</li>
          <li><strong>Represent</strong> each narrative with TF–IDF ({int(s.lexical.vocabulary_size)} terms) and {s.semantic.model} ({s.semantic.dimension} dimensions, revision {s.semantic.revision.slice(0, 8)}).</li>
          <li><strong>Build graphs</strong> at 5/10/15% density, run weighted Louvain (seeds {s.config.seeds.join(", ")}), and compare with labels using {int(s.config.permutations)} label shuffles.</li>
          <li><strong>Export</strong> run <span className="mono">{s.run_id}</span> to this site. Every payload carries this ID.</li>
        </ol>
        <p className="small sans muted">Reproduce with <span className="mono">uv run python -m analysis all</span> and <span className="mono">npm run build</span> (see README.md). Created {s.run.created}; Python packages: {Object.entries(s.run.versions).map(([k, v]) => `${k} ${v}`).join(", ")}.</p>
      </section>

      <section id="cohorts">
        <h2>Cohorts</h2>
        <div className="table-wrap prose-wide">
          <table className="data">
            <thead><tr><th>Cohort</th><th>Definition</th><th className="num">Size</th></tr></thead>
            <tbody>
              <tr><td>Raw records</td><td>Rows of the pinned aft.csv</td><td className="num">{int(c.raw_records)}</td></tr>
              <tr><td>Text cohort</td><td>Distinct usable narratives ({c.records_excluded_non_narrative} non-narrative records excluded, {c.exact_duplicate_records_merged} identical copies merged)</td><td className="num">{int(c.text_cohort)}</td></tr>
              <tr><td>ATU cohort</td><td>One unambiguous ATU label ({c.atu_conflicts} identical texts with conflicting labels excluded)</td><td className="num">{int(c.atu_cohort)}</td></tr>
              <tr><td>Joint cohort</td><td>ATU cohort with a defensible place and UN M49 region (mapping confidence high/medium)</td><td className="num">{int(c.joint_cohort)}</td></tr>
              <tr><td>Distance cohort</td><td>Joint cohort with documented coordinates</td><td className="num">{int(c.distance_cohort)}</td></tr>
              <tr><td>Sensitivity subsets</td><td>Near-duplicates reduced ({c.near_duplicate_pairs} flagged pairs), suspected fragments removed ({c.suspected_fragments_text_cohort} flagged), region-balanced (≤ {s.config.balanced_cap} per region)</td><td className="num">see Story ch. 9</td></tr>
            </tbody>
          </table>
        </div>
        <p className="sans small"><a href="./data/inclusion_ledger.csv" download>Download the inclusion ledger (one row per raw record, with cohort flags and reasons)</a></p>
      </section>

      <section id="cleaning" className="prose-wide">
        <h2>Cleaning</h2>
        <p>Only identifiable non-narrative material was removed: navigation, source citations, editorial notes, inline footnote markers, and classification labels. The labels were removed so they could not leak into the features. Mojibake from a latin-1 conversion in the original scraper was repaired in {int(s.cleaning.mojibake_repaired_texts)} texts. In total {int(s.cleaning.words_removed)} words were removed from {int(s.cleaning.records_with_removals)} records.</p>
        <div className="grid-2">
          <div className="table-wrap"><table className="data"><thead><tr><th>Rule</th><th className="num">Removals</th></tr></thead><tbody>
            {Object.entries(s.cleaning.removals_by_rule).map(([k, v]) => <tr key={k}><td>{k.replace("tail_cut:", "trailing material at: ")}</td><td className="num">{v}</td></tr>)}
          </tbody></table></div>
          <div className="table-wrap"><table className="data"><thead><tr><th>Excluded record</th><th>Reason</th></tr></thead><tbody>
            {s.cleaning.excluded_non_narrative.map((e) => <tr key={e.record_id}><td className="mono">{e.record_id}</td><td>{e.excluded_reason}</td></tr>)}
          </tbody></table></div>
        </div>
        <p className="small sans muted">Flags kept for inspection (not exclusions): {Object.entries(s.cleaning.flags).map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`).join(" · ")}.</p>
      </section>

      <section id="mapping">
        <h2>Provenance mapping</h2>
        <p className="prose-wide">Each distinct raw provenance string ({map.data?.rows.length ?? "…"}) has one reviewable row: a normalised label, its kind (country, region, community, author, collection, mixed, unknown), a UN M49 broad region, a representative point where justified, confidence, evidence and rationale. Authors and collections are never turned into story-origin places. Communities keep their own labels. Cross-border strings get no place label.</p>
        <div className="row" style={{ marginBottom: 8 }}>
          <input type="search" placeholder="search the mapping…" value={mq} onChange={(e) => setMq(e.target.value)} aria-label="Search mapping" />
          <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Filter by kind">
            <option value="">all kinds</option>{["country", "region", "community", "mixed", "author", "collection", "unknown"].map((k) => <option key={k}>{k}</option>)}
          </select>
          <span className="small sans muted">{mapRows.length} rows</span>
          <a className="btn small" href="./data/provenance_map.csv" download>Download CSV</a>
        </div>
        {!map.data ? <Loading what="the mapping" /> : (
          <div className="table-wrap" style={{ maxHeight: 440 }}>
            <table className="data">
              <thead><tr><th>Raw string</th><th className="num">Records</th><th>Kind</th><th>Place label</th><th>Region</th><th>Confidence</th><th>Point</th><th>Rationale</th></tr></thead>
              <tbody>
                {mapRows.slice(0, 400).map((r) => (
                  <tr key={col(r, "raw_provenance")}>
                    <td>{col(r, "raw_provenance").slice(0, 70)}{col(r, "raw_provenance").length > 70 ? "…" : ""}</td>
                    <td className="num">{col(r, "n_records")}</td><td>{col(r, "entity_kind")}</td>
                    <td>{col(r, "place_label") || <span className="muted">—</span>}</td><td>{col(r, "broad_region") || <span className="muted">—</span>}</td>
                    <td><span className={`chip ${col(r, "confidence") === "high" ? "ok" : col(r, "confidence") === "none" ? "" : "warn"}`}>{col(r, "confidence")}</span></td>
                    <td className="small">{col(r, "latitude") ? `${fmt(Number(col(r, "latitude")), 1)}, ${fmt(Number(col(r, "longitude")), 1)}` : "—"}</td>
                    <td className="small">{col(r, "rationale")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section id="catalogue">
        <h2>Catalogue and source browser</h2>
        <div className="row" style={{ marginBottom: 8 }}>
          <input type="search" placeholder="title, ATU number, place, source…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search catalogue" style={{ minWidth: 280 }} />
          <span className="small sans muted">{filtered.length} of {rows.length} usable narratives · geography shown as “unknown” when not defensible</span>
          <button className="btn small" onClick={() => downloadText("catalogue.csv", toCsv([["id", "title", "atu", "atu_name", "place", "region", "provenance", "source_key", "words", "in_joint"], ...filtered.map((r) => [r.id, r.title, r.atu, r.atu_name, r.place, r.region, r.provenance, r.source_key, r.n_words, r.in_joint])]))}>Download CSV</button>
        </div>
        {!cat.data ? <Loading what="the catalogue" /> : (
          <div className="table-wrap" style={{ maxHeight: 480 }}>
            <table className="data">
              <thead><tr><th>Title</th><th>ATU</th><th>Recorded provenance</th><th>Place</th><th>Region</th><th>Source group</th><th className="num">Words</th><th>Cohort</th></tr></thead>
              <tbody>
                {filtered.slice(0, 300).map((r) => (
                  <tr key={r.id}>
                    <td><a href={`#/explore?tale=${r.id}&cohort=${r.in_joint ? "joint" : "text"}`}>{r.title}</a>{r.fragment && <span className="chip warn" style={{ marginLeft: 4 }}>fragment?</span>}</td>
                    <td title={r.atu_name ?? ""}>{r.atu ?? <span className="chip warn">conflict</span>}</td>
                    <td className="small">{r.provenance}</td>
                    <td>{r.place ?? <span className="muted">unknown</span>}</td><td className="small">{r.region ?? "—"}</td>
                    <td className="small">{r.source_key}</td><td className="num">{int(r.n_words)}</td>
                    <td className="small">{r.in_joint ? "joint" : r.in_atu ? "ATU only" : "text only"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {filtered.length > 300 && <p className="small sans muted">Showing the first 300 matches; refine the search or download the CSV.</p>}
        {cat.data && <p className="small sans">Excluded non-narrative records are listed under Cleaning. <button className="btn small ghost" onClick={() => navigate("/explore", { cohort: "text" })}>Browse all usable tales in Explore →</button></p>}
      </section>

      <section id="representations" className="prose-wide">
        <h2>Representations</h2>
        <div className="grid-2">
          <div>
            <h3>TF–IDF (lexical)</h3>
            <p className="sans small">One space fitted on the {int(c.text_cohort)} narratives: NFKC, lowercase, negated contractions expanded (“n't” → “not”), letters-only tokens, scikit-learn stopwords minus 13 negation words, min_df 2, sublinear TF, L2 norm. Vocabulary {int(s.lexical.vocabulary_size)} terms ({int(s.lexical.vocabulary_size_names_masked)} with names masked). TF–IDF emphasises words distinctive in this corpus; it does not measure plot structure.</p>
          </div>
          <div>
            <h3>Embeddings (semantic)</h3>
            <p className="sans small">{s.semantic.model}, revision <span className="mono">{s.semantic.revision}</span>, {s.semantic.dimension} dimensions, limit 256 tokens including special tokens. Tales are cut into non-overlapping chunks of ≤ {s.semantic.settings.c200.max_tokens} tokens ({int(s.semantic.settings.c200.chunks)} chunks; max observed {s.semantic.settings.c200.max_observed_tokens}). An alternative uses ≤ {s.semantic.settings.c128.max_tokens} tokens. Unit chunk vectors are averaged and renormalised; this loses sequence and can blur several topics.</p>
          </div>
        </div>
      </section>

      <section id="course" className="prose-wide">
        <h2>Course grounding</h2>
        <p className="small sans">Full table with assumptions, implementation and checks: METHOD_MAP.md in the repository.</p>
        <div className="table-wrap"><table className="data">
          <thead><tr><th>Method</th><th>Purpose here</th><th>Course status</th></tr></thead>
          <tbody>{METHODS.map(([m, p, url, st]) => <tr key={m}><td>{url ? <a href={COURSE + url} target="_blank" rel="noreferrer">{m}</a> : m}</td><td>{p}</td><td className="small">{st}</td></tr>)}</tbody>
        </table></div>
      </section>

      <section id="glossary" className="prose-wide">
        <h2>Glossary</h2>
        <dl className="sans" style={{ display: "grid", gridTemplateColumns: "190px 1fr", gap: "8px 18px", fontSize: 14.5 }}>
          {GLOSSARY.map(([t, d]) => <Fragment key={t}><dt style={{ fontWeight: 650 }}>{t}</dt><dd style={{ margin: 0 }}>{d}</dd></Fragment>)}
        </dl>
      </section>
    </div>
  );
}
