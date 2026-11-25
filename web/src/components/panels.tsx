import { useState, type ReactNode } from "react";
import { communityName, communityOf, readLinks, shortType, type NetMap, type Near, type Rep, type Story, type Text } from "../data";
import { fmt, int } from "../lib/format";

// Reading panels: a folktale or a text, its nearest folktales, the words behind each match, the two openings side by
// side, and links to read both texts in full at their source.

export function ReadLinks({ story, atu, title, url }: { story: Story; atu?: string; title: string; url?: string }) {
  const links = url ? [{ href: url, label: "Read it at the source" }] : readLinks(story.links, atu ?? "", title);
  return (
    <span className="read-links">
      {links.map((l) => <a key={l.href} href={l.href} target="_blank" rel="noreferrer">{l.label} ↗</a>)}
    </span>
  );
}

function TaleMeta({ story, map, rep, i }: { story: Story; map?: NetMap; rep?: Rep; i: number }) {
  const F = story.folktales;
  return (
    <div className="sans small muted">
      {F.atu[i] ? `ATU ${F.atu[i]} ${shortType(F.atuName[i], 60)}` : "no tale type"}{F.region[i] ? ` · ${F.region[i]}` : ""}
      {F.collection[i] ? ` · ${F.collection[i].replace(/\b\w/g, (c) => c.toUpperCase())}` : ""}
      {map ? ` · ${rep ? communityName(story, communityOf(map.group[i]), rep) : communityOf(map.group[i])}, ${map.degree[i]} links` : ""} · {int(F.tokens[i])} words
    </div>
  );
}

/** Two texts side by side, with the words that carry their similarity and where to read each in full. */
export function PairCard({ story, near, left, right, cosine, words, onClose }: {
  story: Story; near: Near | null; left: { kind: "tale"; i: number } | { kind: "text"; t: Text } | { kind: "retelling"; id: string };
  right: number; cosine?: number; words?: string; onClose?: () => void;
}) {
  const F = story.folktales;
  const side = (s: typeof left) => {
    if (s.kind === "tale") return { who: "Folktale", title: F.title[s.i], meta: <TaleMeta story={story} i={s.i} />, opening: near?.opening[s.i], link: <ReadLinks story={story} atu={F.atu[s.i]} title={F.title[s.i]} /> };
    if (s.kind === "text") return { who: `${s.t.tradition} ${s.t.kind === "parable" ? "parable" : "non-story passage"}`, title: s.t.title,
      meta: <div className="sans small muted">{s.t.source}{s.t.year ? `, ${s.t.year}` : ""} · {int(s.t.tokens)} words</div>, opening: s.t.opening, link: <ReadLinks story={story} title={s.t.title} url={s.t.url} /> };
    const it = story.calibration.items.find((x) => x.id === s.id)!;
    return { who: `Held-out retelling · ${it.collection}`, title: it.title, meta: <div className="sans small muted">ATU {it.atu} {shortType(it.atuName, 50)}</div>,
      opening: it.opening, link: <ReadLinks story={story} atu={it.atu} title={it.title} /> };
  };
  const a = side(left), b = side({ kind: "tale", i: right });
  return (
    <div className="pair">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <span className="label" style={{ margin: 0 }}>Read the pair{cosine !== undefined ? ` · cosine ${fmt(cosine, 3)}` : ""}</span>
        {onClose && <button type="button" className="btn" onClick={onClose}>Close</button>}
      </div>
      <div className="reading">
        {[a, b].map((x, k) => (
          <div key={k} className={`side ${k ? "folk" : left.kind === "text" && left.t.kind === "baseline" ? "base" : ""}`}>
            <div className="who">{x.who}</div>
            <div className="t">{x.title}</div>
            {x.meta}
            {x.opening ? <div className="o" style={{ marginTop: 6 }}>“{x.opening}”</div> : <div className="muted small">opening loading…</div>}
            <div style={{ marginTop: 8 }}>{x.link}</div>
          </div>
        ))}
      </div>
      {words && <><div className="who" style={{ marginTop: 10 }}>Words that carry the match (TF–IDF)</div><div className="words">{words.split(" ").map((w) => <span key={w}>{w}</span>)}</div></>}
    </div>
  );
}

/** A ranked list of nearest folktales with cosine bars, their shared words and a button to read each pair. */
export function NearList({ story, items, sameType, onOpen, onPair, pairOpen }: {
  story: Story; items: { i: number; cos: number; words?: string }[]; sameType?: string; onOpen?: (i: number) => void;
  onPair: (k: number) => void; pairOpen: number | null;
}) {
  const F = story.folktales, max = Math.max(...items.map((x) => x.cos), 1e-9);
  return (
    <ol className="nearlist">
      {items.map((x, k) => (
        <li key={x.i} className={pairOpen === k ? "open" : undefined}>
          <span className="rank">{k + 1}</span>
          <span className="body">
            {onOpen ? <button type="button" className="linklike" onClick={() => onOpen(x.i)}>{F.title[x.i]}</button> : <strong>{F.title[x.i]}</strong>}
            <span className="muted"> · {F.atu[x.i] ? `ATU ${F.atu[x.i]}` : "no type"}{sameType && F.atu[x.i] === sameType ? " (same type)" : ""}</span>
            {x.words && <span className="nl-words">{x.words}</span>}
            <span className="scorebar" aria-hidden><span style={{ width: `${(100 * x.cos) / max}%` }} /></span>
          </span>
          <span className="score">{fmt(x.cos, 3)}</span>
          <button type="button" className="btn small" onClick={() => onPair(k)} aria-pressed={pairOpen === k}>Read pair</button>
        </li>
      ))}
    </ol>
  );
}

/** Everything about one folktale: labels, opening, where to read it, and its nearest folktales. */
export function TalePanel({ story, map, near, rep, i, onSelect, onClose }: {
  story: Story; map: NetMap; near: Near | null; rep: Rep; i: number; onSelect: (j: number) => void; onClose?: () => void;
}) {
  const F = story.folktales;
  const [pair, setPair] = useState<number | null>(null);
  const nn = near?.folk[rep];
  const items = nn ? nn.idx[i].map((j, k) => ({ i: j, cos: nn.cos[i][k], words: nn.words[i][k] })) : [];
  return (
    <div className="card tale-panel">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <h4 style={{ margin: 0 }}>{F.title[i]}</h4>
        {onClose && <button type="button" className="btn small" onClick={onClose}>Close</button>}
      </div>
      <TaleMeta story={story} map={map} rep={rep} i={i} />
      {map.pagerankZ[i] !== null && <div className="sans small muted">PageRank {fmt(map.pagerank[i], 2)}× the average tale, {fmt(Math.abs(map.pagerankZ[i]), 1)} standard deviations {map.pagerankZ[i] >= 0 ? "above" : "below"} its degree-preserving shuffles</div>}
      {near && <p className="o" style={{ margin: "8px 0" }}>“{near.opening[i]}”</p>}
      <ReadLinks story={story} atu={F.atu[i]} title={F.title[i]} />
      <span className="label" style={{ marginTop: 12 }}>Its {story.settings.nearK} nearest folktales ({rep === "tfidf" ? "TF–IDF" : "embeddings"})</span>
      {!near ? <p className="muted small">Loading the neighbours…</p> :
        <NearList story={story} items={items} sameType={F.atu[i]} onOpen={(j) => { setPair(null); onSelect(j); }} onPair={(k) => setPair(pair === k ? null : k)} pairOpen={pair} />}
      {pair !== null && items[pair] && <PairCard story={story} near={near} left={{ kind: "tale", i }} right={items[pair].i} cosine={items[pair].cos} words={items[pair].words} onClose={() => setPair(null)} />}
    </div>
  );
}

/** Everything about one parable or baseline passage: opening, source, closeness, and its nearest folktales. */
export function TextPanel({ story, near, rep, t, onSelectTale, extra }: {
  story: Story; near: Near | null; rep: Rep; t: Text; onSelectTale?: (j: number) => void; extra?: ReactNode;
}) {
  const [pair, setPair] = useState<number | null>(0);
  const r = t.rep[rep], words = near?.texts[rep][t.id] ?? [];
  const items = r.nearest.map((j, k) => ({ i: j, cos: r.cos[k], words: words[k] }));
  const F = story.folktales;
  const voted = r.voted ? F.atuName[F.atu.indexOf(r.voted)] : null;
  return (
    <div className="card tale-panel">
      <div className="who">{t.tradition} {t.kind === "parable" ? "parable" : "non-story passage"} · {t.source}{t.year ? `, ${t.year}` : ""}</div>
      <h4 style={{ margin: "2px 0 4px" }}>{t.title}</h4>
      <p className="o" style={{ margin: "6px 0" }}>“{t.opening}”</p>
      <ReadLinks story={story} title={t.title} url={t.url} />
      <div className="sans small" style={{ marginTop: 8 }}>
        Folk-closeness <strong>{fmt(r.closeness, 3)}</strong> ({int(t.tokens)} words){r.community ? <> · its neighbours sit mostly in <strong>{communityName(story, r.community, rep)}</strong></> : null}
        {r.voted ? <> · they vote for <strong>ATU {r.voted}{voted ? ` ${shortType(voted, 40)}` : ""}</strong></> : null}
      </div>
      {extra}
      <span className="label" style={{ marginTop: 12 }}>Its {story.settings.nearK} nearest folktales ({rep === "tfidf" ? "TF–IDF" : "embeddings"})</span>
      <NearList story={story} items={items} onOpen={onSelectTale} onPair={(k) => setPair(pair === k ? null : k)} pairOpen={pair} />
      {pair !== null && items[pair] && <PairCard story={story} near={near} left={{ kind: "text", t }} right={items[pair].i} cosine={items[pair].cos} words={items[pair].words} onClose={() => setPair(null)} />}
    </div>
  );
}
