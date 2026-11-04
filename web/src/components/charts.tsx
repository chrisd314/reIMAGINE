import { useMemo } from "react";
import { bin, extent, max, scaleLinear, scaleSqrt, geoPath } from "d3";
import type { FeatureCollection, Geometry } from "geojson";
import { worldProjection } from "../lib/geo";
import { WORLD_H, WORLD_W } from "./NetworkCanvas";
import { fmt, int } from "../lib/format";

/** Saved label-shuffle reference (histogram) with the observed value and an optional single shuffled draw. */
export function NullHistogram({ values, observed, draw, width = 320, height = 86, colour = "#2d6a6a", label, domain }: {
  values: number[]; observed: number; draw?: number | null; width?: number; height?: number; colour?: string; label: string; domain?: [number, number];
}) {
  const m = { l: 8, r: 8, t: 8, b: 22 };
  const [lo, hi] = domain ?? (() => { const e = extent([...values, observed, ...(draw != null ? [draw] : [])]) as [number, number]; const pad = (e[1] - e[0]) * 0.08 || 0.01; return [e[0] - pad, e[1] + pad] as [number, number]; })();
  const x = scaleLinear().domain([lo, hi]).range([m.l, width - m.r]);
  const bins = useMemo(() => bin().domain([lo, hi]).thresholds(36)(values), [values, lo, hi]);
  const y = scaleLinear().domain([0, max(bins, (b) => b.length) ?? 1]).range([height - m.b, m.t]);
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${label}: observed ${fmt(observed)}; ${values.length} label shuffles range ${fmt(Math.min(...values))} to ${fmt(Math.max(...values))}${draw != null ? `; one shuffled draw ${fmt(draw)}` : ""}`}>
      {bins.map((b, k) => (
        <rect key={k} x={x(b.x0!)} y={y(b.length)} width={Math.max(0, x(b.x1!) - x(b.x0!) - 0.6)} height={height - m.b - y(b.length)} fill="#b9b2a5" />
      ))}
      <line x1={x(observed)} x2={x(observed)} y1={m.t - 2} y2={height - m.b} stroke={colour} strokeWidth={2.5} />
      <text x={Math.min(x(observed) + 4, width - 70)} y={m.t + 9} fontSize={10.5} fontFamily="Inter Variable, sans-serif" fill={colour} fontWeight={650}>observed {fmt(observed)}</text>
      {draw != null && (
        <g>
          <circle cx={x(draw)} cy={height - m.b - 6} r={5} fill="#e8a33d" stroke="#1d2b33" strokeWidth={1} />
          <text x={x(draw)} y={height - m.b - 14} fontSize={10} textAnchor="middle" fontFamily="Inter Variable, sans-serif" fill="#7a4a0a">one draw</text>
        </g>
      )}
      <line x1={m.l} x2={width - m.r} y1={height - m.b} y2={height - m.b} stroke="#c9bda6" />
      {x.ticks(4).map((t) => (
        <text key={t} x={x(t)} y={height - 6} fontSize={9.5} textAnchor="middle" fill="#6b767c" fontFamily="Inter Variable, sans-serif">{t.toFixed(2)}</text>
      ))}
    </svg>
  );
}

export function BarList({ items, colour = "#2d6a6a", max: maxV, format = int, onClick, selected }: {
  items: { label: string; value: number; colour?: string; note?: string }[]; colour?: string; max?: number; format?: (v: number) => string;
  onClick?: (label: string) => void; selected?: string | null;
}) {
  const mx = maxV ?? Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="sans" style={{ fontSize: 13 }}>
      {items.map((it) => (
        <div key={it.label} style={{ display: "grid", gridTemplateColumns: "minmax(110px, 38%) 1fr auto", gap: 8, alignItems: "center", margin: "3px 0" }}>
          {onClick ? <button className="btn small ghost" style={{ border: 0, padding: 0, justifyContent: "flex-start", fontWeight: selected === it.label ? 700 : 400 }} onClick={() => onClick(it.label)}>{it.label}</button>
            : <span style={{ color: "var(--ink-2)" }}>{it.label}</span>}
          <div style={{ background: "var(--paper-3)", height: 10, borderRadius: 3, overflow: "hidden" }} aria-hidden>
            <div style={{ width: `${(it.value / mx) * 100}%`, height: "100%", background: it.colour ?? colour }} />
          </div>
          <span style={{ fontVariantNumeric: "tabular-nums", color: "var(--ink-2)", minWidth: 42, textAlign: "right" }}>{format(it.value)}{it.note && <span className="muted"> {it.note}</span>}</span>
        </div>
      ))}
    </div>
  );
}

export function Funnel({ steps }: { steps: { label: string; value: number; note: string }[] }) {
  const mx = steps[0]?.value ?? 1;
  return (
    <ol className="sans" style={{ listStyle: "none", padding: 0, margin: 0, fontSize: 13.5 }}>
      {steps.map((s, k) => (
        <li key={s.label} style={{ display: "grid", gridTemplateColumns: "minmax(140px, 28%) 1fr", gap: 12, alignItems: "center", margin: "6px 0" }}>
          <div>
            <div style={{ fontWeight: 650 }}>{s.label}</div>
            <div className="muted small">{s.note}</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: `${(s.value / mx) * 100}%`, minWidth: 6, height: 22, background: k === 4 ? "var(--accent)" : "var(--ink)", opacity: 1 - k * 0.1, borderRadius: 4 }} />
            <span style={{ fontFamily: "var(--serif)", fontSize: 18, fontWeight: 600 }}>{int(s.value)}</span>
          </div>
        </li>
      ))}
    </ol>
  );
}

export interface MapPoint { lat: number; lon: number; count: number; label: string; colour?: string; approximate?: boolean }

/** One map point per distinct coordinate; labels sharing a point (e.g. communities recorded in the USA) are listed together. */
export function pointsByCoordinate(rows: { lat: number | null; lon: number | null; place: string | null; region: string | null }[], colourOf: (region: string | null) => string): MapPoint[] {
  const m = new Map<string, MapPoint & { labels: Map<string, number> }>();
  rows.forEach((r) => {
    if (r.lat == null || r.lon == null) return;
    const key = `${r.lat},${r.lon}`;
    const p = m.get(key) ?? { lat: r.lat, lon: r.lon, count: 0, label: "", colour: colourOf(r.region), approximate: true, labels: new Map<string, number>() };
    p.count++;
    p.labels.set(r.place ?? "?", (p.labels.get(r.place ?? "?") ?? 0) + 1);
    m.set(key, p);
  });
  return [...m.values()].map(({ labels, ...p }) => ({ ...p, label: [...labels.entries()].sort((a, b) => b[1] - a[1]).map(([l, n]) => (labels.size > 1 ? `${l} (${n})` : l)).join(", ") }));
}

/** SVG map: documented representative points sized by tale count. */
export function CoverageMap({ land, points, highlight, lines, height = 360, onPoint }: {
  land: FeatureCollection<Geometry> | null; points: MapPoint[]; highlight?: string[]; lines?: { a: [number, number]; b: [number, number] }[];
  height?: number; onPoint?: (p: MapPoint) => void;
}) {
  const proj = useMemo(() => worldProjection(), []);
  const path = useMemo(() => geoPath(proj), [proj]);
  const r = scaleSqrt().domain([1, Math.max(...points.map((p) => p.count), 1)]).range([2.5, 18]);
  const hl = new Set(highlight ?? []);
  return (
    <svg viewBox={`0 0 ${WORLD_W} ${WORLD_H}`} width="100%" style={{ maxHeight: height }} role="img"
      aria-label={`Map of ${points.length} documented representative points; circle size shows the number of tales.`}>
      <path d={path({ type: "Sphere" } as never) ?? ""} fill="#eef0ea" />
      {land && <path d={path(land) ?? ""} fill="#ddd3bf" stroke="#c6b99e" strokeWidth={0.6} />}
      {lines?.map((l, k) => {
        const a = proj([l.a[1], l.a[0]]), b = proj([l.b[1], l.b[0]]);
        if (!a || !b) return null;
        const mx = (a[0] + b[0]) / 2, my = Math.min(a[1], b[1]) - Math.abs(a[0] - b[0]) * 0.18 - 10;
        return <path key={k} d={`M${a[0]},${a[1]} Q${mx},${my} ${b[0]},${b[1]}`} fill="none" stroke="#e8a33d" strokeWidth={2.5} strokeDasharray="6 4" />;
      })}
      {[...points].sort((p, q) => q.count - p.count).map((p) => {
        const xy = proj([p.lon, p.lat]);
        if (!xy) return null;
        const on = hl.has(p.label);
        return (
          <g key={p.label} transform={`translate(${xy[0]},${xy[1]})`} style={{ cursor: onPoint ? "pointer" : "default" }} onClick={() => onPoint?.(p)}>
            <circle r={r(p.count) + (on ? 4 : 0)} fill={p.colour ?? "#2d6a6a"} fillOpacity={on ? 0.95 : 0.62} stroke={on ? "#1d2b33" : "#fffaf2"} strokeWidth={on ? 2.5 : 0.8} />
            <title>{`${p.label}: ${p.count} tale${p.count === 1 ? "" : "s"}${p.approximate ? " (approximate representative point)" : ""}`}</title>
          </g>
        );
      })}
    </svg>
  );
}
