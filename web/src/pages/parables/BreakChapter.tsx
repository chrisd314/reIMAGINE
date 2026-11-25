import { useState } from "react";
import type { Rep, Story } from "../../data";
import { RepToggle, useRep } from "../../components/rep";
import { Chapter, DataTable, Result, Why } from "../../components/ui";
import { fmt, list, pval, signed } from "../../lib/format";

export const HEADLINE = "tfidf (headline)";
export const CHECKS: { id: string; label: string; note: string; match: (v: string) => boolean }[] = [
  { id: "embedding", label: "Meaning instead of words", note: "sentence embeddings (MiniLM) instead of TF–IDF word weights", match: (v) => v === "embedding" },
  { id: "length", label: "Equal length", note: "longer texts look more folk-like; compare at equal length (regression)", match: (v) => v === "tfidf, regression at equal length" },
  { id: "nouns", label: "Nouns masked", note: "every noun and name removed before measuring", match: (v) => v === "tfidf_nouns_masked" },
  { id: "names", label: "Names and old formulae masked", note: "names and translators' formulae (“thou”, “verily”) removed", match: (v) => v === "tfidf, names and formulae masked" },
  { id: "hubs", label: "Hubs removed", note: "the folktales that are everybody's neighbour taken out", match: (v) => v === "tfidf, hubs removed" },
  { id: "graphs", label: "Other ways to build the graph", note: "density 5% and 15%, k-nearest-neighbour graphs with k = 5, 10, 20", match: (v) => v.startsWith("tfidf, communities of") },
];

/** Whether a tradition's parables are closer than its baseline under a check (every variant of the check must agree). */
export function holds(d: Story, tradition: string, match: (v: string) => boolean): boolean {
  const rows = d.robust.filter((r) => r.tradition === tradition && match(r.variant));
  return rows.length > 0 && rows.every((r) => r.closer);
}

function LengthChart({ d, rep }: { d: Story; rep: Rep }) {
  const rows = d.traditions.map((t) => d.byRep[rep].lengthControl.find((c) => c.tradition === t)!).filter(Boolean);
  const lo = Math.min(...rows.map((r) => r.low)) * 1.1, hi = 0.005;
  const W = 420, L = 84, R = 60, rowH = 28, H = rows.length * rowH + 30;
  const x = (v: number) => L + (W - L - R) * (v - lo) / (hi - lo);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Parables minus folktale excerpts of the same length">
      <line className="axis" x1={x(0)} x2={x(0)} y1={4} y2={rows.length * rowH + 4} strokeWidth={1.5} />
      <text className="tick" x={x(0)} y={H - 6} textAnchor="end">as folk-like as a folktale excerpt</text>
      {rows.map((r, k) => {
        const y = 4 + k * rowH + rowH / 2;
        return (
          <g key={r.tradition}>
            <text x={L - 10} y={y + 4} textAnchor="end" fontSize={13}>{r.tradition}</text>
            <line x1={x(r.low)} x2={x(r.high)} y1={y} y2={y} stroke="var(--c1)" strokeWidth={3} />
            <circle cx={x(r.diff)} cy={y} r={5} fill="var(--c1)" />
            <text className="tick" x={W - R + 6} y={y + 4}>{signed(r.diff)}</text>
          </g>
        );
      })}
    </svg>
  );
}

export function BreakChapter({ d }: { d: Story }) {
  const { rep } = useRep();
  const [on, setOn] = useState<string[]>([]);
  const [cell, setCell] = useState<{ id: string; label: string; t: string; match: (v: string) => boolean } | null>(null);
  const active = CHECKS.filter((c) => on.includes(c.id));
  const standing = d.traditions.filter((t) => holds(d, t, (v) => v === HEADLINE) && active.every((c) => holds(d, t, c.match)));
  const L = d.length;
  const minP = Math.min(...L.matching.map((m) => m.p));
  const diffs = d.byRep[rep].lengthControl.map((c) => c.diff);
  const cellRows = cell ? d.robust.filter((r) => r.tradition === cell.t && cell.match(r.variant)) : [];

  return (
    <Chapter id="break" num="Parables · 6" title="Trying to break it">
      <Why course="week 8 (compare against a null, against another method), week 4 (graph construction), week 6 (names out)"
        what={<>We re-ran the comparison of section 3 under every sceptical objection we could think of, each with the same permutation test within tradition.</>}
        why={<>A result that hangs on one choice (the way words are counted, how long the texts are, which links make the graph) is a weak result. What survives every check is what we report as the answer.</>} />

      <div className="two-col flip">
        <div className="panel">
          <span className="label">Switch on the sceptic's checks</span>
          {CHECKS.map((c) => (
            <label key={c.id} className="toggle">
              <input type="checkbox" checked={on.includes(c.id)} onChange={() => setOn((o) => (o.includes(c.id) ? o.filter((x) => x !== c.id) : [...o, c.id]))} />
              <span>{c.label}<small>{c.note}</small></span>
            </label>
          ))}
          <div className="row" style={{ marginTop: 10 }}>
            <button type="button" className="btn" onClick={() => setOn(CHECKS.map((c) => c.id))}>All checks</button>
            <button type="button" className="btn" onClick={() => setOn([])}>None</button>
          </div>
        </div>
        <figure className="figure">
          <p className="figure-title">Are the parables still closer to folktales than their baseline?</p>
          <div className="table-wrap">
            <table className="matrix">
              <thead><tr><th>Check</th>{d.traditions.map((t) => <th key={t}>{t}</th>)}</tr></thead>
              <tbody>
                {[{ id: "h", label: "Section 3 (TF–IDF)", match: (v: string) => v === HEADLINE }, ...active].map((c) => (
                  <tr key={c.id}><td>{c.label}</td>{d.traditions.map((t) => {
                    const ok = holds(d, t, c.match), sel = cell?.id === c.id && cell.t === t;
                    return <td key={t} className={`${ok ? "mark-yes" : "mark-no"}${sel ? " sel" : ""}`}><button type="button" className="cell-btn" aria-label={`${c.label}, ${t}: ${ok ? "closer" : "not closer"}; show the numbers`} aria-pressed={sel}
                      onClick={() => setCell(sel ? null : { id: c.id, label: c.label, t, match: c.match })}>{ok ? "✓" : "·"}</button></td>;
                  })}</tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="survivors" aria-live="polite">Still standing: {standing.length ? list(standing) : "no tradition"}</p>
          <p className="caption">✓ parables closer than their own non-story passages (one-sided permutation test, p &lt; 0.05); · not distinguishable. Click a cell for its numbers.</p>
          {cell && (
            <div className="card" style={{ marginTop: 8 }}>
              <div className="tag">{cell.t} · {cell.label}</div>
              <table className="data"><thead><tr><th>Variant</th><th className="n">Parables − baseline</th><th className="n">p</th><th className="n">Closer?</th></tr></thead>
                <tbody>{cellRows.map((r) => <tr key={r.variant}><td>{r.variant}</td><td className="n">{signed(r.diff)}</td><td className="n">{pval(r.p, d.settings.permutations)}</td><td className="n">{r.closer ? "yes" : "no"}</td></tr>)}</tbody></table>
            </div>
          )}
        </figure>
      </div>

      <div className="two-col even" style={{ marginTop: 22 }}>
        <figure className="figure">
          <div className="controls-row"><RepToggle /></div>
          <p className="figure-title">Parables against folktale excerpts of the same length</p>
          <p className="figure-sub">Median difference in folk-closeness, 95% interval</p>
          <LengthChart d={d} rep={rep} />
          <DataTable head={["Tradition", "Parable words (median)", "Baseline words (median)", "Mann-Whitney p"]} rows={L.matching.map((m) => [m.tradition, m.par, m.base, fmt(m.p, 2)])} caption="Are the baselines length-matched?" />
        </figure>
        <div>
          <p>Longer texts have more chances to share words, so closeness rises with length. Two answers to that: the baseline passages were cut to the parables' length (no tradition differs, Mann-Whitney p ≥ {fmt(minP, 2)}), and we compared every parable with folktale excerpts of its own length.</p>
          <p>Against same-length excerpts, every tradition's parables come out less folk-like ({signed(Math.min(...diffs))} to {signed(Math.max(...diffs))}). At equal length the order of traditions barely moves: {L.orderEqual}.</p>
          <span className="label" style={{ marginTop: 16 }}>Every check at a glance</span>
          <ul className="answer-list" style={{ gap: 6 }}>
            {d.table1.map((r) => (
              <li key={r.check} className="sans small"><span className={`chip ${r.holds}`}>{r.holds}</span> <strong>{r.check}</strong>: {r.agreement} verdicts agree <span className="muted">({r.variant})</span></li>
            ))}
          </ul>
        </div>
      </div>

      <Result>
        <p>With every check on, <strong>{list(d.traditions.filter((t) => holds(d, t, (v) => v === HEADLINE) && CHECKS.every((c) => holds(d, t, c.match))))}</strong> still stand. {list(d.traditions.filter((t) => !holds(d, t, (v) => v === HEADLINE) || !CHECKS.every((c) => holds(d, t, c.match))))} fall at one check or more, so we report them as fragile. Switch the checks on one at a time to see which one each tradition falls at.</p>
      </Result>
    </Chapter>
  );
}
