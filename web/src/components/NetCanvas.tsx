import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { NetMap } from "../data";
import { Tooltip, useTokens, type Tip } from "./ui";

// The folktale network on a canvas, following the course's drawing rules (week 4): the backbone (each tale's
// strongest links) drawn faintly first, dots placed by the force layout of the whole network, coloured by one
// categorical choice, sized by degree or PageRank, a few important tales labelled. Zoom with the wheel or the
// buttons, drag to pan, click a dot to select it. Markers (parables) sit at given positions on top.

export type Tone = 0 | 1 | 2 | 3;
export interface Rings { counts: Map<number, number>; tone: Tone }
export interface Marker { id: string; x: number; y: number; tone: Tone; hollow?: boolean; title: string }

function quantile(sorted: number[], q: number) { return sorted[Math.min(sorted.length - 1, Math.max(0, Math.round(q * (sorted.length - 1))))]; }

export function NetCanvas({ map, tone, tip, label, onPick, onPickMarker, rings = [], size = "degree", labels = [], selected = null,
  focus = null, markers = [], aspect = 0.68, height, wheel = "ctrl" }: {
  map: NetMap; tone: (i: number) => Tone; tip: (i: number) => ReactNode; label: string;
  onPick?: (i: number) => void; onPickMarker?: (id: string) => void; rings?: Rings[]; size?: "degree" | "pagerank" | "none";
  labels?: { node: number; text: string }[]; selected?: number | null; focus?: number | null; markers?: Marker[]; aspect?: number; height?: number;
  /** "ctrl": the wheel scrolls the page and Ctrl + wheel zooms (story pages); "always": the wheel zooms (Explore) */
  wheel?: "ctrl" | "always";
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const pts = useRef<[number, number, number][]>([]);
  const mks = useRef<[number, number, string][]>([]);
  const [width, setWidth] = useState(720);
  const [hover, setHover] = useState<Tip | null>(null);
  const [view, setView] = useState({ k: 1, tx: 0, ty: 0 });
  const drag = useRef<{ x: number; y: number; tx: number; ty: number; moved: boolean } | null>(null);
  const tk = useTokens(["neutral", "c1", "c2", "c3", "edge", "ink", "paper"]);
  useEffect(() => {
    const el = canvas.current?.parentElement;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth));
    ro.observe(el);
    setWidth(el.clientWidth);
    return () => ro.disconnect();
  }, []);
  const h = height ?? Math.max(280, Math.min(Math.round(width * aspect), 680));

  // fit the central 97% of the communities' tales to the canvas: a few isolates sit far out
  const frame = useMemo(() => {
    const inner = map.x.map((_, i) => i).filter((i) => map.group[i] >= 0);
    const xs = inner.map((i) => map.x[i]).sort((a, b) => a - b), ys = inner.map((i) => map.y[i]).sort((a, b) => a - b);
    return { x0: quantile(xs, 0.015), x1: quantile(xs, 0.985), y0: quantile(ys, 0.015), y1: quantile(ys, 0.985) };
  }, [map]);
  const sizeOf = useMemo(() => {
    const v = size === "pagerank" ? map.pagerank : map.degree, max = Math.max(...v);
    return (i: number) => (size === "none" ? 0 : Math.sqrt(v[i] / max));
  }, [map, size]);
  // base projection (before zoom): layout -> canvas pixels
  const base = useMemo(() => {
    const { x0, x1, y0, y1 } = frame, pad = 12;
    const s = Math.min((width - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0));
    const ox = (width - s * (x1 - x0)) / 2, oy = (h - s * (y1 - y0)) / 2;
    return { px: (x: number) => ox + (x - x0) * s, py: (y: number) => oy + (y1 - y) * s };
  }, [frame, width, h]);

  // zoom onto a focused tale (a search result or a selection from a list)
  useEffect(() => {
    if (focus === null || focus === undefined || focus < 0) return;
    const k = 3.2, bx = base.px(map.x[focus]), by = base.py(map.y[focus]);
    setView({ k, tx: width / 2 - k * bx, ty: h / 2 - k * by });
  }, [focus, base, map, width, h]);
  useEffect(() => { setView({ k: 1, tx: 0, ty: 0 }); }, [map]);

  useEffect(() => {
    const cv = canvas.current;
    if (!cv) return;
    const w = width, dpr = window.devicePixelRatio || 1;
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); cv.style.height = `${h}px`;
    const ctx = cv.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const { k, tx, ty } = view;
    const px = (i: number) => tx + k * base.px(map.x[i]), py = (i: number) => ty + k * base.py(map.y[i]);
    const colours = [tk.neutral, tk.c1, tk.c2, tk.c3];
    const r0 = Math.max(1.4, Math.min(2.4, w / 360)) * Math.min(2.2, Math.sqrt(k));
    const radius = (i: number) => (size === "none" ? r0 : r0 * 0.75 + r0 * 1.9 * sizeOf(i));

    ctx.strokeStyle = tk.edge; ctx.globalAlpha = 0.07; ctx.lineWidth = 0.6; ctx.beginPath();
    for (let e = 0; e < map.edges.length; e += 2) { ctx.moveTo(px(map.edges[e]), py(map.edges[e])); ctx.lineTo(px(map.edges[e + 1]), py(map.edges[e + 1])); }
    ctx.stroke();
    if (selected !== null) {             // the selected tale's strongest links, drawn darker
      ctx.globalAlpha = 0.85; ctx.lineWidth = 1.2; ctx.strokeStyle = tk.ink; ctx.beginPath();
      for (let e = 0; e < map.edges.length; e += 2) {
        const a = map.edges[e], b = map.edges[e + 1];
        if (a === selected || b === selected) { ctx.moveTo(px(a), py(a)); ctx.lineTo(px(b), py(b)); }
      }
      ctx.stroke();
    }
    const n = map.x.length, order = Array.from({ length: n }, (_, i) => i), tones = order.map(tone);
    order.sort((a, b) => Number(tones[a] > 0) - Number(tones[b] > 0));
    for (const i of order) {
      ctx.globalAlpha = tones[i] ? 0.92 : 0.5;
      ctx.fillStyle = colours[tones[i]];
      ctx.beginPath(); ctx.arc(px(i), py(i), radius(i), 0, 2 * Math.PI); ctx.fill();
    }
    ctx.globalAlpha = 0.95; ctx.lineWidth = 1.4;
    for (const ring of rings) {
      ctx.strokeStyle = colours[ring.tone];
      ring.counts.forEach((c, i) => { ctx.beginPath(); ctx.arc(px(i), py(i), r0 + 1.5 + 2.2 * Math.sqrt(c), 0, 2 * Math.PI); ctx.stroke(); });
    }
    // markers (parables): diamonds, filled or hollow
    const mk: [number, number, string][] = [];
    for (const m of markers) {
      const x = tx + k * base.px(m.x), y = ty + k * base.py(m.y), s = 4.2;
      ctx.globalAlpha = 0.95; ctx.beginPath(); ctx.moveTo(x, y - s); ctx.lineTo(x + s, y); ctx.lineTo(x, y + s); ctx.lineTo(x - s, y); ctx.closePath();
      ctx.fillStyle = m.hollow ? tk.paper : m.tone ? colours[m.tone] : tk.ink; ctx.fill();
      ctx.lineWidth = 1.3; ctx.strokeStyle = m.tone ? colours[m.tone] : tk.ink; ctx.stroke();
      mk.push([x, y, m.id]);
    }
    mks.current = mk;
    if (selected !== null && selected >= 0) {
      ctx.globalAlpha = 1; ctx.strokeStyle = tk.ink; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(px(selected), py(selected), radius(selected) + 4, 0, 2 * Math.PI); ctx.stroke();
    }
    ctx.globalAlpha = 1; ctx.font = "600 11.5px Inter Variable, Inter, system-ui, sans-serif"; ctx.textBaseline = "middle";
    for (const l of labels) {
      const x = px(l.node), y = py(l.node);
      if (x < 0 || x > w || y < 0 || y > h) continue;
      const right = x + 7 + ctx.measureText(l.text).width > w - 4;
      ctx.textAlign = right ? "right" : "left";
      const tx2 = right ? x - 7 : x + 7;
      ctx.lineWidth = 3.5; ctx.strokeStyle = tk.paper; ctx.strokeText(l.text, tx2, y);
      ctx.fillStyle = tk.ink; ctx.fillText(l.text, tx2, y);
      ctx.beginPath(); ctx.arc(x, y, radius(l.node) + 2, 0, 2 * Math.PI); ctx.lineWidth = 1.2; ctx.strokeStyle = tk.ink; ctx.stroke();
    }
    pts.current = order.map((i) => [px(i), py(i), i]);
  }, [map, base, width, h, view, tone, rings, tk, size, sizeOf, labels, selected, markers]);

  const at = (clientX: number, clientY: number) => {
    const b = canvas.current!.getBoundingClientRect();
    return [clientX - b.left, clientY - b.top];
  };
  const nearestDot = (x: number, y: number) => {
    let best = -1, bd = 90;
    for (const [px, py, i] of pts.current) { const d = (px - x) ** 2 + (py - y) ** 2; if (d < bd) { bd = d; best = i; } }
    return best;
  };
  const nearestMarker = (x: number, y: number) => {
    for (const [mx, my, id] of mks.current) if ((mx - x) ** 2 + (my - y) ** 2 < 49) return id;
    return null;
  };
  const zoomBy = (f: number, cx = width / 2, cy = h / 2) =>
    setView((v) => { const k = Math.min(12, Math.max(1, v.k * f)); const s = k / v.k; return k === 1 ? { k: 1, tx: 0, ty: 0 } : { k, tx: cx - s * (cx - v.tx), ty: cy - s * (cy - v.ty) }; });
  const zoomRef = useRef(zoomBy);
  zoomRef.current = zoomBy;
  useEffect(() => {
    const el = canvas.current;
    if (!el) return;
    const on = (ev: WheelEvent) => {
      if (wheel === "ctrl" && !(ev.ctrlKey || ev.metaKey)) return;
      ev.preventDefault();
      const b = el.getBoundingClientRect();
      zoomRef.current(ev.deltaY < 0 ? 1.25 : 0.8, ev.clientX - b.left, ev.clientY - b.top);
    };
    el.addEventListener("wheel", on, { passive: false });
    return () => el.removeEventListener("wheel", on);
  }, [wheel]);

  return (
    <div className="netcanvas">
      <canvas ref={canvas} className="map-canvas" role="img" aria-label={label} style={{ cursor: drag.current ? "grabbing" : "grab" }}
        onPointerDown={(ev) => { drag.current = { x: ev.clientX, y: ev.clientY, tx: view.tx, ty: view.ty, moved: false }; (ev.target as HTMLElement).setPointerCapture(ev.pointerId); }}
        onPointerMove={(ev) => {
          const d = drag.current;
          if (d && view.k > 1) {
            const dx = ev.clientX - d.x, dy = ev.clientY - d.y;
            if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
            if (d.moved) { setView((v) => ({ ...v, tx: d.tx + dx, ty: d.ty + dy })); setHover(null); return; }
          }
          const [x, y] = at(ev.clientX, ev.clientY);
          const m = nearestMarker(x, y);
          if (m) { const mm = markers.find((q) => q.id === m); setHover(mm ? { x: ev.clientX, y: ev.clientY, body: <><strong>{mm.title}</strong><br /><em>click to open it</em></> } : null); return; }
          const i = nearestDot(x, y);
          setHover(i < 0 ? null : { x: ev.clientX, y: ev.clientY, body: tip(i) });
        }}
        onPointerUp={(ev) => {
          const d = drag.current; drag.current = null;
          if (d?.moved) return;
          const [x, y] = at(ev.clientX, ev.clientY);
          const m = nearestMarker(x, y);
          if (m && onPickMarker) { onPickMarker(m); return; }
          const i = nearestDot(x, y);
          if (i >= 0) onPick?.(i);
        }}
        onPointerLeave={() => setHover(null)} />
      <div className="zoom-buttons">
        <button type="button" className="btn" aria-label="Zoom in" onClick={() => zoomBy(1.5)}>+</button>
        <button type="button" className="btn" aria-label="Zoom out" onClick={() => zoomBy(1 / 1.5)}>−</button>
        <button type="button" className="btn" aria-label="Show the whole network" onClick={() => setView({ k: 1, tx: 0, ty: 0 })}>⤢</button>
        <span className="zoom-hint">{wheel === "ctrl" ? "Ctrl + scroll or +/− to zoom · drag to move" : "scroll to zoom · drag to move"}</span>
      </div>
      <Tooltip tip={hover} />
    </div>
  );
}

/** The tales a tale is drawn linked to (its strongest links and those that count it among theirs). */
export function linkedTo(map: NetMap, node: number): number[] {
  const out = new Set<number>();
  for (let k = 0; k < map.edges.length; k += 2) {
    if (map.edges[k] === node) out.add(map.edges[k + 1]);
    else if (map.edges[k + 1] === node) out.add(map.edges[k]);
  }
  return [...out];
}

/** Position of a parable on the map, for display only: the mean position of its five nearest folktales. */
export function placeOnMap(map: NetMap, nearest: number[]): { x: number; y: number } {
  const five = nearest.slice(0, 5);
  return { x: five.reduce((a, i) => a + map.x[i], 0) / five.length, y: five.reduce((a, i) => a + map.y[i], 0) / five.length };
}

/** Colours for a partition: its three communities that overlap most with the reference picks get the three hues. */
export function alignTones(part: number[], reference: number[], picks: number[]): (i: number) => Tone {
  const used = new Set<number>(), map = new Map<number, Tone>();
  picks.forEach((g, k) => {
    const count = new Map<number, number>();
    reference.forEach((r, i) => { if (r === g) count.set(part[i], (count.get(part[i]) ?? 0) + 1); });
    const best = [...count.entries()].filter(([c]) => !used.has(c)).sort((a, b) => b[1] - a[1])[0];
    if (best) { used.add(best[0]); map.set(best[0], (k + 1) as Tone); }
  });
  return (i: number) => map.get(part[i]) ?? 0;
}
