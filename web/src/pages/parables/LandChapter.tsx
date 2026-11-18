import { useCallback, useMemo, useState } from "react";
import { communityOf, shortType, type Cell, type Near, type Network, type Story } from "../../data";
import { NetCanvas, type Rings, type Tone } from "../../components/NetCanvas";
import { TalePanel, TextPanel } from "../../components/panels";
import { RepToggle, useRep } from "../../components/rep";
import { Chapter, DataTable, Result, Why } from "../../components/ui";
import { fmt, list, pct, points, pval } from "../../lib/format";
import { TraditionPicker } from "./PlaceChapter";

function Bars({ cells, selected, onPick }: { cells: Cell[]; selected: string | null; onPick: (c: string) => void }) {
  const W = 440, L = 140, R = 50, bh = 9, gap = 9, H = cells.length * (2 * bh + gap) + 8;
  const max = Math.max(...cells.flatMap((c) => [c.par, c.base, c.map])) * 1.05;
  const x = (v: number) => L + (W - L - R) * v / max;
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Share of links to each community, parables against baseline; click a community to see its texts">
      {cells.map((c, k) => {
        const y = 4 + k * (2 * bh + gap), sel = c.community === selected;
        return (
          <g key={c.community} onClick={() => onPick(c.community)} style={{ cursor: "pointer" }} role="button" tabIndex={0} aria-pressed={sel}
            onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onPick(c.community); }}>
            <rect x={0} y={y - 3} width={W} height={2 * bh + 6} rx={4} fill={sel ? "var(--paper-3)" : "transparent"} />
            <text x={L - 8} y={y + bh + 3} textAnchor="end" fontSize={12.5} fontWeight={sel ? 700 : 400}>{c.community === "small" ? "small groups" : `${c.community} ${c.words.split(" ").slice(0, 2).join(" ")}`}</text>
            <rect x={L} y={y} width={x(c.par) - L} height={bh} fill="var(--c1)" rx={1.5} />
            <rect x={L} y={y + bh + 1} width={x(c.base) - L} height={bh} fill="var(--c2)" rx={1.5} />
            <line x1={x(c.map)} x2={x(c.map)} y1={y - 2} y2={y + 2 * bh + 3} stroke="var(--ink)" strokeWidth={1.4} />
            <text className="tick" x={Math.max(x(c.par), x(c.base), x(c.map)) + 6} y={y + bh + 3}>{points(c.excess)}{c.sig ? " *" : ""}</text>
          </g>
        );
      })}
    </svg>
  );
}

export function LandChapter({ d, net, near, trad, setTrad }: { d: Story; net: Network; near: Near | null; trad: string; setTrad: (t: string) => void }) {
  const { rep } = useRep();
  const map = net.maps[rep], R = d.byRep[rep];
  const fallback = [...R.headline].sort((a, b) => b.diff - a.diff)[0].tradition;
  const t = trad === "all" ? fallback : trad;
  const h = R.headline.find((x) => x.tradition === t)!;
  const cells = R.cells.filter((c) => c.tradition === t);
  const types = (kind: string) => R.types.filter((x) => x.tradition === t && x.kind === kind).sort((a, b) => a.rank - b.rank).slice(0, 5);
  const perm = d.settings.permutations, K = d.settings.attachK;
  const [comm, setComm] = useState<string | null>(null);
  const [type, setType] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [tale, setTale] = useState<number | null>(null);
  const focusComm = comm ?? h.topCommunity;

  const rings = useMemo<Rings[]>(() => (["parable", "baseline"] as const).map((kind, j) => {
    const counts = new Map<number, number>();
    d.texts.filter((x) => x.tradition === t && x.kind === kind).forEach((x) => x.rep[rep].nearest.slice(0, K).forEach((i) => counts.set(i, (counts.get(i) ?? 0) + 1)));
    return { counts, tone: (j + 1) as Tone };
  }), [d, t, rep, K]);
  const tone = useCallback((i: number): Tone => (communityOf(map.group[i]) === focusComm ? 3 : 0), [map, focusComm]);
  const F = d.folktales;
  const tip = (i: number) => {
    const p = rings[0].counts.get(i) ?? 0, b = rings[1].counts.get(i) ?? 0;
    return <><strong>{F.title[i]}</strong><br />{F.atu[i] ? `ATU ${F.atu[i]} ${shortType(F.atuName[i], 70)}` : "no tale type"} · {communityOf(map.group[i])}<br />near {p} {t} parable{p === 1 ? "" : "s"}, {b} baseline passage{b === 1 ? "" : "s"}<br /><em>click to read it</em></>;
  };
  const differs = R.headline.filter((x) => x.differs).map((x) => x.tradition);
  const topWords = cells.find((c) => c.community === h.topCommunity)?.words.split(" ").slice(0, 3).join(", ");
  const inComm = comm ? d.texts.filter((x) => x.tradition === t && x.rep[rep].community === comm) : [];
  const forType = type ? d.texts.filter((x) => x.tradition === t && x.kind === "parable" && x.rep[rep].voted === type) : [];
  const shown = comm ? inComm : forType;
  const openText = open ? d.texts.find((x) => x.id === open) : undefined;

  return (
    <Chapter id="land" num="Parables · 4" title="Where do they land?">
      <Why course="week 4 (communities), week 3 (label shuffles)"
        what={<>Each text's {K} nearest folktales vote for their communities and tale types. For each tradition we compare where its parables' votes go with where its own non-story passages' votes go, shuffling the parable/passage label {perm.toLocaleString("en-GB")} times within the tradition.</>}
        why={<>Being close to folktales in general is one thing; the question is also <em>which</em> folktales. If parables reach a community their scripture's other text does not, that community tells us what kind of story they resemble.</>} />
      <div className="controls-row"><RepToggle /><TraditionPicker d={d} value={t} onChange={(x) => { setTrad(x); setComm(null); setType(null); setOpen(null); }} all={false} /></div>
      <div className="two-col">
        <figure className="figure">
          <p className="figure-title">The neighbours of {t} texts in the network</p>
          <NetCanvas map={map} tone={tone} rings={rings} tip={tip} aspect={0.62} selected={tale} onPick={setTale}
            label={`Folktale network with rings on the nearest folktales of ${t} parables and baseline passages`} />
          <div className="legend" aria-hidden>
            <span><i className="swatch" style={{ border: "2px solid var(--c1)" }} />near {t} parables</span>
            <span><i className="swatch" style={{ border: "2px solid var(--c2)" }} />near non-story passages</span>
            <span><i className="swatch" style={{ background: "var(--c3)" }} />community {focusComm}</span>
          </div>
          <p className="caption">Ring size grows with the number of texts that have the folktale among their {K} nearest. Click a ring to read that folktale.</p>
          {tale !== null && <TalePanel story={d} map={map} near={near} rep={rep} i={tale} onSelect={setTale} onClose={() => setTale(null)} />}
        </figure>
        <figure className="figure">
          <p className="figure-title">Share of links per community</p>
          <p className="figure-sub"><i className="swatch" style={{ background: "var(--c1)" }} /> parables · <i className="swatch" style={{ background: "var(--c2)" }} /> baseline · black tick: share of the whole network · * significant after Bonferroni · click a community</p>
          <Bars cells={cells} selected={comm} onPick={(c) => { setComm(comm === c ? null : c); setType(null); setOpen(null); }} />
          <DataTable head={["Community", "Parables", "Baseline", "Network", "Excess", "p"]} rows={cells.map((c) => [c.community, pct(c.par), pct(c.base), pct(c.map), points(c.excess), fmt(c.p, 3)])} />
        </figure>
      </div>

      <div className="two-col even" style={{ marginTop: 18 }}>
        {(["parable", "baseline"] as const).map((kind) => (
          <div key={kind} className="card">
            <div className="tag">Tale types their neighbours vote for · {kind === "parable" ? `${t} parables (click one)` : "non-story passages"}</div>
            <ol className="sans" style={{ margin: 0, paddingLeft: 20, fontSize: 14 }}>
              {types(kind).map((x) => (
                <li key={x.atu}>{kind === "parable"
                  ? <button type="button" className="linklike" onClick={() => { setType(type === x.atu ? null : x.atu); setComm(null); setOpen(null); }}>ATU {x.atu} {shortType(x.name, 70)}</button>
                  : <>ATU {x.atu} {shortType(x.name, 70)}</>} <span className="muted">{pct(x.share)}</span></li>
              ))}
            </ol>
          </div>
        ))}
      </div>
      {(comm || type) && (
        <div className="two-col even" style={{ marginTop: 18 }}>
          <div className="card">
            <div className="tag">{comm ? `${t} texts whose neighbours sit mostly in ${comm}` : `${t} parables whose neighbours vote for ATU ${type}`} · {shown.length}</div>
            <ul className="sans small" style={{ margin: 0, paddingLeft: 18 }}>
              {shown.map((x) => <li key={x.id}><button type="button" className="linklike" onClick={() => setOpen(x.id)}>{x.title}</button><span className="muted"> · {x.kind === "parable" ? "parable" : "non-story"}</span></li>)}
              {shown.length === 0 && <li className="muted">none</li>}
            </ul>
          </div>
          {openText && <TextPanel story={d} near={near} rep={rep} t={openText} onSelectTale={setTale} />}
        </div>
      )}
      <Result>
        <p><strong>{t}</strong> parables lean towards community {h.topCommunity} ({topWords}): {points(h.topExcess)} of their links compared with their baseline{h.topSig ? ", significant after correction for the number of communities" : ", which does not survive correction for the number of communities"}. Their whole mix of communities {h.differs ? "differs" : "does not differ"} from the baseline's ({fmt(h.jsd, 3)} bits against {fmt(h.jsdNull, 3)} under shuffling, {pval(h.jsdP, perm)}).</p>
        <p>Across the five traditions, {list(differs)} land in a different mix of communities than their own non-story text does ({rep === "tfidf" ? "TF–IDF" : "embeddings"}).</p>
      </Result>
    </Chapter>
  );
}
