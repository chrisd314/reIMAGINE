import { useMemo, useState } from "react";
import { REP_NAME, shortType, type CalItem, type Near, type Story } from "../../data";
import { NearList, PairCard, ReadLinks } from "../../components/panels";
import { RepToggle, useRep } from "../../components/rep";
import { BarList, Chapter, DataTable, Result, Why } from "../../components/ui";
import { ordinal, pct, rng } from "../../lib/format";

interface Round { item: CalItem; options: string[] }

/** The held-out retellings in a fixed shuffled order. Each round offers the true tale type and decoys of other retellings. */
function makeRounds(items: CalItem[], nOptions: number): Round[] {
  const rand = rng(20261118);
  const order = items.map((it) => ({ it, k: rand() })).sort((a, b) => a.k - b.k).map((x) => x.it);
  const names = [...new Set(items.map((it) => it.atuName))];
  return order.map((item) => {
    const decoys = names.filter((n) => n !== item.atuName).map((n) => ({ n, k: rand() })).sort((a, b) => a.k - b.k).slice(0, nOptions - 1).map((x) => x.n);
    const options = [item.atuName, ...decoys].map((n) => ({ n, k: rand() })).sort((a, b) => a.k - b.k).map((x) => x.n);
    return { item, options };
  });
}

export function TestChapter({ d, near }: { d: Story; near: Near | null }) {
  const { rep } = useRep();
  const c = d.calibration;
  const rounds = useMemo(() => makeRounds(c.items, c.options), [c]);
  const [at, setAt] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [pair, setPair] = useState<number | null>(null);
  const round = rounds[at % rounds.length];
  const chosen = answers[at];
  const played = Object.keys(answers).map(Number);
  const you = played.filter((k) => answers[k] === rounds[k % rounds.length].item.atuName).length;
  const mapHits = played.filter((k) => rounds[k % rounds.length].item.ranks[rep] <= c.k).length;
  const it = round.item, rank = it.ranks[rep];
  const words = near?.texts[rep][it.id] ?? [];
  const items = it.near[rep].idx.map((j, k) => ({ i: j, cos: it.near[rep].cos[k], words: words[k] }));
  const reps = (["tfidf", "embedding", "tfidf_nouns_masked"] as const).filter((r) => c.byRep[r]);

  return (
    <Chapter id="test" num="Parables · 2" title="Can the method place a story?">
      <Why course="week 5 (ten nearest neighbours against ten random ones), week 7 (a held-out labelled test set)"
        what={<>We held {c.queries} religious retellings of well-known tale types out of the network: medieval sermon stories, Buddhist birth stories and the like, each labelled with its ATU tale type. For each one we asked whether a folktale of the <em>same</em> type is among its {c.k} nearest folktales.</>}
        why={<>If the method cannot find the folktale relatives of stories whose type we already know, it cannot tell us anything about parables. This is the test that earns it the right to answer the question.</>} />
      <div className="controls-row"><RepToggle /></div>
      <div className="two-col">
        <div className="game" aria-live="polite">
          <span className="label">Your turn · round {played.length + (chosen ? 0 : 1)} · {it.collection}</span>
          <p className="opening">“{it.opening}”</p>
          <p className="sans small" style={{ margin: "0 0 8px" }}><strong>{it.title}</strong>. Which tale type is this?</p>
          <div className="options">
            {round.options.map((o) => {
              const cls = chosen ? (o === it.atuName ? "option right" : o === chosen ? "option wrong" : "option") : "option";
              return <button key={o} type="button" className={cls} disabled={!!chosen} onClick={() => setAnswers((a) => ({ ...a, [at]: o }))}>{shortType(o, 90)}</button>;
            })}
          </div>
          {chosen && (
            <div className="sans" style={{ marginTop: 14, fontSize: 14.5 }}>
              <p style={{ marginBottom: 6 }}>{chosen === it.atuName ? "Right." : "Not quite."} It is <strong>ATU {it.atu} {shortType(it.atuName, 90)}</strong>, and {it.sameType} folktale{it.sameType === 1 ? "" : "s"} of that type are in the network. <ReadLinks story={d} atu={it.atu} title={it.title} /></p>
              <p style={{ margin: 0 }}>{rank <= c.k
                ? <>With {REP_NAME[rep]}, the method found one as the <strong>{rank === 1 ? "very nearest" : `${ordinal(rank)} nearest`}</strong> folktale.</>
                : <>With {REP_NAME[rep]}, the method missed: the nearest folktale of this type is only the {ordinal(rank)}.</>}</p>
              <span className="label" style={{ marginTop: 12 }}>Where it landed: its {c.k} nearest folktales</span>
              <NearList story={d} items={items} sameType={it.atu} onPair={(k) => setPair(pair === k ? null : k)} pairOpen={pair} />
              {pair !== null && <PairCard story={d} near={near} left={{ kind: "retelling", id: it.id }} right={items[pair].i} cosine={items[pair].cos} words={items[pair].words} onClose={() => setPair(null)} />}
              <button type="button" className="btn primary" style={{ marginTop: 12 }} onClick={() => { setAt((a) => a + 1); setPair(null); }}>Next story →</button>
            </div>
          )}
          <div className="score">
            <span>You: <strong>{you} of {played.length}</strong></span>
            <span>The method (same type within {c.k} nearest): <strong>{mapHits} of {played.length}</strong></span>
          </div>
        </div>
        <div>
          <div className="tiles">
            <div className="tile"><div className="v">{pct(c.byRep[rep].recall)}</div><div className="l">found a same-type folktale among the {c.k} nearest (95% CI {pct(c.byRep[rep].low)}–{pct(c.byRep[rep].high)}), {REP_NAME[rep]}</div></div>
            <div className="tile"><div className="v">{pct(c.chance, 1)}</div><div className="l">expected by chance with {c.k} random folktales</div></div>
            <div className="tile"><div className="v">{pct(c.byRep[rep].vote)}</div><div className="l">neighbours vote for the right type (chance {pct(c.voteChance, 2)})</div></div>
          </div>
          <BarList label="Recall by representation" items={reps.map((r) => ({ label: REP_NAME[r] ?? r, value: c.byRep[r].recall }))} max={1} format={(v) => pct(v)} />
          <DataTable head={["Retelling", "Tale type", "Rank, TF–IDF", "Rank, embeddings"]} caption="All 36 retellings"
            rows={c.items.map((x) => [x.title, `ATU ${x.atu}`, x.ranks.tfidf, x.ranks.embedding])} />
        </div>
      </div>
      <Result>
        <p>The method passes. For {c.hits} of the {c.queries} retellings a folktale of the same type is among the {c.k} nearest with TF–IDF: {pct(c.recall)}, about {Math.round(c.recall / c.chance)} times what chance gives. It still works with every noun masked ({pct(c.other.tfidf_nouns_masked)}), so it is not only matching names of animals and kings. None of the retellings has a copy among the folktales: the most similar one reaches a cosine of {c.maxCosine.toFixed(2)}.</p>
      </Result>
    </Chapter>
  );
}
