import { useEffect, useMemo, useRef, useState } from "react";

// "Shuffle it yourself": every click reruns the null model in the browser and adds the result to a histogram, next to
// the observed value. This is the permutation logic of the course (week 2; week 3 label shuffles), made visible.

export function ShuffleLab({ observed, runOne, label, unit = "", pipeline, reset, digits = 3 }: {
  observed: number; runOne: () => number; label: string; unit?: string; pipeline?: string; reset: string; digits?: number;
}) {
  const [values, setValues] = useState<number[]>([]);
  const run = useRef(runOne);
  run.current = runOne;
  useEffect(() => { setValues([]); }, [reset]);
  const add = (n: number) => setValues((v) => { const out = [...v]; for (let k = 0; k < n; k++) out.push(run.current()); return out; });

  const W = 520, H = 170, L = 10, R = 10, T = 12, B = 30, bins = 30;
  const { lo, hi, counts, max } = useMemo(() => {
    const all = values.length ? [...values, observed] : [observed];
    let lo = Math.min(...all), hi = Math.max(...all);
    if (hi - lo < 1e-9) { lo -= 0.01; hi += 0.01; }
    const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
    const counts = new Array(bins).fill(0);
    values.forEach((v) => { counts[Math.min(bins - 1, Math.max(0, Math.floor(((v - lo) / (hi - lo)) * bins)))] += 1; });
    return { lo, hi, counts, max: Math.max(1, ...counts) };
  }, [values, observed]);
  const x = (v: number) => L + (W - L - R) * (v - lo) / (hi - lo);
  const atLeast = values.filter((v) => v >= observed).length;
  const p = values.length ? (1 + atLeast) / (1 + values.length) : null;
  const mean = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
  return (
    <div className="shufflelab">
      <div className="row">
        <button type="button" className="btn primary" onClick={() => add(1)}>Shuffle once</button>
        <button type="button" className="btn" onClick={() => add(100)}>Shuffle 100 times</button>
        <button type="button" className="btn" onClick={() => setValues([])} disabled={!values.length}>Start again</button>
        <span className="sans small muted">{values.length} shuffle{values.length === 1 ? "" : "s"}</span>
      </div>
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`${label}: ${values.length} shuffled values and the observed value`}>
        {counts.map((c, k) => c > 0 && (
          <rect key={k} x={L + ((W - L - R) * k) / bins + 0.5} width={(W - L - R) / bins - 1} y={T + (H - T - B) * (1 - c / max)} height={(H - T - B) * c / max} fill="var(--c2)" opacity={0.75} rx={1} />
        ))}
        <line x1={x(observed)} x2={x(observed)} y1={T - 4} y2={H - B} stroke="var(--c1)" strokeWidth={2.5} />
        <text x={x(observed)} y={T - 2} className="tick" textAnchor={x(observed) > W - 120 ? "end" : "start"} dx={x(observed) > W - 120 ? -5 : 5}>observed {observed.toFixed(digits)}{unit}</text>
        <line className="axis" x1={L} x2={W - R} y1={H - B} y2={H - B} />
        {[lo + (hi - lo) * 0.1, (lo + hi) / 2, hi - (hi - lo) * 0.1].map((v) => <text key={v} className="tick" x={x(v)} y={H - B + 15} textAnchor="middle">{v.toFixed(digits)}</text>)}
        <text className="tick" x={(L + W - R) / 2} y={H - 2} textAnchor="middle">{label}</text>
      </svg>
      <p className="sans small" style={{ margin: "4px 0 0" }}>
        {values.length === 0 ? <>Press <em>Shuffle</em>: each shuffle breaks the link being tested and recomputes the value. The orange bars are what chance gives; the blue line is what we observed.</>
          : <>Your {values.length} shuffles average {mean!.toFixed(digits)}{unit}; {atLeast} reach the observed value, so p ≈ {p!.toFixed(values.length >= 99 ? 3 : 2)}.</>}
        {pipeline ? <span className="muted"> {pipeline}</span> : null}
      </p>
    </div>
  );
}
