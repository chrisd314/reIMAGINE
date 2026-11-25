import { useStory } from "../data";
import { Failed, Loading } from "../components/ui";
import { int, pct } from "../lib/format";

const COURSE = "https://sunelehmann.com/socialgraphs2026-web/";

// Every method of the analysis, the course week that teaches it, and where it is used on this site.
const METHODS: { method: string; week: string; anchor?: string; where: string; course: boolean }[] = [
  { method: "Document checks and cleaning before modelling", week: "Week 5 · from words to documents", anchor: "weeks/week5.html#documents", where: "Folktales · 1", course: true },
  { method: "Tokenisation, stop words (negations kept)", week: "Week 5 · from raw text to tokens", anchor: "weeks/week5.html#tokens", where: "Folktales · 2", course: true },
  { method: "Cosine similarity, and ten nearest neighbours against ten random ones", week: "Week 5 · where counting stops", anchor: "weeks/week5.html#counting-stops", where: "Folktales · 2, Parables · 2–3", course: true },
  { method: "TF–IDF, and taking the names out", week: "Week 6 · documents need better weights · topics", anchor: "weeks/week6.html#tfidf", where: "Folktales · 2 and 4, Parables · 5–6", course: true },
  { method: "LDA topics of the communities", week: "Week 6 · find recurring themes", anchor: "weeks/week6.html#topics", where: "Folktales · 4", course: true },
  { method: "Sentence embeddings (all-MiniLM-L6-v2), passages along sentence boundaries", week: "Week 7 · one vector for a whole text · corpus atlas", anchor: "weeks/week7.html#document-embeddings", where: "Folktales · 2, Parables · 6", course: true },
  { method: "A held-out labelled test set for a measurement", week: "Weeks 7 and 8 · validation · compare against a hand-labelled sample", anchor: "weeks/week7.html#sentiment", where: "Parables · 2", course: true },
  { method: "Degree distribution on log–log axes, cumulative distribution", week: "Weeks 1–2 · degree distributions, power laws", anchor: "weeks/week1.html#degree-distributions", where: "Folktales · 3", course: true },
  { method: "Random graph G(n, m), clustering", week: "Week 2 · the random graph · clustering", anchor: "weeks/week2.html#something-is-missing-clustering", where: "Folktales · 3", course: true },
  { method: "Degree-preserving shuffles (edge swaps)", week: "Week 2 · shuffling: the model becomes a test", anchor: "weeks/week2.html#shuffling-the-model-becomes-a-test", where: "Folktales · 3, 4, 7", course: true },
  { method: "Permutation p-values, p = (1 + k)/(1 + N)", week: "Week 2 · goodies (permutation)", anchor: "weeks/week2.html#goodies", where: "Parables · 3, 4, 6", course: true },
  { method: "PageRank compared with shuffles", week: "Week 3 · who has important friends · compared to what?", anchor: "weeks/week3.html#who-has-important-friends", where: "Folktales · 7", course: true },
  { method: "Attribute assortativity, and label shuffles, also within groups", week: "Week 3 · mixing patterns · shuffling the labels", anchor: "weeks/week3.html#mixing-patterns-do-the-important-stick-together", where: "Folktales · 5", course: true },
  { method: "Modularity, Louvain, seed stability by NMI, NMI with labels", week: "Week 4 · modularity · Louvain", anchor: "weeks/week4.html#louvain", where: "Folktales · 4–6", course: true },
  { method: "Weighted networks, global threshold, disparity-filter backbone, drawing rules", week: "Week 4 · weights · backbones", anchor: "weeks/week4.html#backbones", where: "Folktales · 3, 4, 6", course: true },
  { method: "k-nearest-neighbour graphs", week: "not in the course", where: "Folktales · 6", course: false },
  { method: "Part-of-speech tags (spaCy) to mask nouns", week: "spaCy is used in weeks 5 and 7, but part-of-speech tags are not taught", where: "Parables · 5–6", course: false },
  { method: "Bootstrap intervals, Jensen–Shannon divergence, regression on length, Mann-Whitney test", week: "not in the course (supporting statistics)", where: "Parables · 3, 4, 6", course: false },
];

export function MethodsPage() {
  const { data: d, error } = useStory();
  if (error) return <Failed error={error} />;
  if (!d) return <Loading />;
  const c = d.corpus;
  return (
    <div className="page">
      <div className="wrap">
        <div className="kicker">reIMAGINE</div>
        <h1>Methods and sources</h1>
        <p className="lede">Every method of the analysis, where the course teaches it, and where the data come from. The repository holds the code, every result table and the log of decisions.</p>

        <section>
          <h2>Methods and the course</h2>
          <p className="prose">The methods follow the DTU course 02805 <a href={COURSE}>Social Graphs and Interactions</a> (2026). Three kinds of supporting statistics go beyond it, and they are marked.</p>
          <div className="table-wrap">
            <table className="data">
              <thead><tr><th>Method</th><th>Course</th><th>Used in</th></tr></thead>
              <tbody>{METHODS.map((m) => (
                <tr key={m.method}><td>{m.method}</td><td>{m.anchor ? <a href={COURSE + m.anchor}>{m.week}</a> : <span className="muted">{m.week}</span>}{!m.course && <span className="chip partly" style={{ marginLeft: 6 }}>supporting</span>}</td><td>{m.where}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </section>

        <section className="prose">
          <h2>Data</h2>
          <ul>
            <li><strong>Folktales.</strong> {int(c.folktales)} English folktale versions from <em>Annotated Folktales</em> (Hagedorn &amp; Darányi 2022, <a href="https://doi.org/10.5334/johd.78">doi:10.5334/johd.78</a>, repository j-hagedorn/trilogy at a pinned commit), built on D. L. Ashliman's <em>Folktexts</em> (University of Pittsburgh). {int(c.typed)} carry one ATU tale type (Uther 2004, <em>The Types of International Folktales</em>), {int(c.withRegion)} a recorded region ({pct(c.europeShare)} European) and {int(c.collectionKnown)} a source book. Regions follow the UN M49 sub-regions. The mapping from recorded places to regions was drafted once with Natural Earth country points and reviewed by hand.</li>
            <li><strong>Held-out retellings.</strong> {int(c.calibration)} religious retellings of known tale type from the same corpus are kept out of the network and used only as the test of Parables · 2.</li>
            <li><strong>Parables and baseline passages.</strong> Public-domain translations: the World English Bible (eBible.org) and, read at sacred-texts.com, Cowell's <em>Jātaka</em>, Kern's <em>Saddharma-Puṇḍarīka</em>, Müller's <em>Dhammapada</em>, Rapaport's <em>Tales and Maxims from the Midrash</em>, Taylor's <em>Sayings of the Jewish Fathers</em>, Whinfield's <em>Masnavi</em> and Legge's <em>Texts of Taoism</em>.</li>
            <li><strong>Model.</strong> sentence-transformers/all-MiniLM-L6-v2 at a pinned revision (Apache-2.0).</li>
          </ul>
        </section>

        <section className="prose">
          <h2>Reproduce</h2>
          <pre className="cmd">uv sync --group spacy{"\n"}uv run python -m reimagine.run --stage all{"\n"}cd web &amp;&amp; npm ci &amp;&amp; npm run build</pre>
          <p>Seeds are fixed and embeddings cached. The pipeline writes the three data files this site reads (<code>data/site/story.json</code>, <code>network.json</code>, <code>near.json</code>), so no number on the site is typed by hand. The shuffles you run on the Folktales and Parables pages use the same tales, partitions and statistics as the pipeline, so their observed values are the published ones.</p>
        </section>

        <section className="prose">
          <h2>Reading the texts</h2>
          <p>The site shows only openings of at most {d.settings.openingWords} words. Every folktale links to the page of D. L. Ashliman's <em>Folktexts</em> it was taken from (the corpus took each tale from the page of its tale type, and the link opens that page at the tale's title), and every parable and passage links to its source at sacred-texts.com or eBible.org. The full corpus is the <a href="https://github.com/j-hagedorn/trilogy">Annotated Folktales repository</a>.</p>
        </section>

        <section className="prose">
          <h2>Authors, licence and credits</h2>
          <p>reIMAGINE is a project for the course 02805 Social Graphs and Interactions at DTU (Technical University of Denmark), autumn 2026, by Christos Diamantis, Dávid Weiner and Evangelos Panagiotopoulos.</p>
          <p>The site and its repository are released under CC BY-NC-SA 4.0. The folktale corpus states two licences, and we follow the more restrictive one. Its ShareAlike term carries over to everything built from the corpus, including the data files this site reads, and its NonCommercial term rules out commercial use. The site shows titles, labels and openings of at most {d.settings.openingWords} words, never full texts.</p>
          <p>Fonts: Source Serif 4, Inter and IM Fell English (SIL Open Font License). Data built {d.built}{d.commit ? ` from commit ${d.commit}` : ""}.</p>
        </section>
      </div>
    </div>
  );
}
