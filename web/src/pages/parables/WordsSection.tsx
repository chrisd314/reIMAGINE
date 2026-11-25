import { useState } from "react";
import { communityName, type Near, type Story } from "../../data";
import { TextPanel } from "../../components/panels";
import { Chapter, DataTable, Result, Why } from "../../components/ui";
import { list, pct } from "../../lib/format";
import { holds } from "./BreakChapter";

const ARCHAIC = new Set(["thou", "thee", "thy", "thine", "ye", "unto", "hath", "doth", "art", "shalt", "wilt", "saith"]);

/** "lord (7); said (7); ..." -> [["lord", 7], ["said", 7], ...] */
function parseTerms(s: string): [string, number][] {
  return s.split("; ").map((x) => { const m = x.match(/^(.*) \((\d+)\)$/); return m ? [m[1], Number(m[2])] as [string, number] : [x, 1] as [string, number]; });
}

export function WordsSection({ d, near }: { d: Story; near: Near | null }) {
  const [word, setWord] = useState<{ t: string; w: string } | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const R = d.byRep.tfidf;
  const rows = d.traditions.map((t) => {
    const par = d.drivers.find((x) => x.tradition === t && x.kind === "parable");
    const base = d.drivers.find((x) => x.tradition === t && x.kind === "baseline");
    const h = R.headline.find((x) => x.tradition === t)!;
    const words = R.cells.find((c) => c.tradition === t && c.community === h.topCommunity)?.words.split(" ").slice(0, 3).join(", ") ?? "";
    const terms = par ? parseTerms(par.terms) : [];
    return { t, par, base, h, words, terms, masked: holds(d, t, (v) => v === "tfidf_nouns_masked"), archaic: terms.filter(([w]) => ARCHAIC.has(w)).map(([w]) => w) };
  });
  const archaic = rows.filter((r) => r.archaic.length);
  // traditions that share the same old-translation words are named together: "thou for Jewish and Sufi parables"
  const archaicByWords = new Map<string, string[]>();
  archaic.forEach((r) => { const w = list(r.archaic); archaicByWords.set(w, [...(archaicByWords.get(w) ?? []), r.t]); });
  const archaicText = list([...archaicByWords].map(([w, ts]) => `${w} for ${list(ts)} parables`));
  const shares = rows.map((r) => r.par?.nounShare ?? 0).filter((x) => x > 0);
  const lost = rows.filter((r) => r.h.closer && !r.masked).map((r) => r.t), gained = rows.filter((r) => !r.h.closer && r.masked).map((r) => r.t);
  // the parables whose best match is carried by the clicked word (words behind each text's nearest folktale)
  const matches = word && near ? d.texts.filter((x) => x.tradition === word.t && x.kind === "parable" && (near.texts.tfidf[x.id]?.[0] ?? "").split(" ").includes(word.w)) : [];
  const openText = open ? d.texts.find((x) => x.id === open) : undefined;
  return (
    <Chapter id="words" num="Parables · 5" title="What does the resemblance rest on?">
      <Why course="week 6 (TF–IDF weights, names out), week 7 (what a similarity measures)"
        what={<>For every text and its most similar folktale, we list the words that carry most of their cosine (the largest products of their TF–IDF weights) and how much of the similarity comes from nouns. Then we mask every noun and name (spaCy part-of-speech tags) and test again.</>}
        why={<>Similarity can come from a shared cast (animals, kings, servants) rather than a shared plot. A parable about a lion will sit near animal tales almost by construction. Knowing which words carry a match says what a “resemblance” means for each tradition.</>} />
      <p className="sans small muted" style={{ margin: "0 0 10px" }}>Click a word to see the parables whose best match it carries, and read them beside their folktale.</p>
      <div className="multiples">
        {rows.map((r) => (
          <div key={r.t} className="multiple">
            <h4>{r.t}<span className={`chip ${r.masked ? "yes" : "no"}`} title="Closer to folktales than the baseline with every noun masked?">{r.masked ? "✓" : "✗"} without nouns</span></h4>
            <div className="word-cloud">{r.terms.slice(0, 8).map(([w, n], k) => (
              <button key={w} type="button" className="word-btn" aria-pressed={word?.t === r.t && word.w === w} onClick={() => { setWord(word?.t === r.t && word.w === w ? null : { t: r.t, w }); setOpen(null); }}
                style={{ fontSize: `${(1.25 - (0.45 * k) / 7).toFixed(2)}rem` }}>{w}<small> {n}</small></button>
            ))}</div>
            <p className="type">Nouns carry {r.par ? pct(r.par.nounShare) : "–"} of the similarity (baseline {r.base ? pct(r.base.nounShare) : "–"}).</p>
            <p className="type">Leans towards {communityName(d, r.h.topCommunity, "tfidf")} ({r.words}){r.h.topSig ? "" : ", not significant"}.</p>
          </div>
        ))}
      </div>
      {word && (
        <div className="two-col even" style={{ marginTop: 16 }}>
          <div className="card">
            <div className="tag">{word.t} parables whose best match is carried by “{word.w}” · {near ? matches.length : "…"}</div>
            <ul className="sans small" style={{ margin: 0, paddingLeft: 18 }}>
              {matches.map((x) => <li key={x.id}><button type="button" className="linklike" onClick={() => setOpen(x.id)}>{x.title}</button></li>)}
              {near && matches.length === 0 && <li className="muted">none among the best matches (the word counts above include all of the tradition's matches)</li>}
            </ul>
          </div>
          {openText && <TextPanel story={d} near={near} rep="tfidf" t={openText} />}
        </div>
      )}
      <DataTable head={["Tradition", "Top words of the matches", "Noun share (parables)", "Noun share (baseline)", "Closer than baseline without nouns"]}
        rows={rows.map((r) => [r.t, r.terms.slice(0, 6).map(([w]) => w).join(", "), r.par ? pct(r.par.nounShare) : "–", r.base ? pct(r.base.nounShare) : "–", r.masked ? "yes" : "no"])} />
      <Result>
        <p>Matches rest on the people, animals and objects of a story: nouns carry {pct(Math.min(...shares))} to {pct(Math.max(...shares))} of a parable's similarity to its nearest folktale. With every noun masked, {list(rows.filter((r) => r.masked).map((r) => r.t))} parables are closer to folktales than their baseline.{lost.length > 0 && <> {list(lost)} {lost.length === 1 ? "loses its" : "lose their"} lead: that resemblance rested on a shared cast.</>}{gained.length > 0 && <> {list(gained)} {gained.length === 1 ? "becomes" : "become"} closer only once nouns are masked.</>}</p>
        {archaic.length > 0 && <p>Old-translation words are among the top matching words: {archaicText}. Part of any resemblance is the translators' English, which is why each tradition is compared with its own non-story text, from the same translation wherever possible.</p>}
      </Result>
    </Chapter>
  );
}
