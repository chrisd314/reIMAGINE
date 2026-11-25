import { useCallback, useMemo, useState } from "react";
import type { Near, Rep, Story, Text } from "../../data";
import { TextPanel } from "../../components/panels";
import { RepToggle, useRep } from "../../components/rep";
import { ShuffleLab } from "../../components/ShuffleLab";
import { Chapter, DataTable, Result, Tooltip, useNarrow, Why, type Tip } from "../../components/ui";
import { fmt, hash01, int, list, pval, signed } from "../../lib/format";
import { median, rng, shuffled } from "../../lib/stats";

export function TraditionPicker({ d, value, onChange, all = true }: { d: Story; value: string; onChange: (t: string) => void; all?: boolean }) {
  return (
    <div className="segmented" role="group" aria-label="Tradition">
      {(all ? ["all", ...d.traditions] : d.traditions).map((t) => (
        <button key={t} type="button" aria-pressed={value === t} onClick={() => onChange(t)}>{t === "all" ? "All five" : t}</button>
      ))}
    </div>
  );
}

function Strip({ d, rep, trad, picked, onPick }: { d: Story; rep: Rep; trad: string; picked: string; onPick: (id: string) => void }) {
  const [tip, setTip] = useState<Tip | null>(null);
  const narrow = useNarrow();
  const band = d.byRep[rep].folkBand;
  const vals = d.texts.map((t) => t.rep[rep].closeness);
  const lo = Math.min(...vals), hi = Math.max(band.q75, ...vals);
  const W = narrow ? 400 : 760, L = narrow ? 64 : 84, R = 10, T = 8, rowH = narrow ? 62 : 56, H = T + rowH * d.traditions.length + 34;
  const x = (v: number) => L + (W - L - R) * (v - lo) / (hi - lo);
  const step = (hi - lo) > 0.4 ? 0.1 : 0.05;
  const ticks: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) ticks.push(+t.toFixed(2));
  return (
    <>
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Folk-closeness of every parable and baseline passage, by tradition" onPointerLeave={() => setTip(null)}>
        <rect x={x(band.q25)} width={x(band.q75) - x(band.q25)} y={T} height={rowH * d.traditions.length} fill="var(--c3)" opacity={0.14} />
        <line x1={x(band.q50)} x2={x(band.q50)} y1={T} y2={T + rowH * d.traditions.length} stroke="var(--c3)" strokeWidth={1.5} />
        {ticks.map((t) => <g key={t}><line className="axis" x1={x(t)} x2={x(t)} y1={T} y2={T + rowH * d.traditions.length} strokeDasharray="2 4" /><text className="tick" x={x(t)} y={H - 18} textAnchor="middle">{t.toFixed(2)}</text></g>)}
        <text className="tick" x={L + (W - L - R) / 2} y={H - 2} textAnchor="middle">{narrow ? "folk-closeness →" : `folk-closeness: mean cosine to the ${d.settings.closenessK} nearest folktales →`}</text>
        {d.traditions.map((tr, k) => {
          const y0 = T + k * rowH, faded = trad !== "all" && trad !== tr;
          const items = d.texts.filter((t) => t.tradition === tr);
          const med = (kind: string) => median(items.filter((t) => t.kind === kind).map((t) => t.rep[rep].closeness));
          return (
            <g key={tr} opacity={faded ? 0.25 : 1}>
              <text x={L - 8} y={y0 + rowH / 2 + 4} textAnchor="end" fontSize={narrow ? 12 : 13}>{tr}</text>
              {items.map((t) => {
                const cy = y0 + (t.kind === "parable" ? 0.3 : 0.72) * rowH + (hash01(t.id) - 0.5) * rowH * 0.32;
                return <circle key={t.id} cx={x(t.rep[rep].closeness)} cy={cy} r={t.id === picked ? 6 : 3.4}
                  fill={t.kind === "parable" ? "var(--c1)" : "var(--c2)"} fillOpacity={t.id === picked ? 1 : 0.62}
                  stroke={t.id === picked ? "var(--ink)" : "none"} strokeWidth={1.5} style={{ cursor: "pointer" }}
                  onClick={() => onPick(t.id)}
                  onPointerMove={(ev) => setTip({ x: ev.clientX, y: ev.clientY, body: <><strong>{t.title}</strong><br />{t.kind === "parable" ? "parable" : "non-story passage"} · {fmt(t.rep[rep].closeness, 3)}<br />click to read it beside its nearest folktales</> })} />;
              })}
              {(["parable", "baseline"] as const).map((kind) => {
                const m = med(kind), yy = y0 + (kind === "parable" ? 0.3 : 0.72) * rowH;
                return Number.isNaN(m) ? null : <line key={kind} x1={x(m)} x2={x(m)} y1={yy - 11} y2={yy + 11} stroke="var(--ink)" strokeWidth={2.5} />;
              })}
            </g>
          );
        })}
      </svg>
      <Tooltip tip={tip} />
    </>
  );
}

function Forest({ d, rep }: { d: Story; rep: Rep }) {
  const rows = d.traditions.map((t) => d.byRep[rep].headline.find((h) => h.tradition === t)!).filter(Boolean);
  const lo = Math.min(0, ...rows.map((r) => r.low)), hi = Math.max(...rows.map((r) => r.high));
  const W = 420, L = 84, R = 70, rowH = 30, H = rows.length * rowH + 30;
  const x = (v: number) => L + (W - L - R) * (v - lo) / (hi - lo);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Parables minus baseline, median folk-closeness with 95% interval">
      <line className="axis" x1={x(0)} x2={x(0)} y1={4} y2={rows.length * rowH + 4} strokeWidth={1.5} />
      <text className="tick" x={x(0)} y={H - 6} textAnchor="middle">0 = same as baseline</text>
      {rows.map((r, k) => {
        const y = 4 + k * rowH + rowH / 2;
        return (
          <g key={r.tradition}>
            <text x={L - 10} y={y + 4} textAnchor="end" fontSize={13}>{r.tradition}</text>
            <line x1={x(r.low)} x2={x(r.high)} y1={y} y2={y} stroke={r.closer ? "var(--c1)" : "var(--neutral)"} strokeWidth={3} />
            <circle cx={x(r.diff)} cy={y} r={5} fill={r.closer ? "var(--c1)" : "var(--neutral)"} />
            <text className="tick" x={W - R + 6} y={y + 4}>{signed(r.diff)}</text>
          </g>
        );
      })}
    </svg>
  );
}

/** The permutation test of the headline, run in the browser: parable/passage labels shuffled within one tradition. */
function PermutationLab({ d, rep, trad, setTrad }: { d: Story; rep: Rep; trad: string; setTrad: (t: string) => void }) {
  const t = trad === "all" ? d.traditions[0] : trad;
  const items = useMemo(() => d.texts.filter((x) => x.tradition === t), [d, t]);
  const vals = useMemo(() => items.map((x) => x.rep[rep].closeness), [items, rep]);
  const isPar = useMemo(() => items.map((x) => x.kind === "parable"), [items]);
  const stat = (lab: boolean[]) => median(vals.filter((_, k) => lab[k])) - median(vals.filter((_, k) => !lab[k]));
  const observed = stat(isPar);
  const rand = useMemo(() => rng(20261118), [t, rep]);   // eslint-disable-line react-hooks/exhaustive-deps
  const runOne = useCallback(() => stat(shuffled(isPar, rand)), [isPar, rand, vals]);   // eslint-disable-line react-hooks/exhaustive-deps
  const h = d.byRep[rep].headline.find((x) => x.tradition === t);
  return (
    <figure className="figure">
      <p className="figure-title">Is it chance? Shuffle the labels yourself</p>
      <p className="figure-sub">Each shuffle hands the “parable” and “non-story” labels of {t} at random to the same {items.length} texts and recomputes the difference of medians</p>
      <div className="controls-row"><TraditionPicker d={d} value={t} onChange={setTrad} all={false} /></div>
      <ShuffleLab observed={observed} runOne={runOne} reset={`${rep}-${t}`} label={`${t}: median of parables minus median of passages`}
        pipeline={h ? `The pipeline's ${int(d.settings.permutations)} shuffles: ${pval(h.p, d.settings.permutations)}.` : undefined} />
    </figure>
  );
}

export function PlaceChapter({ d, near, trad, setTrad }: { d: Story; near: Near | null; trad: string; setTrad: (t: string) => void }) {
  const { rep } = useRep();
  const best = useMemo(() => [...d.texts].filter((t) => t.kind === "parable").sort((a, b) => b.rep[rep].closeness - a.rep[rep].closeness)[0], [d, rep]);
  const [picked, setPicked] = useState(best.id);
  const choose = (t: string) => {
    setTrad(t);
    if (t !== "all") {
      const top = d.texts.filter((x) => x.tradition === t && x.kind === "parable").sort((a, b) => b.rep[rep].closeness - a.rep[rep].closeness)[0];
      if (top) setPicked(top.id);
    }
  };
  const text: Text = d.texts.find((t) => t.id === picked) ?? best;
  const H = d.byRep[rep].headline, perm = d.settings.permutations, band = d.byRep[rep].folkBand;
  const closer = H.filter((h) => h.closer).sort((a, b) => b.diff - a.diff);
  const notCloser = H.filter((h) => !h.closer).map((h) => h.tradition);
  const below = H.filter((h) => h.par < band.q25).length;

  return (
    <Chapter id="place" num="Parables · 3" title="Are parables closer to folktales than their own scripture?">
      <Why course="week 5 (cosine similarity, nearest neighbours), week 2 (permutation test, p = (1 + k)/(1 + N))"
        what={<>We placed {int(d.corpus.parables)} parables from five traditions among the folktales, together with {int(d.corpus.baseline)} non-story passages cut from the very same translations, matched in length. A text's <em>folk-closeness</em> is its mean similarity to its {d.settings.closenessK} nearest folktales.</>}
        why={<>Old translations share one voice: “thou” and “thee”, kings and servants. Any text from those books would look a little folk-like for that reason alone. Comparing each tradition's parables with non-story text from its own book takes that voice out, so what remains is the story.</>} />
      <div className="controls-row"><RepToggle /><TraditionPicker d={d} value={trad} onChange={choose} /></div>
      <div className="two-col">
        <figure className="figure">
          <p className="figure-title">Every text, by how folk-like it is</p>
          <p className="figure-sub">
            <i className="swatch" style={{ background: "var(--c1)" }} /> parables (upper row) · <i className="swatch" style={{ background: "var(--c2)" }} /> non-story passages (lower row) · <i className="swatch" style={{ background: "var(--c3)" }} /> band: folktales compared with each other (middle half) · black ticks: medians · click a dot to read it
          </p>
          <Strip d={d} rep={rep} trad={trad} picked={picked} onPick={setPicked} />
        </figure>
        <figure className="figure">
          <p className="figure-title">Parables minus their baseline</p>
          <p className="figure-sub">Median difference in folk-closeness, 95% bootstrap interval</p>
          <Forest d={d} rep={rep} />
          <DataTable head={["Tradition", "Parables", "Baseline", "Difference", "p"]} rows={H.map((h) => [h.tradition, fmt(h.par, 3), fmt(h.base, 3), signed(h.diff), pval(h.p, perm)])} />
        </figure>
      </div>
      <div className="two-col even" style={{ marginTop: 18 }}>
        <TextPanel story={d} near={near} rep={rep} t={text} />
        <PermutationLab d={d} rep={rep} trad={trad} setTrad={setTrad} />
      </div>
      <Result>
        <p><strong>{list(closer.map((h) => h.tradition))}</strong> parables sit closer to folktales than non-story text from their own translations ({closer.map((h) => `${h.tradition} ${signed(h.diff)}, ${pval(h.p, perm)}`).join("; ")}; {rep === "tfidf" ? "TF–IDF" : "embeddings"}). For {list(notCloser)} we cannot tell parables from their baseline. Switch the representation to see which verdicts change.</p>
        <p>Even so, {below === H.length ? "every tradition's" : `${below} of ${H.length} traditions'`} parables stay below the band of folktales compared with each other: parables lean towards folktales, they do not read like them.</p>
      </Result>
    </Chapter>
  );
}
