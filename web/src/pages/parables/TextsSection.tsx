import { useMemo, useState } from "react";
import type { Near, Story } from "../../data";
import { TextPanel } from "../../components/panels";
import { RepToggle, useRep } from "../../components/rep";
import { Chapter, Result, Segmented, Why } from "../../components/ui";
import { fmt, int } from "../../lib/format";

export function TextsSection({ d, near }: { d: Story; near: Near | null }) {
  const { rep } = useRep();
  const [trad, setTrad] = useState("all");
  const [kind, setKind] = useState<"parable" | "baseline" | "both">("both");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<"closeness" | "title" | "length">("closeness");
  const [sel, setSel] = useState<string>(() => d.texts.filter((t) => t.kind === "parable").sort((a, b) => b.rep[rep].closeness - a.rep[rep].closeness)[0].id);
  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    const out = d.texts.filter((t) => (trad === "all" || t.tradition === trad) && (kind === "both" || t.kind === kind) && (!s || t.title.toLowerCase().includes(s) || t.opening.toLowerCase().includes(s)));
    return out.sort((a, b) => (sort === "closeness" ? b.rep[rep].closeness - a.rep[rep].closeness : sort === "length" ? b.tokens - a.tokens : a.title.localeCompare(b.title)));
  }, [d, trad, kind, q, sort, rep]);
  const max = Math.max(...d.texts.map((t) => t.rep[rep].closeness));
  const text = d.texts.find((t) => t.id === sel);
  const src = (tr: string, k: string) => d.sources.find((s) => s.tradition === tr && s.kind === k);
  const minP = Math.min(...d.length.matching.map((m) => m.p));
  return (
    <Chapter id="texts" num="Parables · 1" title="The parables and their baseline">
      <Why course="week 5 (documents and their checks)"
        what={<>{int(d.corpus.parables)} parables from five traditions, each from one public-domain English translation, and {int(d.corpus.baseline)} <em>non-story</em> passages cut from the very same translations: sayings, laws, verses, sermons. The passages are consecutive verses or sayings, spread evenly through each book's non-story text, and cut to the lengths of that tradition's parables.</>}
        why={<>These {int(d.corpus.baseline)} passages are the baseline of the outline. A parable and a passage from the same book share the translator and the vocabulary of scripture; they differ in whether they tell a story. If parables sit closer to folktales than their own book's non-story text, it is the story that does it.</>} />
      <div className="table-wrap">
        <table className="data">
          <thead><tr><th>Tradition</th><th className="n">Parables</th><th className="n">median words</th><th>from</th><th className="n">Baseline</th><th className="n">median words</th><th>from</th></tr></thead>
          <tbody>{d.traditions.map((tr) => {
            const a = src(tr, "parable"), c = src(tr, "baseline");
            return <tr key={tr}><td>{tr}</td><td className="n">{a?.n}</td><td className="n">{int(a?.tokens)}</td><td>{a?.sources}</td><td className="n">{c?.n}</td><td className="n">{int(c?.tokens)}</td><td>{c?.sources}</td></tr>;
          })}</tbody>
        </table>
      </div>

      <h3 style={{ marginTop: 26 }}>Browse all {int(d.texts.length)} texts</h3>
      <div className="controls-row">
        <RepToggle />
        <select aria-label="Tradition" value={trad} onChange={(e) => setTrad(e.target.value)}>
          <option value="all">All five traditions</option>{d.traditions.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <Segmented label="Kind" value={kind} onChange={setKind} options={[{ value: "both", label: "Both" }, { value: "parable", label: "Parables" }, { value: "baseline", label: "Non-story" }]} />
        <input type="search" placeholder="Search titles and openings…" aria-label="Search the texts" value={q} onChange={(e) => setQ(e.target.value)} />
        <select aria-label="Sort" value={sort} onChange={(e) => setSort(e.target.value as typeof sort)}>
          <option value="closeness">most folk-like first</option><option value="length">longest first</option><option value="title">by title</option>
        </select>
      </div>
      <div className="two-col even">
        <div className="text-list" role="listbox" aria-label="Texts">
          <div className="sans small muted" style={{ padding: "4px 8px" }}>{list.length} texts</div>
          {list.map((t) => (
            <button key={t.id} type="button" role="option" aria-selected={t.id === sel} className="text-row" onClick={() => setSel(t.id)}>
              <span className={`kind ${t.kind}`} aria-hidden />
              <span className="tr-title">{t.title}<span className="muted"> · {t.tradition}{t.kind === "baseline" ? ", non-story" : ""}</span></span>
              <span className="tr-score"><span className="scorebar"><span style={{ width: `${(100 * t.rep[rep].closeness) / max}%`, background: t.kind === "parable" ? "var(--c1)" : "var(--c2)" }} /></span>{fmt(t.rep[rep].closeness, 3)}</span>
            </button>
          ))}
        </div>
        {text && <TextPanel story={d} near={near} rep={rep} t={text} />}
      </div>
      <Result>
        <p>The baseline is length-matched: in no tradition do parable and passage lengths differ (Mann-Whitney p ≥ {fmt(minP, 2)}). The passages are fixed by rule rather than drawn at random, so every run compares against the same text. Sort by folk-closeness to see which texts sit nearest the folktales, and open any of them to read it beside its nearest folktale.</p>
      </Result>
    </Chapter>
  );
}
