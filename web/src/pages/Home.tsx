import type { ReactNode } from "react";
import { useData } from "../data/load";
import { ErrorState, Loading } from "../components/ui";
import { int } from "../lib/format";

// The overview of reIMAGINE. Every number on this page is read from paper.json, which the paper pipeline
// (`python -m ouaw.run --stage site`) builds from the files in results/. Only the prose is written here.

type Rep = "tfidf" | "embedding" | "tfidf_nouns_masked";
interface HeadRow {
  variant: Rep; tradition: string; n_parables: number; n_baseline: number; parable_median: number; baseline_median: number;
  diff: number; diff_ci_low: number; diff_ci_high: number; diff_p_upper: number; closer_than_baseline: boolean;
  inside_share: number; inside_null_mean: number; inside_p_upper: number; jsd_bits: number; jsd_null_mean: number; jsd_p_upper: number;
  profile_differs: boolean; top_excess_community: string; top_excess_community_words: string; top_excess: number; top_excess_p: number;
  top_excess_significant_bonferroni: boolean; top_source_collection: string | null; top_source_collection_share: number | null;
}
interface TypeRow { tradition: string; kind: string; rank: number; atu_id: string; atu_name: string; share: number; n_texts: number }
interface CalRow { representation: string; queries: number; hits: number; recall_at_k: number; ci_low: number; ci_high: number; chance_at_k: number;
  vote_accuracy: number; vote_hits: number; vote_chance: number; vote_chance_high: number }
interface T1Row { check: string; variant: string; holds: "yes" | "partly" | "no" | "n/a"; agreement: string; key_number: string }
interface CommRow { community: string; size: number; top_words: string; lda_topic_words: string; dominant_atu_types: string; dominant_regions: string;
  dominant_source_collections: string }
interface LabelRow { label: string; null: string; measure: string; observed: number; null_mean: number; null_q025: number; null_q975: number; p_upper: number }
interface Caption { title: string; text: string }
interface PaperPayload {
  built: string; commit: string; primary: Rep; traditions: string[];
  settings: { density: number; permutations: number; closenessK: number; attachK: number; labelShuffles: number; handLabelPairs: number };
  corpus: { folktales: number; calibration: number; typed: number; types: number; withRegion: number; regions: number; both: number;
    europeShare: number; collectionKnown: number; collections: number; translatorKnown: number };
  sources: { tradition: string; kind: string; n: number; tokens_median: number; sources: string }[];
  headline: HeadRow[]; types: TypeRow[];
  length: { control: { rep: string; tradition: string; diff_median: number; diff_ci_low: number; diff_ci_high: number; share_above_own_excerpts: number }[];
    matching: { tradition: string; mann_whitney_p: number; matched: boolean }[];
    regression: { rep: string; estimate: number; p: number; order_raw: string; order_at_equal_length: string; kendall_tau: number }[] };
  drivers: { tradition: string; top_driver_terms: string; noun_share_of_cosine_median: number }[];
  calibration: CalRow[]; exclusion: Record<string, number>; hand: { status: string; kappa: number | null };
  table1: T1Row[]; communities: CommRow[];
  map: { graph: { m: number; similarity_threshold: number; communities_major: number; modularity: number; modularity_null_mean: number;
      modularity_z: number; seed_nmi_min: number; seed_nmi_max: number };
    labels: LabelRow[]; backbone: { filtered: string; alpha: number; edges_kept: number; nodes_with_an_edge: number; drawn: boolean }[];
    archetypes: { title: string; atu_id: string; atu_name: string; z: number }[] };
  figures: Record<string, string>; captions: Record<string, Caption>;
}

const REP_NAME: Record<string, string> = { tfidf: "TF–IDF", embedding: "embeddings", tfidf_nouns_masked: "TF–IDF with nouns masked" };
const asset = (p: string) => `${import.meta.env.BASE_URL}data/${p}`;
const f3 = (v: number) => v.toFixed(3);
const f2 = (v: number) => v.toFixed(2);
const signed = (v: number, d = 3) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(d)}`;
const pts = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(Math.round(v * 100))}`;
const pc = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${Math.round(v * 100)}%`);
const pval = (p: number) => (p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(3)}`);
const list = (xs: string[]) => (xs.length === 0 ? "none" : xs.length === 1 ? xs[0] : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`);
const shortType = (atu: string, name: string) => `${atu} ${name.split(" (previously")[0].split(" [")[0]}`;

function Flourish() { return <div className="flourish" aria-hidden>❦</div>; }

function Figure({ data, file, label, alt }: { data: PaperPayload; file: string; label: string; alt: string }) {
  const src = data.figures[file];
  const cap = data.captions[label];
  if (!src) return <p className="small sans muted">{label} has not been generated yet.</p>;
  return (
    <figure className="storyframe">
      <a href={asset(src)} target="_blank" rel="noopener noreferrer" title="Open the full-size figure"><img src={asset(src)} alt={alt} loading="lazy" /></a>
      {cap && <figcaption><strong>{label}. {cap.title}.</strong> {cap.text}</figcaption>}
    </figure>
  );
}

function Section({ id, num, title, children }: { id: string; num: string; title: string; children: ReactNode }) {
  return (
    <section id={id} style={{ scrollMarginTop: "calc(var(--header-h) + 12px)" }}>
      <div className="section-head"><span className="num">{num}</span><h2>{title}</h2></div>
      {children}
    </section>
  );
}

export function Home() {
  const d = useData<PaperPayload>("paper.json");
  if (d.error) return <div className="page"><ErrorState message={d.error} /></div>;
  if (!d.data) return <div className="page"><Loading what="the overview" /></div>;
  const data = d.data;
  const prim = data.primary;
  const head = data.headline.filter((r) => r.variant === prim).sort((a, b) => b.diff - a.diff);
  const masked = new Map(data.headline.filter((r) => r.variant === "tfidf_nouns_masked").map((r) => [r.tradition, r]));
  const other = data.headline.filter((r) => r.variant !== prim && r.variant !== "tfidf_nouns_masked");
  const otherRep = other[0]?.variant;
  const closer = head.filter((r) => r.closer_than_baseline).map((r) => r.tradition);
  const notCloser = head.filter((r) => !r.closer_than_baseline).map((r) => r.tradition);
  const closerOther = other.filter((r) => r.closer_than_baseline).map((r) => r.tradition);
  const closerAll = closer.filter((t) => closerOther.includes(t) && masked.get(t)?.closer_than_baseline);
  const topType = (t: string, kind: string) => data.types.find((x) => x.tradition === t && x.kind === kind && x.rank === 1);
  const excerpts = data.length.control.filter((x) => x.rep === prim);
  const exMin = Math.min(...excerpts.map((x) => x.diff_median)), exMax = Math.max(...excerpts.map((x) => x.diff_median));
  const cal = new Map(data.calibration.map((c) => [c.representation, c]));
  const c0 = cal.get(prim);
  const label = (lab: string, nul: string, measure = "nmi") => data.map.labels.find((x) => x.label === lab && x.null === nul && x.measure === measure);
  const typePlain = label("atu_type", "label shuffle"), typeWithin = label("atu_type", "within-collection shuffle");
  const regionPlain = label("region", "label shuffle"), regionWithin = label("region", "within-collection shuffle");
  const collPlain = label("source_collection", "label shuffle");
  const drawn = data.map.backbone.find((b) => b.drawn);
  const g = data.map.graph;
  const parN = data.sources.filter((s) => s.kind === "parable");
  const baseN = data.sources.filter((s) => s.kind === "baseline");
  const nPar = parN.reduce((a, s) => a + s.n, 0), nBase = baseN.reduce((a, s) => a + s.n, 0);
  const reg = data.length.regression.find((x) => x.rep === prim);
  const s = data.settings;
  const excess = (r?: LabelRow) => (r ? r.observed - r.null_mean : 0);
  const typeOverRegion = excess(typePlain) > excess(regionPlain);
  // share of region's excess over plain shuffles that vanishes when every tale's source collection is held fixed
  const regionToCollection = regionPlain && regionWithin && excess(regionPlain) > 0
    ? (regionWithin.null_mean - regionPlain.null_mean) / excess(regionPlain) : null;
  const allBelowExcerpts = excerpts.length > 0 && exMax < 0;

  return (
    <>
      <header className="tale-hero">
        <div className="kicker-sc">reIMAGINE · a study of parables and folktales</div>
        <h1>Where do parables land in the world of folktales?</h1>
        <div className="question-card">
          <div className="tag">The question</div>
          <p>Do parables from different religious traditions sit inside folktale communities more than non-story text from the same translations does, and which folktale communities and tale types do they land in?</p>
        </div>
        <div className="motivation">
          <span className="ribbon">Motivation · not tested</span>
          <div className="tag">Why we ask</div>
          <p className="sans small" style={{ margin: 0 }}>People often say that parables are “just folktales with a moral attached”. We cannot test that claim: text similarity sees shared words and content, never the moral, and no lesson was coded. It is where the question comes from, not a result.</p>
        </div>
        <div className="tiles" style={{ maxWidth: 960 }}>
          <div className="tile"><div className="v">{int(data.corpus.folktales)}</div><div className="l">folktale versions on the map</div></div>
          <div className="tile"><div className="v">{int(data.corpus.types)}</div><div className="l">ATU tale types</div></div>
          <div className="tile"><div className="v">{int(nPar)}</div><div className="l">parables from {parN.length} traditions</div></div>
          <div className="tile"><div className="v">{int(nBase)}</div><div className="l">non-story passages from the same translations</div></div>
          <div className="tile"><div className="v">{int(data.corpus.calibration)}</div><div className="l">religious retellings of known type, held out to test the method</div></div>
        </div>
        <p className="lede dropcap">Once upon a time, every tradition told stories to teach. We place {int(nPar)} parables on a map of {int(data.corpus.folktales)} folktales built from text similarity, and compare each tradition with non-story text cut from the same translation. That baseline matters: a parable can look folktale-like only because its translator wrote like a teller of tales.</p>
        <nav className="row sans" aria-label="Sections" style={{ marginTop: 6 }}>
          {[["data", "The data"], ["map", "The folklore map"], ["headline", "The headline"], ["validity", "Validity and robustness"], ["limits", "What we can conclude"]].map(([id, t]) => (
            <a key={id} className="btn small ghost" href={`#/`} onClick={(e) => { e.preventDefault(); document.getElementById(id)?.scrollIntoView({ behavior: document.documentElement.dataset.motion === "off" ? "auto" : "smooth" }); }}>{t}</a>
          ))}
        </nav>
      </header>

      <div className="page" style={{ paddingTop: 0 }}>
        <Flourish />
        <Section id="data" num="I" title="The data">
          <div className="prose-wide">
            <p>The map is {int(data.corpus.folktales)} English folktale versions from D. L. Ashliman's Folktexts (Annotated Folktales, 2022). {int(data.corpus.typed)} carry one ATU tale type ({int(data.corpus.types)} types), {int(data.corpus.withRegion)} a recorded region ({data.corpus.regions} regions), and {int(data.corpus.collectionKnown)} a source collection ({int(data.corpus.collections)} collections). The {int(data.corpus.calibration)} versions that come from religious collections are kept off the map and used to test whether the method finds a tale's own type.</p>
            <p>For every tradition, the parables and a length-matched baseline of non-story text come from the same public-domain translation:</p>
          </div>
          <div className="table-wrap" style={{ maxWidth: 980 }}>
            <table className="data">
              <thead><tr><th>Tradition</th><th className="num">Parables</th><th>Parables from</th><th className="num">Baseline passages</th><th>Baseline from</th></tr></thead>
              <tbody>{data.traditions.map((t) => {
                const p = parN.find((s) => s.tradition === t), b = baseN.find((s) => s.tradition === t);
                return <tr key={t}><td>{t}</td><td className="num">{p?.n ?? "–"}</td><td>{p?.sources}</td><td className="num">{b?.n ?? "–"}</td><td>{b?.sources}</td></tr>;
              })}</tbody>
            </table>
          </div>
        </Section>

        <Flourish />
        <Section id="map" num="II" title="The folklore map">
          <div className="prose-wide">
            <p>Each folktale is linked to the ones it resembles most (the top {Math.round(s.density * 100)}% of all pairs by {REP_NAME[prim]} cosine, {int(g.m)} links). Louvain finds {g.communities_major} communities; modularity {f3(g.modularity)} against {f3(g.modularity_null_mean)} in degree-preserving shuffles. The communities follow tale type {typeOverRegion ? "more than" : "no more than"} region: NMI with type {typePlain ? f3(typePlain.observed) : "–"} (shuffles {typePlain ? f3(typePlain.null_mean) : "–"}), with region {regionPlain ? f3(regionPlain.observed) : "–"} (shuffles {regionPlain ? f3(regionPlain.null_mean) : "–"}).</p>
            <p><strong>Is it just the collection?</strong> Ashliman's tales come from many books and translators, and a book's style could pass for “type” or “region”. Holding every tale's source collection fixed, tale type {typeWithin && typeWithin.p_upper < 0.05 ? "still beats" : "no longer beats"} the shuffles ({typeWithin ? `${f3(typeWithin.observed)} against ${f3(typeWithin.null_mean)}, ${pval(typeWithin.p_upper)}` : "–"}). For region, {regionToCollection !== null ? <>{pc(regionToCollection)} of its excess over the plain shuffles disappears</> : "the excess"} when collections are held fixed ({regionWithin ? `${f3(regionWithin.null_mean)} expected, ${pval(regionWithin.p_upper)}` : "–"}). Source collection itself: NMI {collPlain ? `${f3(collPlain.observed)} against ${f3(collPlain.null_mean)}` : "–"}.</p>
          </div>
          <Figure data={data} file="fig1_map" label="Figure 1" alt="Network map of the folktales coloured by community, with the agreement of the communities with tale type, region and source collection" />
          <p className="sans small muted">{drawn ? `The drawing uses the disparity backbone of the complete similarity graph (α = ${drawn.alpha}, ${int(drawn.edges_kept)} edges); communities are computed on the full network, never on the backbone.` : ""} The interactive version of this map, chapter by chapter, is on the <a href="#/story">Folklore map</a> page.</p>
          <h3 style={{ marginTop: 24 }}>What the communities are</h3>
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>Community</th><th className="num">Tales</th><th>Most distinctive words</th><th>Dominant tale types</th><th>Regions</th><th>Source collections</th></tr></thead>
              <tbody>{data.communities.map((c) => (
                <tr key={c.community}><td><strong>{c.community}</strong></td><td className="num">{int(c.size)}</td><td>{c.top_words}</td><td>{c.dominant_atu_types}</td><td>{c.dominant_regions}</td><td>{c.dominant_source_collections}</td></tr>
              ))}</tbody>
            </table>
          </div>
          {data.map.archetypes.length > 0 && <p className="sans small" style={{ marginTop: 12 }}><strong>The most “archetypal” tales</strong>, more central by PageRank than their number of links predicts: {data.map.archetypes.map((a) => `“${a.title}” (ATU ${a.atu_id}, z = ${a.z.toFixed(1)})`).join("; ")}.</p>}
        </Section>

        <Flourish />
        <Section id="headline" num="III" title="The headline: where parables land">
          <div className="prose-wide">
            <p className="dropcap">Against non-story text from their own translation, parables are closer to folktales for <strong>{list(closer)}</strong>; not for {list(notCloser)} ({REP_NAME[prim]}; the parable/baseline label shuffled {int(s.permutations)} times within each tradition).{closerAll.length > 0 && <> Only {list(closerAll)} {closerAll.length === 1 ? "stays" : "stay"} closer with embeddings and with nouns masked as well.</>} {allBelowExcerpts ? <>And every tradition's parables remain less folktale-like than folktale excerpts of the same length ({signed(exMin)} to {signed(exMax)}): they sit at the edge of folklore.</> : <>Against folktale excerpts of the same length the differences run from {signed(exMin)} to {signed(exMax)}.</>}</p>
          </div>
          <Figure data={data} file="fig2_headline" label="Figure 2" alt="For each tradition, the share of links to each folktale community compared with the baseline, and the folk-closeness differences" />
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>Tradition</th><th className="num">Parables minus baseline [95% interval]</th><th className="num">Permutation</th><th>Closer?</th><th>Leans toward, against the baseline</th><th>Most voted tale type</th><th className="num">Above the baseline's 95th percentile</th></tr></thead>
              <tbody>{head.map((r) => {
                const tt = topType(r.tradition, "parable");
                return (
                  <tr key={r.tradition}>
                    <td><strong>{r.tradition}</strong><div className="muted small">{r.n_parables} parables, {r.n_baseline} baseline</div></td>
                    <td className="num">{signed(r.diff)} [{signed(r.diff_ci_low)}, {signed(r.diff_ci_high)}]</td>
                    <td className="num">{pval(r.diff_p_upper)}</td>
                    <td><span className={`chip ${r.closer_than_baseline ? "yes" : "no"}`}>{r.closer_than_baseline ? "closer" : "not closer"}</span></td>
                    <td>{r.profile_differs ? <>{r.top_excess_community} ({r.top_excess_community_words.split(" ").join(", ")}) {pts(r.top_excess)} points</> : <span className="muted">same profile as the baseline ({pval(r.jsd_p_upper)})</span>}</td>
                    <td>{tt ? <>{shortType(tt.atu_id, tt.atu_name)} <span className="muted">({pc(tt.share)})</span></> : "–"}</td>
                    <td className="num">{pc(r.inside_share)} <span className="muted">(shuffles {pc(r.inside_null_mean)})</span></td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
          <h3 style={{ marginTop: 26 }}>Shared cast or shared story?</h3>
          <p className="prose-wide">Text similarity rewards shared nouns: animals, kings, farmers. For each parable's closest folktale we list the words that carry the match, and we rerun the headline with every noun and proper noun masked.</p>
          <ul className="prose-wide sans" style={{ fontSize: 14.5 }}>
            {head.map((r) => {
              const dr = data.drivers.find((x) => x.tradition === r.tradition);
              const m = masked.get(r.tradition);
              const terms = dr ? dr.top_driver_terms.split("; ").slice(0, 5).map((w) => w.split(" (")[0]).join(", ") : "";
              const verdict = m === undefined ? "" : r.closer_than_baseline && m.closer_than_baseline ? "the resemblance is more than a shared cast"
                : r.closer_than_baseline ? "the resemblance rests mostly on shared nouns"
                : m.closer_than_baseline ? "the baseline's shared nouns hid a resemblance in the rest of the wording" : "no resemblance beyond the baseline either way";
              return <li key={r.tradition}><strong>{r.tradition}:</strong> matches carried by {terms}{dr ? `; nouns give ${pc(dr.noun_share_of_cosine_median)} of the closest match` : ""}.{m && <> With nouns masked, {m.closer_than_baseline ? "closer" : "not closer"} than the baseline ({signed(m.diff)}, {pval(m.diff_p_upper)}): {verdict}.</>}</li>;
            })}
          </ul>
          {otherRep && <p className="sans small muted prose-wide">With {REP_NAME[otherRep]} instead of {REP_NAME[prim]}, parables are closer than their baseline for {list(closerOther)}. Every parable and its nearest folktales: <a href="#/parables">the Parables explorer</a>.</p>}
        </Section>

        <Flourish />
        <Section id="validity" num="IV" title="Validity and robustness">
          <div className="prose-wide">
            <p>Can the method find a story's relatives at all? The {int(data.corpus.calibration)} retellings from religious collections are off the map (no retelling or near-copy stays in the pool; highest cosine {Object.entries(data.exclusion).map(([r, v]) => `${f2(v)} with ${REP_NAME[r] ?? r}`).join(", ")}). For {c0 ? `${c0.hits} of ${c0.queries}` : "–"} of them, a folktale of the same tale type is among the {s.attachK} nearest ({REP_NAME[prim]}; chance {c0 ? f3(c0.chance_at_k) : "–"}).{cal.get("tfidf_nouns_masked") && <> With nouns masked it is still {cal.get("tfidf_nouns_masked")!.hits} of {cal.get("tfidf_nouns_masked")!.queries}.</>}</p>
          </div>
          <Figure data={data} file="fig3_validity" label="Figure 3" alt="Calibration recall and type-vote accuracy for each representation against chance, and the pending hand labels" />
          <h3>Table 1. Does the headline survive each modelling choice?</h3>
          <p className="prose-wide sans small muted">Per tradition the headline is two findings: closer than the baseline, and a community profile that differs from the baseline's. A check holds when every comparable verdict stays the same, partly when at least 60% do.</p>
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>Check</th><th>What changes</th><th>Holds</th><th className="num">Verdicts kept</th><th>Key number</th></tr></thead>
              <tbody>{data.table1.map((r) => (
                <tr key={r.check}><td><strong>{r.check}</strong></td><td>{r.variant}</td><td><span className={`chip ${r.holds === "yes" ? "yes" : r.holds === "partly" ? "partly" : "no"}`}>{r.holds}</span></td><td className="num">{r.agreement}</td><td>{r.key_number}</td></tr>
              ))}</tbody>
            </table>
          </div>
          {reg && <p className="sans small prose-wide" style={{ marginTop: 12 }}><strong>Length.</strong> Closeness rises with length, so the baselines are cut to the parables' lengths (matched in {data.length.matching.filter((x) => x.matched).length} of {data.length.matching.length} traditions). At equal length the order of the traditions is {reg.order_at_equal_length} (raw: {reg.order_raw}).</p>}
          <p className="sans small prose-wide"><strong>Hand labels:</strong> <span className={`chip ${data.hand.status === "pending" ? "partly" : "yes"}`}>{data.hand.status}</span> Two coders judge the closest pair of {s.handLabelPairs} parables (same plot, shared motif, theme only, unrelated); precision and Cohen's κ appear in Figure 3 once coded. The <a href="#/validation">Validation</a> page collects judgements on folktale pairs.</p>
          <details className="how" style={{ marginTop: 16 }}>
            <summary>Supplementary figures</summary>
            <Figure data={data} file="figS1_labels" label="Supplementary Figure S1" alt="Tale type, region and source collection against their nulls for every edge construction" />
            <Figure data={data} file="figS2_headline_embedding" label="Supplementary Figure S2" alt="Figure 2 with embeddings" />
          </details>
        </Section>

        <Flourish />
        <Section id="limits" num="V" title="What we can and cannot conclude">
          <div className="two-col">
            <div className="prose">
              <h3>We can say</h3>
              <ul>
                <li>How close each tradition's parables are to this folktale corpus, against non-story text of the same translation and against folktale excerpts of the same length.</li>
                <li>Which folktale communities and tale types each tradition's parables reach more than their baseline does.</li>
                <li>Whether that survives other graphs, the other representation, length control, masking of nouns, names and collection formulae, and the removal of hub folktales (Table 1).</li>
              </ul>
            </div>
            <div className="prose">
              <h3>We cannot say</h3>
              <ul>
                <li><strong>Who borrowed from whom.</strong> Similarity has no direction.</li>
                <li><strong>How old a story is.</strong> A recording date is not an origin date.</li>
                <li><strong>That a shared plot exists.</strong> Shared vocabulary is not shared narrative; the noun-masked check narrows the gap but does not close it.</li>
                <li><strong>Anything about world folklore or a whole religion.</strong> The corpus is English and {pc(data.corpus.europeShare)} of the tales with a recorded region are European; each tradition is one or two translations.</li>
                <li><strong>Anything about the moral.</strong> Whether parables are folktales with a moral attached stays our motivation, not our result.</li>
              </ul>
            </div>
          </div>
          <p className="note-earlier"><strong>Earlier plan.</strong> The project first set out to code the lesson of each tale and parable. That study was dropped before it produced any result, because text similarity cannot test a moral; its code is kept in the repository under <span className="mono">legacy/</span> and is not part of this site.</p>
          <p className="sans small muted">Numbers built {data.built} from commit {data.commit} by <span className="mono">python -m ouaw.run --stage site</span>; every number comes from the repository's <span className="mono">results/</span> folder.</p>
        </Section>
      </div>
    </>
  );
}
