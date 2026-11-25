import { communityName, shortType, useNetwork, useStory, type Rep, type Story } from "../../data";
import { RepToggle, useRep } from "../../components/rep";
import { Chapter, DataTable, Failed, Loading } from "../../components/ui";
import { int, list, pct, points, pval, signed } from "../../lib/format";
import { CHECKS, HEADLINE, holds } from "../parables/BreakChapter";
import { AnswerChapter } from "./AnswerChapter";

/** One tradition: how its parables' links to the folktale communities differ from its baseline's (HTML rows, so the
 *  text stays readable at any width). */
function Panel({ d, rep, t, max }: { d: Story; rep: Rep; t: string; max: number }) {
  const R = d.byRep[rep];
  const h = R.headline.find((x) => x.tradition === t)!;
  const cells = R.cells.filter((c) => c.tradition === t && c.community !== "small");
  const top = R.types.filter((x) => x.tradition === t && x.kind === "parable").sort((a, b) => a.rank - b.rank)[0];
  return (
    <a className="multiple panel-link" href={`#/parables/land?t=${encodeURIComponent(t)}`} aria-label={`${t}: open where its parables land`}>
      <h4>{t}<span className={`chip ${h.closer ? "yes" : "no"}`}>{h.closer ? "closer" : "not closer"}</span></h4>
      <div className="small muted">{signed(h.diff)} folk-closeness vs baseline, {pval(h.p, d.settings.permutations)}</div>
      <ul className="diverging" aria-label={`${t}: share of links to each community, parables minus baseline`}>
        {cells.map((c) => {
          const w = (50 * Math.abs(c.excess)) / max;
          const name = communityName(d, c.community, rep);
          return (
            <li key={c.community} title={`${name} (${c.words.split(" ").slice(0, 3).join(", ")}): parables ${pct(c.par)}, baseline ${pct(c.base)}, ${points(c.excess)}${c.sig ? ", significant" : ""}`}>
              <span className="dv-label">{name !== c.community ? name : `${c.community} ${c.words.split(" ")[0]}`}</span>
              <span className="dv-track">
                <span className="dv-bar" style={{ left: c.excess >= 0 ? "50%" : `${50 - w}%`, width: `${Math.max(w, 0.6)}%`,
                  background: c.excess >= 0 ? "var(--c1)" : "var(--c2)", opacity: c.sig ? 1 : 0.35 }} />
                {c.sig && <span className="dv-star" style={c.excess >= 0 ? { left: `${50 + w}%` } : { right: `${50 + w}%` }}>*</span>}
              </span>
            </li>
          );
        })}
      </ul>
      <div className="type">Neighbours vote for <strong>{top ? `ATU ${top.atu} ${shortType(top.name, 32)}` : "–"}</strong></div>
      <div className="type more">Open {t} in detail →</div>
    </a>
  );
}

export function OverviewPage() {
  const { data: d, error } = useStory();
  const { data: net, error: e2 } = useNetwork();
  const { rep } = useRep();
  if (error || e2) return <Failed error={(error ?? e2) as string} />;
  if (!d || !net) return <Loading what="the book" />;
  const R = d.byRep[rep];
  const max = Math.max(...R.cells.filter((c) => c.community !== "small").map((c) => Math.abs(c.excess)), 0.01);
  const closer = d.byRep[d.primary].headline.filter((h) => h.closer).map((h) => h.tradition);
  const all = [{ id: "h", label: "Main test (TF–IDF)", match: (v: string) => v === HEADLINE }, ...CHECKS];
  const standing = d.traditions.filter((t) => all.every((c) => holds(d, t, c.match)));
  const org = (label: string, within = false) => net.maps[d.primary].organise.find((o) => o.label === label && o.measure === "nmi" && o.null === (within ? "within-collection shuffle" : "label shuffle"));
  return (
    <>
      <header className="hero">
        <div className="wrap">
          <div className="kicker">reIMAGINE · a text-network study</div>
          <h1>Where do parables land in the world of folktales?</h1>
          <p className="lede dropcap">Religious traditions teach with short stories: a sower, a mustard seed, a burning house, an elephant in a dark room. Folktales are short stories too. We placed {int(d.corpus.parables)} parables from five traditions on a network of {int(d.corpus.folktales)} folktales and looked at where they fall.</p>
          <div className="cards">
            <div className="card motivation">
              <div className="tag">Where we started</div>
              <p style={{ margin: 0 }}>Are parables just folktales with a moral attached? A tempting question, but similarity of wording cannot see a moral, so we do not test it. We test what text can show.</p>
            </div>
            <div className="card question">
              <div className="tag">The question we test</div>
              <p>Do religious parables resemble folktales more closely than non-story text from their own traditions does, and which parts of the folktale corpus and which tale types do they come closest to?</p>
            </div>
          </div>
        </div>
      </header>

      <Chapter id="how" num="How we answer it" title="Three steps">
        <div className="steps">
          <div className="step">
            <span className="n">1 · Folklore</span><h3>Tale types</h3>
            <ul><li>{int(d.corpus.folktales)} folktales, each with its ATU tale type ({int(d.corpus.types)} types)</li><li>plus the region it was recorded in and the book it came from</li></ul>
            <p className="found">The tale type is the folklorists' grouping of stories: our ground truth.</p>
            <a className="more" href="#/folktales/corpus">The folktales →</a>
          </div>
          <div className="step">
            <span className="n">2 · Folklore</span><h3>Communities</h3>
            <ul><li>similarity of texts: TF–IDF, and embeddings as a check</li><li>a network of the strongest links, and Louvain communities</li><li>do they follow tale type or location?</li></ul>
            <p className="found">They follow tale type ({org("atu_type")?.excess.toFixed(2)} NMI above shuffles), while location adds almost nothing once the source book is held fixed ({org("region", true)?.excess.toFixed(3)}).</p>
            <a className="more" href="#/folktales/communities">The network →</a>
          </div>
          <div className="step">
            <span className="n">3 · Parables</span><h3>Into the communities</h3>
            <ul><li>{int(d.corpus.parables)} parables placed by similarity to the folktales</li><li>{int(d.corpus.baseline)} non-story passages from the same traditions as baseline, from the same translation wherever possible</li><li>the parable/passage label shuffled {int(d.settings.permutations)} times as the null</li></ul>
            <p className="found">{list(closer)} parables are closer to folktales than their baseline.{standing.length ? ` ${list(standing)} parables stay closer under every check.` : ""}</p>
            <a className="more" href="#/parables">The parables →</a>
          </div>
        </div>
      </Chapter>

      <Chapter id="headline" num="The main result" title="Which part of folklore do parables reach?">
        <p className="prose">For each tradition: how much more (blue) or less (orange) of its parables' links go to each folktale community than its own non-story text's links do. Solid bars are significant after correction for the number of communities. The chip says whether the parables are closer to folktales at all. Click a tradition to open it.</p>
        <div className="controls-row"><RepToggle /><a className="btn" href="#/explore">Explore the whole network →</a></div>
        <div className="multiples" style={{ marginTop: 14 }}>{d.traditions.map((t) => <Panel key={t} d={d} rep={rep} t={t} max={max} />)}</div>
        <DataTable head={["Tradition", "Closer than baseline", "p", "Leans most towards", "Excess", "Significant"]}
          rows={R.headline.map((h) => [h.tradition, h.closer ? "yes" : "no", pval(h.p, d.settings.permutations), communityName(d, h.topCommunity, rep), points(h.topExcess), h.topSig ? "yes" : "no"])} />
        <p className="caption">Hover a bar for the shares. Communities are those of the {rep === "tfidf" ? "TF–IDF" : "embedding"} network, so their numbers differ between the two representations.</p>
      </Chapter>

      <Chapter id="holds" num="Does it hold?" title="Every check at once">
        <div className="two-col">
          <div className="table-wrap">
            <table className="matrix">
              <thead><tr><th>Check</th>{d.traditions.map((t) => <th key={t}>{t}</th>)}</tr></thead>
              <tbody>{all.map((c) => (
                <tr key={c.id}><td>{c.label}</td>{d.traditions.map((t) => {
                  const ok = holds(d, t, c.match);
                  const rows = d.robust.filter((r) => r.tradition === t && c.match(r.variant));
                  const tipText = rows.map((r) => `${r.variant}: ${signed(r.diff)}, ${pval(r.p, d.settings.permutations)}`).join(" · ");
                  return <td key={t} className={ok ? "mark-yes" : "mark-no"} title={tipText} aria-label={`${ok ? "yes" : "no"}. ${tipText}`}>{ok ? "✓" : "·"}</td>;
                })}</tr>
              ))}</tbody>
            </table>
          </div>
          <div>
            <p className="survivors">Still standing under every check: {standing.length ? list(standing) : "no tradition"}</p>
            <p>✓ marks parables closer to folktales than their own non-story passages under that check (one-sided permutation test, p &lt; 0.05). Switch the checks on one by one on the <a href="#/parables/break">Parables page</a>.</p>
          </div>
        </div>
      </Chapter>

      <AnswerChapter d={d} net={net} />
    </>
  );
}
