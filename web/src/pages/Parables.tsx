import { useEffect, useMemo, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import { useData } from "../data/load";
import type { Route } from "../lib/router";
import { ErrorState, HowMade, Loading, Segmented } from "../components/ui";
import { fmt, int } from "../lib/format";

// Results of the paper pipeline (python -m ouaw.run, then python -m ouaw.site): the folklore map of
// 1,462 folktales and 281 religious parables placed on it. Data file: parables.json.

type Rep = "tfidf" | "embedding";
interface Community { name: string; size: number; words: string[]; types: string; regions: string }
interface TvrRow { observed: number; nullMean: number; nullMin: number; nullMax: number; assort: number }
interface MapData {
  x: number[]; y: number[]; group: number[]; linked: number[]; edges: number[]; communities: Community[];
  stats: { edges: number; threshold: number; modularity: number; nullMean: number; nullSd: number; shuffles: number;
    communities: number; major: number; seedNmiMin: number; seedNmiMax: number; n: number };
  typeVsRegion: { atu_type: TvrRow; region: TvrRow };
}
interface TextItem {
  id: string; kind: "parable" | "baseline"; tradition: string; title: string; tokens: number; source: string; translator: string;
  year: string; url: string; opening: string; note: string;
  closeness: Partial<Record<Rep, number>>; rank: Partial<Record<Rep, number | null>>; nearest: Record<Rep, number[]>; cos: Record<Rep, number[]>;
}
interface TradRow {
  tradition: string; rank: number; n_parables: number; median: number; ci_low: number; ci_high: number; baseline_median: number | null;
  minus_baseline_median: number | null; minus_baseline_ci_low: number | null; minus_baseline_ci_high: number | null; percentile_among_folktales: number;
}
interface Cell { tradition: string; community: string; share: number; expected: number; diff: number; sig: boolean; links: number }
interface PerRep {
  traditions: TradRow[]; folktales: { q05: number; q25: number; q50: number; q75: number; q95: number }; cells: Cell[];
  variants: { variant: string; tradition: string; median: number; rank: number }[];
}
interface Cal { recall: number; low: number; high: number; chance: number; hits: number; queries: number; recall1: number }
interface Pair { tradition: string; title: string; folktale: string; atu: string; cosine: number; parableOpening: string; folktaleOpening: string }
// The headline test (parables against non-story text of the same translation; label shuffled within the tradition)
interface HCell { tradition: string; community: string; par: number; base: number; diff: number; sig: boolean }
interface HTrad { tradition: string; diff: number; low: number; high: number; p: number; closer: boolean; differs: boolean; jsdP: number }
interface Payload {
  built: string; commit: string; primary: Rep; traditions: string[];
  headline: Record<Rep, { cells: HCell[]; traditions: HTrad[] }>;
  corpus: { folktales: number; calibration: number; typed: number; types: number; both: number; regions: number; parables: number; baseline: number };
  folktales: { id: string[]; title: string[]; atu: string[]; atuName: string[]; region: string[] };
  maps: Record<Rep, MapData>; texts: TextItem[]; perRep: Record<Rep, PerRep>;
  checks: {
    gate: { passed: boolean; rule: string }; calibration: Record<string, Cal>;
    queries: { title: string; collection: string; atu: string; sameType: number; tfidf: number; embedding: number }[];
    second: { spearman: number; jaccard: number; sameNearest: number; noShared: number };
    length: Record<Rep, number>; hubs: Record<Rep, { top10Share: number; never: number; first: string; firstShare: number }>;
    topPairs: Record<Rep, Pair[]>; hand: { status: string };
  };
}

const REP_NAME: Record<Rep, string> = { tfidf: "TF–IDF", embedding: "embeddings" };
const COMMUNITY = ["#2f5f8f", "#c0632f", "#3d7a3d", "#8a5aa8", "#b07d2b", "#4c8a8a", "#5e4425", "#a33a3a", "#d9952b"];
const SMALL = "#c9bda6";
const PARABLE = "#2d6a6a";
const BASELINE = "#b4532a";
const commColour = (g: number) => (g < 0 ? SMALL : COMMUNITY[g % COMMUNITY.length]);
const pc = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${Math.round(v * 100)}%`);
const signed = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v)}`;

function hexToRgb(h: string): [number, number, number] { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }
function mix(a: string, b: string, t: number) {
  const [r1, g1, b1] = hexToRgb(a), [r2, g2, b2] = hexToRgb(b);
  return `rgb(${Math.round(r1 + (r2 - r1) * t)}, ${Math.round(g1 + (g2 - g1) * t)}, ${Math.round(b1 + (b2 - b1) * t)})`;
}
function quantile(values: number[], q: number) { const s = [...values].sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.max(0, Math.round(q * (s.length - 1))))]; }
function hash01(s: string) { let h = 2166136261; for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return ((h >>> 0) % 1000) / 1000; }
function niceTicks(lo: number, hi: number, n = 6) {
  const step0 = (hi - lo) / n, mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map((k) => k * mag).find((k) => k >= step0) ?? step0;
  const out: number[] = []; for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(6));
  return out;
}

interface Tip { x: number; y: number; html: ReactNode }
function Tooltip({ tip }: { tip: Tip | null }) {
  if (!tip) return null;
  return <div className="sans small" role="status" style={{ position: "fixed", left: Math.min(tip.x + 14, window.innerWidth - 300), top: tip.y + 16, zIndex: 40, pointerEvents: "none",
    background: "#fffaf2", border: "1px solid var(--rule)", borderRadius: 6, padding: "7px 10px", maxWidth: 290, boxShadow: "var(--shadow)" }}>{tip.html}</div>;
}

/* ---------------------------------------------------------------- the map */
type Focus = { type: "community"; g: number } | { type: "tradition"; t: string } | null;

function FolkMap({ data, rep, focus, setTip }: { data: Payload; rep: Rep; focus: Focus; setTip: (t: Tip | null) => void }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const pts = useRef<[number, number, number][]>([]);
  const [width, setWidth] = useState(700);
  useEffect(() => {
    const el = canvas.current?.parentElement; if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth)); ro.observe(el); setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);
  const m = data.maps[rep];
  const counts = useMemo(() => {
    const c = new Map<number, number>();
    if (focus?.type === "tradition") data.texts.filter((t) => t.kind === "parable" && t.tradition === focus.t)
      .forEach((t) => t.nearest[rep].forEach((i) => c.set(i, (c.get(i) ?? 0) + 1)));
    return c;
  }, [data, rep, focus]);
  useEffect(() => {
    const cv = canvas.current; if (!cv) return;
    const w = width, h = Math.max(300, Math.min(Math.round(w * 0.78), 620)), dpr = window.devicePixelRatio || 1;
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); cv.style.height = `${h}px`;
    const ctx = cv.getContext("2d"); if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, w, h);
    const idx = m.x.map((_, i) => i).filter((i) => m.linked[i]);
    const xs = idx.map((i) => m.x[i]), ys = idx.map((i) => m.y[i]);
    const x0 = quantile(xs, 0.004), x1 = quantile(xs, 0.996), y0 = quantile(ys, 0.004), y1 = quantile(ys, 0.996);
    const pad = 14, s = Math.min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0));
    const ox = (w - s * (x1 - x0)) / 2, oy = (h - s * (y1 - y0)) / 2;
    const px = (i: number) => ox + (m.x[i] - x0) * s, py = (i: number) => oy + (y1 - m.y[i]) * s;
    ctx.strokeStyle = "#6b767c"; ctx.globalAlpha = 0.06; ctx.lineWidth = 0.6; ctx.beginPath();
    for (let k = 0; k < m.edges.length; k += 2) { ctx.moveTo(px(m.edges[k]), py(m.edges[k])); ctx.lineTo(px(m.edges[k + 1]), py(m.edges[k + 1])); }
    ctx.stroke();
    const order = [...idx].sort((a, b) => Number(m.group[b] < 0) - Number(m.group[a] < 0));
    for (const i of order) {
      const dim = focus?.type === "community" && m.group[i] !== focus.g;
      ctx.globalAlpha = dim ? 0.12 : focus?.type === "tradition" ? 0.35 : 0.9;
      ctx.fillStyle = commColour(m.group[i]); ctx.beginPath(); ctx.arc(px(i), py(i), 2.1, 0, 2 * Math.PI); ctx.fill();
    }
    ctx.globalAlpha = 1;
    if (focus?.type === "tradition") {
      ctx.strokeStyle = "#1d2b33"; ctx.lineWidth = 1.3;
      counts.forEach((c, i) => { if (!m.linked[i]) return; ctx.beginPath(); ctx.arc(px(i), py(i), 2.5 + 2.2 * Math.sqrt(c), 0, 2 * Math.PI); ctx.stroke(); });
    }
    pts.current = idx.map((i) => [px(i), py(i), i]);
  }, [m, width, focus, counts]);
  const F = data.folktales;
  const onMove = (ev: ReactPointerEvent<HTMLCanvasElement>) => {
    const r = ev.currentTarget.getBoundingClientRect(), x = ev.clientX - r.left, y = ev.clientY - r.top;
    let best = -1, bd = 100;
    for (const [px, py, i] of pts.current) { const d = (px - x) ** 2 + (py - y) ** 2; if (d < bd) { bd = d; best = i; } }
    if (best < 0) { setTip(null); return; }
    const g = m.group[best];
    setTip({ x: ev.clientX, y: ev.clientY, html: <><strong>{F.title[best]}</strong><br />{F.atu[best] ? `ATU ${F.atu[best]} ${F.atuName[best]}` : "no tale type"}<br />{F.region[best] || "no region"} · {g < 0 ? "small group" : `community C${g + 1}`}{focus?.type === "tradition" && counts.get(best) ? <><br />near {counts.get(best)} {focus.t} parable{counts.get(best) === 1 ? "" : "s"}</> : null}</> });
  };
  const shown = m.linked.reduce((a, b) => a + b, 0);
  return (
    <div>
      <canvas ref={canvas} style={{ display: "block", width: "100%", borderRadius: 6, background: "#fffaf2" }} onPointerMove={onMove} onPointerLeave={() => setTip(null)}
        role="img" aria-label={`Network map of ${int(shown)} folktales coloured by community`} />
      <p className="small sans muted" style={{ marginTop: 6 }}>{int(shown)} of {int(m.linked.length)} folktales, placed by the whole similarity network; each tale's 5 strongest links drawn. Hover a dot to see the tale.</p>
    </div>
  );
}

/* ---------------------------------------------------------------- closeness chart */
function ClosenessChart({ data, rep, setTip }: { data: Payload; rep: Rep; setTip: (t: Tip | null) => void }) {
  const P = data.perRep[rep], fb = P.folktales;
  const ord = [...P.traditions].sort((a, b) => a.rank - b.rank);
  const items = data.texts.filter((t) => t.closeness[rep] !== undefined);
  const vals = [...items.map((t) => t.closeness[rep] as number), fb.q25, fb.q75];
  const lo = Math.min(...vals), hi = Math.max(...vals), padv = (hi - lo) * 0.05;
  const W = 900, H = 430, L = 58, R = 12, T = 14, B = 46;
  const y = (v: number) => T + (H - T - B) * (1 - (v - (lo - padv)) / (hi - lo + 2 * padv));
  const cw = (W - L - R) / ord.length, cx = (k: number) => L + cw * (k + 0.5);
  const F = data.folktales;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Folk-closeness of every parable, by tradition" style={{ fontFamily: "var(--sans)" }}
      onPointerLeave={() => setTip(null)}>
      {niceTicks(lo - padv, hi + padv).map((t) => <g key={t}><line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="#e3d8c4" /><text x={L - 8} y={y(t) + 4} textAnchor="end" fontSize={12} fill="#6b767c">{t}</text></g>)}
      <rect x={L} width={W - L - R} y={y(fb.q75)} height={y(fb.q25) - y(fb.q75)} fill="#e3d8c4" opacity={0.75} />
      <line x1={L} x2={W - R} y1={y(fb.q50)} y2={y(fb.q50)} stroke="#6b767c" strokeWidth={1.2} />
      <text x={W - R - 4} y={y(fb.q50) - 6} textAnchor="end" fontSize={12} fill="#6b767c">folktales to each other</text>
      {ord.map((row, k) => {
        const base = items.filter((t) => t.kind === "baseline" && t.tradition === row.tradition).map((t) => t.closeness[rep] as number).sort((a, b) => a - b);
        const q = (p: number) => base[Math.round(p * (base.length - 1))];
        return (
          <g key={row.tradition}>
            {base.length > 0 && <>
              <rect x={cx(k) + cw * 0.24} width={cw * 0.1} y={y(q(0.75))} height={Math.max(2, y(q(0.25)) - y(q(0.75)))} fill={BASELINE} opacity={0.4} />
              <line x1={cx(k) + cw * 0.2} x2={cx(k) + cw * 0.38} y1={y(q(0.5))} y2={y(q(0.5))} stroke={BASELINE} strokeWidth={3} />
            </>}
            {items.filter((t) => t.kind === "parable" && t.tradition === row.tradition).map((t) => {
              const n = t.nearest[rep][0];
              return <circle key={t.id} cx={cx(k) - cw * 0.1 + (hash01(t.id) - 0.5) * cw * 0.34} cy={y(t.closeness[rep] as number)} r={3.6} fill={PARABLE} fillOpacity={0.6} style={{ cursor: "pointer" }}
                onPointerMove={(ev) => setTip({ x: ev.clientX, y: ev.clientY, html: <><strong>{t.title}</strong><br />{t.tradition} · closeness {fmt(t.closeness[rep])}<br />nearest folktale: {F.title[n]}{F.atu[n] ? ` (ATU ${F.atu[n]})` : ""}</> })} />;
            })}
            <line x1={cx(k) - cw * 0.1} x2={cx(k) - cw * 0.1} y1={y(row.ci_low)} y2={y(row.ci_high)} stroke="#1d2b33" strokeWidth={1.4} />
            <line x1={cx(k) - cw * 0.32} x2={cx(k) + cw * 0.12} y1={y(row.median)} y2={y(row.median)} stroke="#1d2b33" strokeWidth={3} />
            <text x={cx(k)} y={H - B + 20} textAnchor="middle" fontSize={13} fill="#1d2b33">{row.tradition}</text>
            <text x={cx(k)} y={H - B + 36} textAnchor="middle" fontSize={12} fill="#6b767c">n = {row.n_parables}</text>
          </g>
        );
      })}
      <text transform={`translate(14 ${(H - B) / 2}) rotate(-90)`} textAnchor="middle" fontSize={12} fill="#6b767c">folk-closeness ({REP_NAME[rep]})</text>
    </svg>
  );
}

/* ---------------------------------------------------------------- placement against the baseline */
function Placement({ data, rep }: { data: Payload; rep: Rep }) {
  const H = data.headline[rep], m = data.maps[rep];
  const ord = [...H.traditions].sort((a, b) => b.diff - a.diff).map((t) => t.tradition);
  const cols = m.communities.map((c) => c.name).filter((n) => H.cells.some((c) => c.community === n));
  const max = Math.max(0.05, ...H.cells.map((c) => Math.abs(c.diff)));
  const cell = (tr: string, cn: string) => H.cells.find((c) => c.tradition === tr && c.community === cn) as HCell;
  return (
    <div className="table-wrap">
      <table className="data" style={{ minWidth: 640 }}>
        <thead><tr><th />{cols.map((cn) => { const c = m.communities.find((x) => x.name === cn); return <th key={cn} className="num" style={{ textAlign: "center" }}>{cn}<br /><span className="muted" style={{ fontWeight: 400 }}>{cn === "small" ? "groups" : c?.words.slice(0, 2).join(" ")}</span></th>; })}</tr></thead>
        <tbody>
          {ord.map((tr) => (
            <tr key={tr}><th scope="row" style={{ position: "static" }}>{tr}</th>
              {cols.map((cn) => {
                const c = cell(tr, cn);
                if (!c) return <td key={cn} className="num muted">–</td>;
                const v = Math.round(c.diff * 100), t = 0.85 * Math.min(1, Math.abs(c.diff) / max);
                return <td key={cn} className="num" style={{ textAlign: "center", background: mix("#fffaf2", c.diff >= 0 ? PARABLE : BASELINE, t), color: t > 0.55 ? "#fff" : "var(--ink)", fontWeight: c.sig ? 650 : 400 }}
                  title={`${tr} → ${cn}: parables ${pc(c.par)} of links, baseline ${pc(c.base)}`}>{v === 0 ? "0" : signed(v)}{c.sig ? "*" : ""}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------------------------------------------------------------- the page */
export function Parables({ route, navigate }: { route: Route; navigate: (path: string, params?: Record<string, string | null | undefined>, replace?: boolean) => void }) {
  const d = useData<Payload>("parables.json");
  const rep: Rep = route.params.rep === "embedding" ? "embedding" : "tfidf";
  const setRep = (r: Rep) => navigate("/parables", { ...route.params, rep: r === "tfidf" ? null : r }, true);
  const [focus, setFocus] = useState<Focus>(null);
  const [tip, setTip] = useState<Tip | null>(null);
  const [q, setQ] = useState("");
  const [trad, setTrad] = useState("all");
  const [kind, setKind] = useState<"parable" | "baseline">("parable");
  const [sort, setSort] = useState("desc");
  if (d.error) return <div className="page"><ErrorState message={d.error} /></div>;
  if (!d.data) return <div className="page"><Loading what="parables" /></div>;
  const data = d.data, m = data.maps[rep], P = data.perRep[rep], C = data.checks, F = data.folktales;
  const ord = [...P.traditions].sort((a, b) => a.rank - b.rank);
  const tvr = m.typeVsRegion;
  const H = data.headline[rep];
  const hOf = (t: string) => H.traditions.find((x) => x.tradition === t);
  const closer = [...H.traditions].sort((a, b) => b.diff - a.diff).filter((t) => t.closer).map((t) => t.tradition);
  const notCloser = [...H.traditions].sort((a, b) => b.diff - a.diff).filter((t) => !t.closer).map((t) => t.tradition);
  const leans = H.traditions.filter((t) => t.differs).map((t) => {
    const top = H.cells.filter((c) => c.tradition === t.tradition).sort((a, b) => b.diff - a.diff)[0];
    const info = m.communities.find((c) => c.name === top?.community);
    return top ? `${t.tradition}: ${top.community} (${info?.words.slice(0, 2).join(", ") ?? ""}) ${signed(Math.round(top.diff * 100))}` : t.tradition;
  });
  const pos = H.cells.filter((c) => c.sig && c.diff > 0).sort((a, b) => b.diff - a.diff);
  const cal = C.calibration[rep];
  const collections = Object.entries(C.queries.reduce<Record<string, number>>((acc, q) => { acc[q.collection] = (acc[q.collection] ?? 0) + 1; return acc; }, {}))
    .sort((a, b) => b[1] - a[1]).map(([k, v]) => `${v} ${k}`);
  const andList = (xs: string[]) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs[xs.length - 1]}`);

  let rows = data.texts.filter((t) => t.kind === kind && (trad === "all" || t.tradition === trad) && t.closeness[rep] !== undefined);
  const ql = q.trim().toLowerCase();
  if (ql) rows = rows.filter((t) => `${t.title} ${t.opening} ${t.nearest[rep].map((i) => F.title[i]).join(" ")}`.toLowerCase().includes(ql));
  const cmp: Record<string, (a: TextItem, b: TextItem) => number> = {
    desc: (a, b) => (b.closeness[rep] as number) - (a.closeness[rep] as number), asc: (a, b) => (a.closeness[rep] as number) - (b.closeness[rep] as number),
    trad: (a, b) => a.tradition.localeCompare(b.tradition) || (b.closeness[rep] as number) - (a.closeness[rep] as number), len: (a, b) => b.tokens - a.tokens };
  rows = [...rows].sort(cmp[sort]);
  const allC = data.texts.map((t) => t.closeness[rep]).filter((v): v is number => v !== undefined);
  const cLo = Math.min(...allC, P.folktales.q50), cHi = Math.max(...allC, P.folktales.q50);
  const w = (v: number) => `${(100 * (v - cLo) / (cHi - cLo)).toFixed(1)}%`;
  const variants = [...new Set(P.variants.map((v) => v.variant))];
  const queries = [...C.queries].sort((a, b) => a[rep] - b[rep]);
  const rankChip = (v: number) => <span className={`chip${v <= 10 ? " ok" : ""}`} style={{ minWidth: 34, justifyContent: "center" }}>{v > data.corpus.folktales ? "–" : v}</span>;

  return (
    <div className="page">
      <Tooltip tip={tip} />
      <div className="prose-wide">
        <p className="kicker-sc" style={{ margin: "0 0 4px" }}>The parables explorer</p>
        <h1 style={{ fontSize: "clamp(2rem, 4vw, 3rem)" }}>Religious parables on the map of folklore</h1>
        <p style={{ fontSize: "1.15rem" }}><strong>Do parables from different religious traditions sit inside folktale communities more than non-story text from the same translations does, and which folktale communities and tale types do they land in?</strong> The <a href="#/">overview</a> gives the answer in brief; here you can check it parable by parable.</p>
        <p>We built a text-similarity network of {int(data.corpus.folktales)} folktales, then compared {int(data.corpus.parables)} parables with every folktale: {ord.map((t) => `${t.n_parables} ${t.tradition}`).join(", ")}. Each tradition is compared with {int(data.corpus.baseline)} non-story passages cut from the same translations, so that a translator's style cannot pass for a folktale. The map itself never changes when parables are added.</p>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "center", margin: "18px 0 6px" }}>
        <span className="sans small muted">Text representation</span>
        <Segmented<Rep> label="Text representation" value={rep} onChange={setRep} options={[
          { value: "tfidf", label: "TF–IDF (shared words)", title: "Primary: found more known parallels" },
          { value: "embedding", label: "Embeddings (meaning)", title: "Second method" }]} />
        <span className="sans small muted">TF–IDF is the primary method: it found more known parallels ({fmt(C.calibration.tfidf.recall, 2)} against {fmt(C.calibration.embedding.recall, 2)}).</span>
      </div>

      <div className="grid-2" style={{ gap: 12, margin: "14px 0 8px" }}>
        <div className="callout neutral"><strong>{closer.length ? <>Closer to folktales than their own baseline: {andList(closer)}.</> : <>No tradition is closer to folktales than its own baseline.</>}</strong> {notCloser.length > 0 && <>Not closer: {andList(notCloser)}. </>}Parable/baseline label shuffled within each tradition ({REP_NAME[rep]}).</div>
        <div className="callout neutral">{leans.length ? <><strong>Where parables lean, against their baseline:</strong> {leans.join("; ")} percentage points of links.</> : <strong>No tradition's community profile differs from its baseline's.</strong>}</div>
        <div className="callout neutral"><strong>Folklore groups by tale type {tvr.atu_type.observed - tvr.atu_type.nullMean > tvr.region.observed - tvr.region.nullMean ? "more than" : "no more than"} by region.</strong> NMI with tale type {fmt(tvr.atu_type.observed, 2)}, with region {fmt(tvr.region.observed, 2)}; {tvr.atu_type.observed > tvr.atu_type.nullMax && tvr.region.observed > tvr.region.nullMax ? "both above every shuffle" : "see the shuffle ranges below"}.</div>
        <div className="callout neutral"><strong>The method finds known parallels.</strong> For {cal.hits} of {cal.queries} religious retellings with a known tale type, a folktale of that type is among the 10 nearest (chance: about {Math.round(cal.chance * cal.queries)}).</div>
      </div>

      {/* ---------------- map */}
      <section style={{ marginTop: 40 }}>
        <h2>The map of world folklore</h2>
        <p className="prose">{int(data.corpus.folktales)} folktales, each linked to the ones it resembles most: the top 10% of all pairs by cosine similarity ({int(m.stats.edges)} links). Louvain finds {m.stats.major} communities with at least 1% of the tales. Click a community to pick it out, or a tradition to see which folktales its parables are nearest to.</p>
        <div className="grid-main-side" style={{ "--side": "340px" } as CSSProperties}>
          <FolkMap data={data} rep={rep} focus={focus} setTip={setTip} />
          <div className="sans" style={{ display: "grid", gap: 16 }}>
            <div>
              <h4>Communities</h4>
              <div style={{ display: "grid", gap: 2, fontSize: 13 }}>
                {m.communities.map((c) => {
                  const g = c.name === "small" ? -1 : Number(c.name.slice(1)) - 1;
                  const on = focus?.type === "community" && focus.g === g;
                  return (
                    <button key={c.name} type="button" className="btn small ghost" aria-pressed={on} title={c.types}
                      onClick={() => setFocus(on ? null : { type: "community", g })}
                      style={{ justifyContent: "flex-start", gap: 8, border: 0, background: on ? "var(--paper-3)" : "transparent", textAlign: "left" }}>
                      <span style={{ width: 10, height: 10, borderRadius: "50%", background: commColour(g), flex: "none" }} />
                      <strong style={{ minWidth: 24 }}>{c.name === "small" ? "" : c.name}</strong>
                      <span style={{ flex: 1 }}>{c.name === "small" ? "groups under 1% of the map" : c.words.slice(0, 3).join(", ")}</span>
                      <span className="muted">{c.size}</span>
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <h4>Where each tradition's parables link</h4>
              <p className="small muted" style={{ margin: "0 0 8px" }}>Rings mark the folktales among each parable's 5 nearest; bigger rings, more parables.</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {data.traditions.map((t) => {
                  const on = focus?.type === "tradition" && focus.t === t;
                  return <button key={t} type="button" className={`btn small${on ? " primary" : ""}`} aria-pressed={on} onClick={() => setFocus(on ? null : { type: "tradition", t })}>{t}</button>;
                })}
              </div>
            </div>
            <div>
              <h4>Tale type or region?</h4>
              <p className="small muted" style={{ margin: "0 0 8px" }}>Agreement (NMI) between the communities and each label, on the {int(m.stats.n)} tales that have both. Grey: range of 1,000 shuffles of the label.</p>
              {(["atu_type", "region"] as const).map((k) => {
                const r = tvr[k], mx = Math.max(tvr.atu_type.observed, tvr.region.observed) * 1.2, x = (v: number) => `${(100 * v / mx).toFixed(1)}%`;
                return (
                  <div key={k} style={{ display: "grid", gridTemplateColumns: "72px 1fr 40px", gap: 8, alignItems: "center", fontSize: 13, margin: "6px 0" }}>
                    <span>{k === "atu_type" ? "Tale type" : "Region"}</span>
                    <div style={{ position: "relative", height: 16 }}>
                      <span style={{ position: "absolute", left: 0, right: 0, top: 8, height: 1, background: "var(--rule)" }} />
                      <span style={{ position: "absolute", top: 3, height: 10, left: x(r.nullMin), width: `calc(${x(r.nullMax)} - ${x(r.nullMin)} + 2px)`, background: "#6b767c", opacity: 0.55, borderRadius: 2 }} />
                      <span style={{ position: "absolute", top: 2, width: 12, height: 12, marginLeft: -6, left: x(r.observed), borderRadius: "50%", background: PARABLE }} />
                    </div>
                    <span style={{ fontVariantNumeric: "tabular-nums" }}>{fmt(r.observed, 2)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        <HowMade
          measured={<>Cosine similarity between folktale texts ({REP_NAME[rep]}); communities by weighted Louvain (seed 42) on the 10%-density graph.</>}
          records={<>{int(data.corpus.folktales)} folktales: the corpus without the 36 versions from religious collections, which are used as test queries below.</>}
          method={<>Modularity {fmt(m.stats.modularity)} against {fmt(m.stats.nullMean)} ± {fmt(m.stats.nullSd, 4)} in {m.stats.shuffles} degree-preserving shuffles (week 4); three seeds agree with NMI {fmt(m.stats.seedNmiMin, 2)}–{fmt(m.stats.seedNmiMax, 2)}; NMI and assortativity against 1,000 label shuffles.</>}
          infer={<>The communities split along tale type far more than along region. Assortativity, which counts every link equally, is higher for region ({fmt(tvr.region.assort)} against {fmt(tvr.atu_type.assort)}): neighbours often share a region, but the large groups follow type.</>}
          cannot={<>Where stories came from or how they travelled. The corpus is {int(data.corpus.folktales)} English versions, mostly European.</>} />
      </section>

      {/* ---------------- closeness */}
      <section style={{ marginTop: 48 }}>
        <h2>How folktale-like is each tradition?</h2>
        <p className="prose">Folk-closeness of a text is its mean cosine similarity to its 5 nearest folktales. Each dot is one parable. The orange bar is non-story teaching text from the same translation, cut to the same lengths: closeness that comes only from a translator's style shows up there as well.</p>
        <ClosenessChart data={data} rep={rep} setTip={setTip} />
        <div className="legend sans small" style={{ display: "flex", flexWrap: "wrap", gap: "6px 18px", margin: "6px 0 14px" }}>
          <span className="item"><span className="swatch" style={{ background: PARABLE, borderRadius: "50%" }} />parable</span>
          <span className="item"><span className="swatch" style={{ background: "#1d2b33", height: 3 }} />tradition median and 95% interval</span>
          <span className="item"><span className="swatch" style={{ background: BASELINE, opacity: 0.6 }} />non-story text, same translation (middle half and median)</span>
          <span className="item"><span className="swatch" style={{ background: "#e3d8c4" }} />folktales against each other (middle half and median)</span>
        </div>
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Rank</th><th>Tradition</th><th className="num">Parables</th><th className="num">Median [95% interval]</th><th className="num">Same-translation baseline</th><th className="num">Parables minus baseline [95% interval]</th><th className="num">Permutation</th><th className="num">Percentile among folktales</th></tr></thead>
            <tbody>{ord.map((t) => {
              const h = hOf(t.tradition);
              return (
                <tr key={t.tradition}><td>{t.rank}</td><td>{t.tradition}</td><td className="num">{t.n_parables}</td><td className="num">{fmt(t.median)} [{fmt(t.ci_low)}, {fmt(t.ci_high)}]</td>
                  <td className="num">{fmt(t.baseline_median)}</td>
                  <td className="num">{h ? `${h.diff >= 0 ? "+" : ""}${fmt(h.diff)} [${fmt(h.low)}, ${fmt(h.high)}]` : "–"}</td>
                  <td className="num">{h ? <span className={`chip${h.closer ? " ok" : ""}`}>{h.p < 0.001 ? "p < 0.001" : `p = ${fmt(h.p)}`}</span> : "–"}</td>
                  <td className="num">{Math.round(t.percentile_among_folktales)}</td></tr>
              );
            })}
            </tbody>
          </table>
        </div>
        <ul className="prose sans" style={{ fontSize: 14 }}>
          <li>Every tradition sits well below how close folktales are to each other (median {fmt(P.folktales.q50)}).</li>
          <li>{closer.length ? <>Closer to folktales than non-story text of the same translation (green p: one-sided, 1,000 shuffles of the parable/baseline label within the tradition): {andList(closer)}. For the others, closeness may be the translator's style.</> : <>No tradition is closer than non-story text of the same translation.</>}</li>
          <li>Longer texts score higher (Spearman {fmt(C.length[rep], 2)} between closeness and length). The baselines are cut to the parables' lengths; the overview compares parables with folktale excerpts of the same length as well.</li>
        </ul>
      </section>

      {/* ---------------- placement */}
      <section style={{ marginTop: 48 }}>
        <h2>Where do parables land?</h2>
        <p className="prose">Each text is linked to its 10 nearest folktales. A cell shows how many percentage points more (teal) or fewer (orange) of a tradition's parable links reach a community than the links of non-story text from the same translation. * = beyond 1,000 shuffles of the parable/baseline label within the tradition, after Bonferroni correction; the text, not the link, is the unit.</p>
        <Placement data={data} rep={rep} />
        <ul className="prose sans" style={{ fontSize: 14 }}>
          <li>{pos.length ? <>More parable than baseline links, beyond the shuffles: {pos.map((c) => `${c.tradition} in ${c.community} (parables ${pc(c.par)} of links, baseline ${pc(c.base)})`).join("; ")}.</> : "No tradition reaches any community more than its baseline does, beyond the shuffles."}</li>
          <li>Profiles that differ from the baseline's as a whole (Jensen–Shannon divergence against the same shuffles): {andList(H.traditions.filter((t) => t.differs).map((t) => t.tradition)) || "none"}.</li>
        </ul>
      </section>

      {/* ---------------- trust */}
      <section style={{ marginTop: 48 }}>
        <h2>Can we trust the ranking?</h2>
        <p className="prose">The folktale corpus already holds {C.queries.length} retellings from religious collections whose tale type is known: {andList(collections)}. They were taken off the map (with any near-copy) and used as test queries. A hit means a folktale of the same type is among the 10 most similar. <span className={`chip ${C.gate.passed ? "ok" : "warn"}`}>{C.gate.passed ? "test passed" : "test not passed"}</span></p>
        <div className="grid-2">
          <div className="sans">
            {(["tfidf", "embedding"] as const).map((r) => {
              const c = C.calibration[r];
              return (
                <div key={r} style={{ display: "grid", gridTemplateColumns: "96px 1fr 120px", gap: 10, alignItems: "center", margin: "10px 0", fontSize: 14 }}>
                  <span style={{ fontWeight: r === rep ? 650 : 400 }}>{r === "tfidf" ? "TF–IDF" : "Embeddings"}</span>
                  <div style={{ position: "relative", height: 22, background: "var(--paper-3)", borderRadius: 4 }}>
                    <span style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${c.recall * 100}%`, background: PARABLE, borderRadius: 4 }} />
                    <span style={{ position: "absolute", top: 10, height: 2, left: `${c.low * 100}%`, width: `${(c.high - c.low) * 100}%`, background: "#1d2b33" }} />
                    <span style={{ position: "absolute", top: -4, bottom: -4, left: `${c.chance * 100}%`, borderLeft: "2px dashed #6b767c" }} />
                  </div>
                  <span style={{ fontVariantNumeric: "tabular-nums" }}>{fmt(c.recall, 2)} [{fmt(c.low, 2)}–{fmt(c.high, 2)}]</span>
                </div>
              );
            })}
            <p className="small muted">Bar: share of the 36 queries with a hit in the top 10, with 95% interval. Dashed line: chance ({fmt(C.calibration.tfidf.chance, 2)}), from the sizes of the tale types.</p>
          </div>
          <ul className="sans" style={{ fontSize: 14, margin: 0 }}>
            <li><strong>Second method.</strong> TF–IDF and embeddings agree moderately on which parables are folktale-like (Spearman {fmt(C.second.spearman, 2)}) but rarely on which folktales are nearest (mean overlap of the top-10 lists {fmt(C.second.jaccard, 2)}).</li>
            <li><strong>Hubs.</strong> The 10 most frequent neighbours take {pc(C.hubs[rep].top10Share)} of all links ({REP_NAME[rep]}); the most frequent, “{C.hubs[rep].first}”, is near {pc(C.hubs[rep].firstShare)} of parables.</li>
            <li><strong>Names, formulae and nouns.</strong> Masking names and set phrases such as “when Brahmadatta was reigning in Benares”, or every noun, is one of the checks in <a href="#/">Table 1 of the overview</a>.</li>
            <li><strong>Hand labels</strong> <span className="chip warn">{C.hand.status}</span> Two of us judge the nearest pair of 100 parables: same plot, shared motif, theme only or unrelated.</li>
          </ul>
        </div>
        <details className="how" style={{ marginTop: 14 }}>
          <summary>The 36 test queries and their ranks</summary>
          <div className="table-wrap"><table className="data">
            <thead><tr><th>Retelling</th><th>Collection</th><th>Tale type</th><th className="num">Same-type folktales</th><th className="num">Rank, TF–IDF</th><th className="num">Rank, embeddings</th></tr></thead>
            <tbody>{queries.map((x) => <tr key={x.title + x.atu}><td>{x.title}</td><td>{x.collection}</td><td>{x.atu}</td><td className="num">{x.sameType}</td><td className="num">{rankChip(x.tfidf)}</td><td className="num">{rankChip(x.embedding)}</td></tr>)}</tbody>
          </table></div>
        </details>
        <h3 style={{ marginTop: 24 }}>Does the order of the traditions survive?</h3>
        <p className="prose small sans muted">Rank of each tradition (1 = most folktale-like) when the measure is changed ({REP_NAME[rep]}).</p>
        <div className="table-wrap"><table className="data">
          <thead><tr><th>Measure</th>{ord.map((t) => <th key={t.tradition} className="num">{t.tradition}</th>)}</tr></thead>
          <tbody>{variants.map((vn) => <tr key={vn}><td>{vn}</td>{ord.map((t) => { const v = P.variants.find((x) => x.variant === vn && x.tradition === t.tradition); return <td key={t.tradition} className="num"><span className={`chip${v?.rank === 1 ? " ok" : ""}`}>{v?.rank ?? "–"}</span></td>; })}</tr>)}</tbody>
        </table></div>
        <h3 style={{ marginTop: 24 }}>The closest parable–folktale pairs</h3>
        <div className="grid-2">
          {C.topPairs[rep].map((p) => (
            <div key={p.title} style={{ border: "1px solid var(--rule)", borderRadius: 8, padding: "12px 14px", background: "#fffaf2" }}>
              <div className="sans small muted">{p.tradition} · cosine {fmt(p.cosine)}</div>
              <h4 style={{ fontFamily: "var(--serif)", fontSize: "1.05rem", margin: "4px 0 6px" }}>{p.title}</h4>
              <p className="small" style={{ fontStyle: "italic", margin: "0 0 8px" }}>“{p.parableOpening}”</p>
              <div className="sans small">Nearest folktale: <strong>{p.folktale}</strong> (ATU {p.atu})</div>
              <p className="small muted" style={{ fontStyle: "italic", margin: "4px 0 0" }}>“{p.folktaleOpening}”</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---------------- explorer */}
      <section style={{ marginTop: 48 }}>
        <h2>Every parable and its nearest folktales</h2>
        <p className="prose">Open a row for the opening words, the 5 nearest folktales and the source. The grey tick on each bar is the median folktale's closeness to the other folktales.</p>
        <div className="sans" style={{ display: "flex", flexWrap: "wrap", gap: "8px 14px", alignItems: "center", margin: "10px 0" }}>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search titles, openings and folktales" aria-label="Search parables"
            style={{ flex: "1 1 240px", minWidth: 0, font: "inherit", fontSize: 14, padding: "6px 10px", border: "1px solid var(--rule)", borderRadius: 6, background: "#fffaf2" }} />
          <Segmented<string> label="Tradition" value={trad} onChange={setTrad} options={[{ value: "all", label: "All" }, ...data.traditions.map((t) => ({ value: t, label: t }))]} />
          <select value={kind} onChange={(e) => setKind(e.target.value as "parable" | "baseline")} aria-label="Which texts" className="btn small"><option value="parable">Parables</option><option value="baseline">Non-story baseline</option></select>
          <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort" className="btn small"><option value="desc">Most folktale-like first</option><option value="asc">Least folktale-like first</option><option value="trad">By tradition</option><option value="len">Longest first</option></select>
        </div>
        <p className="sans small muted">{rows.length} {kind === "parable" ? "parables" : "baseline passages"} · closeness by {REP_NAME[rep]}</p>
        <div className="sans" style={{ border: "1px solid var(--rule)", borderRadius: 8, background: "#fffaf2" }}>
          {rows.map((t) => {
            const n = t.nearest[rep];
            return (
              <details key={t.id} style={{ borderBottom: "1px solid var(--paper-3)" }}>
                <summary style={{ cursor: "pointer", display: "grid", gridTemplateColumns: "40px 86px minmax(0, 1.6fr) 150px minmax(0, 1.2fr)", gap: 10, alignItems: "center", padding: "7px 10px", fontSize: 13 }}>
                  <span className="muted">{t.rank[rep] ?? ""}</span><span>{t.tradition}</span>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontWeight: 600 }}>{t.title}</span>
                  <span style={{ display: "grid", gridTemplateColumns: "1fr 44px", gap: 6, alignItems: "center" }}>
                    <span style={{ position: "relative", height: 8, background: "var(--paper-3)", borderRadius: 4 }}>
                      <span style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: w(t.closeness[rep] as number), background: PARABLE, borderRadius: 4 }} />
                      <span style={{ position: "absolute", top: -3, bottom: -3, left: w(P.folktales.q50), borderLeft: "2px solid #6b767c" }} />
                    </span>
                    <span style={{ fontVariantNumeric: "tabular-nums" }}>{fmt(t.closeness[rep])}</span>
                  </span>
                  <span className="muted" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{F.title[n[0]]}</span>
                </summary>
                <div style={{ padding: "4px 10px 14px 60px", fontSize: 13.5, display: "grid", gap: 8 }}>
                  <p style={{ margin: 0, fontFamily: "var(--serif)", fontSize: 15 }}>{t.opening}</p>
                  <div><strong>Nearest folktales</strong>
                    <ol style={{ margin: "4px 0 0", paddingLeft: 20 }}>{n.map((i, k) => <li key={i}>{F.title[i]}{F.atu[i] && <span className="muted"> · ATU {F.atu[i]} {F.atuName[i]}</span>} <span className="muted">· {fmt(t.cos[rep][k])}</span></li>)}</ol>
                  </div>
                  <p className="small muted" style={{ margin: 0 }}>{t.source}, tr. {t.translator} ({t.year}) · {t.tokens} words{t.note ? ` · ${t.note}` : ""} · <a href={t.url} target="_blank" rel="noopener noreferrer">source</a></p>
                </div>
              </details>
            );
          })}
        </div>
      </section>

      <section style={{ marginTop: 48 }}>
        <div className="grid-2">
          <div className="prose"><h3>We can say</h3><ul>
            <li>How close each parable, and each tradition, is in text to this folktale corpus.</li>
            <li>Which folklore communities each tradition's parables resemble, and whether traditions differ in that.</li>
            <li>Whether closeness survives the same-translation baseline, masking of names and removal of hub folktales.</li></ul></div>
          <div className="prose"><h3>We cannot say</h3><ul>
            <li>That a parable borrowed from a folktale, or the reverse.</li>
            <li>Anything about a religion as a whole: these are one or two collections per tradition, in one English translation each.</li>
            <li>Anything about all folktales in the world: the corpus is {int(data.corpus.folktales)} English versions, mostly European.</li></ul></div>
        </div>
        <p className="sans small muted" style={{ marginTop: 12 }}>Parables: World English Bible; <em>The Jātaka</em>, ed. Cowell (1895–1907); <em>Lotus Sutra</em>, tr. Kern (1884); Rapaport, <em>Tales and Maxims from the Midrash</em> (1907); Rumi, <em>Masnavi</em>, tr. Whinfield (1898); Zhuangzi, tr. Legge (1891). Public-domain translations; this page shows titles and openings of at most 40 words. Results built {data.built} from commit {data.commit}; numbers and code in the repository's <span className="mono">results/</span> folder.</p>
      </section>
    </div>
  );
}
