import { communityName, shortType, type Network, type Story } from "../../data";
import { Chapter } from "../../components/ui";
import { int, list, pct } from "../../lib/format";
import { CHECKS, HEADLINE, holds } from "../parables/BreakChapter";

export function AnswerChapter({ d, net }: { d: Story; net: Network }) {
  const R = d.byRep[d.primary];
  const all = [{ id: "h", match: (v: string) => v === HEADLINE }, ...CHECKS];
  const score = (t: string) => all.filter((c) => holds(d, t, c.match)).length;
  const robust = d.traditions.filter((t) => score(t) === all.length);
  const rows = d.traditions.map((t) => {
    const h = R.headline.find((x) => x.tradition === t)!;
    const top = R.types.filter((x) => x.tradition === t && x.kind === "parable").sort((a, b) => a.rank - b.rank)[0];
    const words = R.cells.find((c) => c.tradition === t && c.community === h.topCommunity)?.words.split(" ").slice(0, 3).join(", ");
    return { t, s: score(t), h, top, words };
  }).sort((a, b) => b.s - a.s);
  const org = (label: string, within = false) =>
    net.maps[d.primary].organise.find((o) => o.label === label && o.measure === "nmi" && o.null === (within ? "within-collection shuffle" : "label shuffle"));

  return (
    <Chapter id="answer" num="The answer" title="So, where do parables land?">
      <div className="card question" style={{ marginBottom: 22 }}>
        <div className="tag">The question</div>
        <p>Do religious parables resemble folktales more closely than non-story text from their own traditions does, and which parts of the folktale corpus and which tale types do they come closest to?</p>
      </div>

      <h3>What the network can answer</h3>
      <ul className="answer-list">
        <li><strong>{robust.length ? `${list(robust)} parables do.` : "No tradition does under every check."}</strong> {robust.length ? `They sit closer to folktales than non-story text from their own tradition under all ${all.length} versions of the test.` : ""} {list(rows.filter((r) => r.s < all.length && r.s > 1).map((r) => `${r.t} (${r.s} of ${all.length})`))} lean the same way but not under every check. For the rest the result depends on how the text is measured.</li>
        <li><strong>They land in different places.</strong> Each tradition's parables reach their own corner of the map:
          <div className="table-wrap" style={{ marginTop: 8 }}>
            <table className="data">
              <thead><tr><th>Tradition</th><th className="n">Checks held</th><th>Leans towards, against its baseline</th><th>Tale type its neighbours vote for most</th></tr></thead>
              <tbody>{rows.map((r) => (
                <tr key={r.t}><td>{r.t}</td><td className="n">{r.s} of {all.length}</td><td>{communityName(d, r.h.topCommunity, d.primary)} ({r.words}){r.h.topSig ? "" : ", not significant"}</td><td>{r.top ? `ATU ${r.top.atu} ${shortType(r.top.name, 60)}` : "–"}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </li>
        <li><strong>The folktale network is a map of story types, not of places.</strong> Tale type agrees with the communities well above chance ({org("atu_type")?.excess.toFixed(2)}), even within one source book, while the apparent geography ({org("region")?.excess.toFixed(2)}) is mostly the book a tale was printed in ({org("region", true)?.excess.toFixed(3)} within books).</li>
      </ul>

      <h3 style={{ marginTop: 30 }}>What it cannot answer</h3>
      <ul className="answer-list cannot">
        <li><strong>Whether parables are “folktales with a moral”.</strong> Similarity of wording cannot see a moral. That question started the project, and it stays open.</li>
        <li><strong>Whether one borrowed from the other.</strong> Nothing here has dates or routes of transmission, and being close is not being descended.</li>
        <li><strong>Anything about world folklore.</strong> The map is one editor's English selection of {int(d.corpus.folktales)} tales, {pct(d.corpus.europeShare)} of them European, and the translator is known for only {int(d.corpus.translatorKnown)}.</li>
        <li><strong>The originals.</strong> Every text is read in English translation, most made between 1881 and 1907 (the Bible text is the modern World English Bible). The baseline keeps the translator fixed wherever it can, but not for the Buddhist texts (Müller's Dhammapada against Cowell's Jātaka and Kern's Lotus Sūtra), and no baseline removes the act of translation itself.</li>
        <li><strong>How good each single match is.</strong> The method finds the tale type of {pct(d.calibration.recall)} of the held-out retellings, so it works on average. Single parable–folktale pairs were not judged by hand, and a close pair can share a cast rather than a plot (<a href="#/parables/words">Parables · 5</a>).</li>
      </ul>
      <div className="flourish" aria-hidden>❦</div>
    </Chapter>
  );
}
