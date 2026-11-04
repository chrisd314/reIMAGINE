import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from "react";
import { select, zoom as d3zoom, zoomIdentity, type ZoomBehavior, type ZoomTransform } from "d3";
import { DUR, easeInOutCubic, useMotion } from "../lib/motion";
import { hexToRgb } from "../lib/colours";

// World space shared by every layout and the map projection.
export const WORLD_W = 1000;
export const WORLD_H = 620;

export interface Marker { x: number; y: number; count: number; label: string }
export interface TooltipContent { title: string; lines: string[] }

export interface NetworkCanvasProps {
  n: number;
  positions: Float32Array;              // 2n world coordinates (targets)
  colours: string[];                    // hex per node (targets)
  radius?: number;                      // screen px
  visible?: boolean[];
  dimmed?: boolean[];
  edges?: [number, number, number][];   // faint context edges
  edgeAlpha?: number;
  focusEdges?: [number, number, number][];
  selected?: number | null;
  highlight?: number[];
  pair?: [number, number] | null;
  labels?: string[];
  tooltip?: (i: number) => TooltipContent | null;
  onSelect?: (i: number | null) => void;
  onEdgeClick?: (i: number, j: number) => void;
  background?: ((ctx: CanvasRenderingContext2D, alpha: number) => void) | null;
  backgroundAlpha?: number;
  markers?: Marker[] | null;
  markersAlpha?: number;
  transition?: { key: string; duration?: number };
  onTransitionEnd?: (key: string) => void;
  fit?: { key: string; indices: number[] | null };
  ariaLabel: string;
  drawTrail?: boolean;
  /** "full": wheel/drag/pinch zoom (Explore). "gentle": page scroll wins; Ctrl+wheel or the buttons zoom (Story). */
  zoomMode?: "full" | "gentle";
}

export interface NetworkCanvasHandle { zoomBy: (k: number) => void; fitAll: () => void; toPNG: () => string | null }

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export const NetworkCanvas = forwardRef<NetworkCanvasHandle, NetworkCanvasProps>(function NetworkCanvas(props, ref) {
  const { enabled: motion } = useMotion();
  const hostRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tip, setTip] = useState<{ x: number; y: number; c: TooltipContent } | null>(null);
  const [zoomed, setZoomed] = useState(false);
  const st = useRef({
    pos: new Float32Array(0), from: new Float32Array(0), to: new Float32Array(0),
    col: [] as [number, number, number][], colFrom: [] as [number, number, number][], colTo: [] as [number, number, number][],
    t0: 0, dur: 0, animating: false, transKey: "", raf: 0,
    edgesPrev: [] as [number, number, number][], edgesFade: 1, edgesT0: 0,
    bgAlpha: 0, bgFrom: 0, bgTo: 0, mkAlpha: 0, mkFrom: 0, mkTo: 0,
    transform: zoomIdentity as ZoomTransform, size: { w: 300, h: 200, dpr: 1 },
    trail: null as null | { from: [number, number] },
  });
  const zoomRef = useRef<ZoomBehavior<HTMLCanvasElement, unknown> | null>(null);
  const propsRef = useRef(props);
  propsRef.current = props;

  // base transform: fit world into viewport (contain) with padding
  const base = () => {
    const { w, h } = st.current.size;
    const pad = 16;
    const s = Math.min((w - 2 * pad) / WORLD_W, (h - 2 * pad) / WORLD_H);
    return { s, ox: (w - WORLD_W * s) / 2, oy: (h - WORLD_H * s) / 2 };
  };
  const toScreen = (x: number, y: number) => {
    const b = base();
    const t = st.current.transform;
    return [t.applyX(b.ox + x * b.s), t.applyY(b.oy + y * b.s)] as [number, number];
  };

  const draw = useCallback(() => {
    const c = canvasRef.current;
    if (!c) return;
    const ctx = c.getContext("2d")!;
    const p = propsRef.current;
    const S = st.current;
    const { w, h, dpr } = S.size;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const now = performance.now();
    let more = false;
    // advance animation
    if (S.animating) {
      const raw = S.dur > 0 ? Math.min(1, (now - S.t0) / S.dur) : 1;
      const e = easeInOutCubic(raw);
      for (let k = 0; k < S.pos.length; k++) S.pos[k] = lerp(S.from[k], S.to[k], e);
      for (let k = 0; k < S.col.length; k++) {
        const a = S.colFrom[k] ?? S.colTo[k], b = S.colTo[k];
        S.col[k] = [lerp(a[0], b[0], e), lerp(a[1], b[1], e), lerp(a[2], b[2], e)];
      }
      S.bgAlpha = lerp(S.bgFrom, S.bgTo, e);
      S.mkAlpha = lerp(S.mkFrom, S.mkTo, e);
      if (raw >= 1) {
        S.animating = false;
        const key = S.transKey;
        setTimeout(() => propsRef.current.onTransitionEnd?.(key), 0);
      } else more = true;
    }
    let edgeT = 1;
    if (S.edgesFade < 1) {
      edgeT = Math.min(1, (now - S.edgesT0) / (motion ? DUR.recolour : 1));
      S.edgesFade = edgeT;
      if (edgeT < 1) more = true;
    }
    const b = base();
    const T = S.transform;
    ctx.save();
    ctx.translate(T.x, T.y);
    ctx.scale(T.k, T.k);
    ctx.translate(b.ox, b.oy);
    ctx.scale(b.s, b.s);
    if (p.background && S.bgAlpha > 0.01) p.background(ctx, S.bgAlpha);
    ctx.restore();

    const vis = p.visible;
    const dim = p.dimmed;
    const sx = (i: number) => T.applyX(b.ox + S.pos[2 * i] * b.s);
    const sy = (i: number) => T.applyY(b.oy + S.pos[2 * i + 1] * b.s);
    // context edges (crossfade old -> new)
    const alphaBase = p.edgeAlpha ?? 0.12;
    const drawEdges = (es: [number, number, number][], alpha: number, colour: string, width: number) => {
      if (alpha <= 0.005 || !es.length) return;
      ctx.strokeStyle = colour;
      ctx.globalAlpha = alpha;
      ctx.lineWidth = width;
      ctx.beginPath();
      for (const [i, j] of es) {
        if (vis && (!vis[i] || !vis[j])) continue;
        ctx.moveTo(sx(i), sy(i));
        ctx.lineTo(sx(j), sy(j));
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
    };
    drawEdges(S.edgesPrev, alphaBase * (1 - edgeT), "#55636b", 0.6);
    drawEdges(p.edges ?? [], alphaBase * edgeT, "#55636b", 0.6);
    // focus edges
    if (p.focusEdges?.length) {
      const maxW = Math.max(...p.focusEdges.map((e) => e[2]));
      const minW = Math.min(...p.focusEdges.map((e) => e[2]));
      for (const [i, j, wgt] of p.focusEdges) {
        if (vis && (!vis[i] || !vis[j])) continue;
        const f = maxW > minW ? (wgt - minW) / (maxW - minW) : 1;
        ctx.strokeStyle = "#b4532a";
        ctx.globalAlpha = 0.35 + 0.5 * f;
        ctx.lineWidth = 0.8 + 2.2 * f;
        ctx.beginPath(); ctx.moveTo(sx(i), sy(i)); ctx.lineTo(sx(j), sy(j)); ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    // pair line
    if (p.pair) {
      const [a, c2] = p.pair;
      ctx.strokeStyle = "#e8a33d"; ctx.lineWidth = 3; ctx.setLineDash([6, 4]);
      ctx.beginPath(); ctx.moveTo(sx(a), sy(a)); ctx.lineTo(sx(c2), sy(c2)); ctx.stroke(); ctx.setLineDash([]);
    }
    // trail for the selected tale during a morph
    if (p.drawTrail && S.trail && p.selected != null && S.animating) {
      const [fx, fy] = toScreen(S.trail.from[0], S.trail.from[1]);
      ctx.strokeStyle = "#e8a33d"; ctx.lineWidth = 2; ctx.globalAlpha = 0.8;
      ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(sx(p.selected), sy(p.selected)); ctx.stroke(); ctx.globalAlpha = 1;
    }
    // nodes
    const r = (p.radius ?? 3.2) * Math.max(1, Math.sqrt(T.k) * 0.9);
    const hl = new Set(p.highlight ?? []);
    const order: number[] = [];
    for (let i = 0; i < p.n; i++) if (!vis || vis[i]) order.push(i);
    const pass = (filter: (i: number) => boolean, alpha: number, ring: boolean) => {
      for (const i of order) {
        if (!filter(i)) continue;
        const cc = S.col[i] ?? [150, 150, 150];
        ctx.globalAlpha = alpha;
        ctx.fillStyle = `rgb(${cc[0] | 0},${cc[1] | 0},${cc[2] | 0})`;
        ctx.beginPath(); ctx.arc(sx(i), sy(i), r, 0, Math.PI * 2); ctx.fill();
        if (ring) { ctx.strokeStyle = "#fffaf2"; ctx.lineWidth = 0.8; ctx.stroke(); }
      }
      ctx.globalAlpha = 1;
    };
    const anyFocus = p.selected != null || (dim?.some(Boolean) ?? false);
    pass((i) => !!dim?.[i], 0.16, false);
    pass((i) => !dim?.[i] && !hl.has(i) && i !== p.selected, anyFocus && p.selected != null ? 0.5 : 0.92, true);
    for (const i of hl) {
      if (vis && !vis[i]) continue;
      const cc = S.col[i] ?? [150, 150, 150];
      ctx.fillStyle = `rgb(${cc[0] | 0},${cc[1] | 0},${cc[2] | 0})`;
      ctx.beginPath(); ctx.arc(sx(i), sy(i), r * 1.6, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = "#1d2b33"; ctx.lineWidth = 1.4; ctx.stroke();
    }
    const ringAt = (i: number, colour: string, rr: number) => {
      if (vis && !vis[i]) return;
      ctx.fillStyle = "rgba(232,163,61,0.35)";
      ctx.beginPath(); ctx.arc(sx(i), sy(i), rr + 7, 0, Math.PI * 2); ctx.fill();
      const cc = S.col[i] ?? [150, 150, 150];
      ctx.fillStyle = `rgb(${cc[0] | 0},${cc[1] | 0},${cc[2] | 0})`;
      ctx.beginPath(); ctx.arc(sx(i), sy(i), rr, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = colour; ctx.lineWidth = 2.6; ctx.stroke();
    };
    if (p.pair) { ringAt(p.pair[0], "#1d2b33", r * 2); ringAt(p.pair[1], "#1d2b33", r * 2); }
    if (p.selected != null) ringAt(p.selected, "#1d2b33", r * 2.3);
    // markers (collapsed places)
    if (p.markers && S.mkAlpha > 0.01) {
      ctx.globalAlpha = S.mkAlpha;
      for (const m of p.markers) {
        const [mx, my] = toScreen(m.x, m.y);
        const rr = 3.5 + Math.sqrt(m.count) * 1.55;
        ctx.fillStyle = "rgba(29,43,51,0.82)";
        ctx.beginPath(); ctx.arc(mx, my, rr, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = "#fffaf2"; ctx.lineWidth = 1.2; ctx.stroke();
        if (rr > 9) {
          ctx.fillStyle = "#fffaf2"; ctx.font = "600 10.5px Inter Variable, system-ui, sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
          ctx.fillText(String(m.count), mx, my + 0.5);
        }
      }
      ctx.globalAlpha = 1;
    }
    // labels on focus
    if (p.labels && (p.selected != null || p.pair)) {
      const want = [...(p.selected != null ? [p.selected] : []), ...(p.pair ?? []), ...(p.highlight ?? [])].slice(0, 14);
      const boxes: [number, number, number, number][] = [];
      ctx.font = "600 12px Inter Variable, system-ui, sans-serif";
      ctx.textAlign = "left"; ctx.textBaseline = "middle";
      want.forEach((i, k) => {
        if (vis && !vis[i]) return;
        const text = (p.labels![i] ?? "").slice(0, 38) + ((p.labels![i] ?? "").length > 38 ? "…" : "");
        const tw = ctx.measureText(text).width;
        const x = sx(i) + r * 2 + 6, y = sy(i);
        const box: [number, number, number, number] = [x - 3, y - 9, tw + 6, 18];
        if (boxes.some((bb) => !(box[0] > bb[0] + bb[2] || box[0] + box[2] < bb[0] || box[1] > bb[1] + bb[3] || box[1] + box[3] < bb[1]))) return;
        boxes.push(box);
        ctx.fillStyle = k === 0 && p.selected != null ? "rgba(29,43,51,0.92)" : "rgba(251,247,239,0.92)";
        ctx.fillRect(box[0], box[1], box[2], box[3]);
        ctx.fillStyle = k === 0 && p.selected != null ? "#fffaf2" : "#1d2b33";
        ctx.fillText(text, x, y);
      });
    }
    if (more) S.raf = requestAnimationFrame(draw);
    else S.raf = 0;
  }, [motion]);

  const kick = useCallback(() => {
    if (!st.current.raf) st.current.raf = requestAnimationFrame(draw);
  }, [draw]);

  // targets change -> start (interruptible) transition from the current drawn state
  useEffect(() => {
    const S = st.current;
    const n = props.n;
    const target = props.positions;
    const newCols = props.colours.map((c) => hexToRgb(c));
    const first = S.pos.length !== target.length;
    const dur = !motion || first ? 0 : (props.transition?.duration ?? DUR.layout);
    if (props.selected != null && S.pos.length === target.length) S.trail = { from: [S.pos[2 * props.selected], S.pos[2 * props.selected + 1]] };
    S.from = first ? new Float32Array(target) : new Float32Array(S.pos);
    S.to = new Float32Array(target);
    if (first) S.pos = new Float32Array(target);
    S.colFrom = first || S.col.length !== n ? newCols : S.col.map((c) => [...c] as [number, number, number]);
    S.colTo = newCols;
    if (first || S.col.length !== n) S.col = newCols.map((c) => [...c] as [number, number, number]);
    S.bgFrom = S.bgAlpha; S.bgTo = props.backgroundAlpha ?? (props.background ? 1 : 0);
    S.mkFrom = S.mkAlpha; S.mkTo = props.markersAlpha ?? (props.markers ? 1 : 0);
    if (first) { S.bgAlpha = S.bgTo; S.mkAlpha = S.mkTo; }
    S.t0 = performance.now();
    S.dur = dur;
    S.animating = true;
    S.transKey = props.transition?.key ?? "";
    kick();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.positions, props.colours, props.transition?.key, props.backgroundAlpha, props.markersAlpha, motion]);

  // context edges crossfade
  const lastEdges = useRef<[number, number, number][] | undefined>(undefined);
  useEffect(() => {
    if (lastEdges.current !== props.edges) {
      st.current.edgesPrev = lastEdges.current ?? [];
      st.current.edgesFade = 0;
      st.current.edgesT0 = performance.now();
      lastEdges.current = props.edges;
    }
    kick();
  }, [props.edges, kick]);

  // redraw on any other visual prop change
  useEffect(() => { kick(); }, [props.selected, props.highlight, props.pair, props.visible, props.dimmed, props.focusEdges, props.markers, kick]);

  // size + zoom setup
  useEffect(() => {
    const c = canvasRef.current!, host = hostRef.current!;
    const ro = new ResizeObserver(() => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const w = host.clientWidth, h = host.clientHeight;
      st.current.size = { w, h, dpr };
      c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
      if (!sized.current && w > 0 && h > 0) {
        sized.current = true;
        if (pendingFit.current !== undefined) { const idx = pendingFit.current; pendingFit.current = undefined; requestAnimationFrame(() => fitRef.current(idx)); }
      }
      kick();
    });
    ro.observe(host);
    const z = d3zoom<HTMLCanvasElement, unknown>().scaleExtent([0.6, 14])
      .filter((event: Event & { ctrlKey?: boolean; metaKey?: boolean; button?: number }) => {
        if ((propsRef.current.zoomMode ?? "full") === "full") return (!event.ctrlKey || event.type === "wheel") && !event.button;
        if (event.type === "wheel") return !!(event.ctrlKey || event.metaKey);
        if (event.type.startsWith("touch")) return false;  // let the page scroll on touch screens
        return !event.button;
      })
      .on("zoom", (ev) => {
        st.current.transform = ev.transform;
        const z0 = ev.transform.k === 1 && ev.transform.x === 0 && ev.transform.y === 0;
        setZoomed((was) => (was === !z0 ? was : !z0));
        setTip(null);
        kick();
      });
    zoomRef.current = z;
    select(c).call(z).on("dblclick.zoom", null);
    return () => { ro.disconnect(); select(c).on(".zoom", null); };
  }, [kick]);

  const zoomTo = useCallback((t: ZoomTransform) => {
    const c = canvasRef.current;
    if (!c || !zoomRef.current) return;
    if (motion) select(c).transition().duration(DUR.layout).call(zoomRef.current.transform, t);
    else select(c).call(zoomRef.current.transform, t);
  }, [motion]);

  const fitIndices = useCallback((idx: number[] | null) => {
    if (!idx || !idx.length) { zoomTo(zoomIdentity); return; }
    const S = st.current, b = base();
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const i of idx) {
      const x = b.ox + S.to[2 * i] * b.s, y = b.oy + S.to[2 * i + 1] * b.s;
      x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
    }
    const { w, h } = S.size;
    const pad = 70;
    const k = Math.max(0.8, Math.min(6, Math.min((w - 2 * pad) / Math.max(x1 - x0, 1), (h - 2 * pad) / Math.max(y1 - y0, 1))));
    zoomTo(zoomIdentity.translate(w / 2, h / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2));
  }, [zoomTo]);

  // a fit requested before the canvas has measured itself is applied after the first resize
  const sized = useRef(false);
  const pendingFit = useRef<number[] | null | undefined>(undefined);
  useEffect(() => {
    if (!props.fit) return;
    if (sized.current) fitIndices(props.fit.indices);
    else pendingFit.current = props.fit.indices;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.fit?.key]);
  const fitRef = useRef(fitIndices);
  fitRef.current = fitIndices;

  useImperativeHandle(ref, () => ({
    zoomBy: (k: number) => { const c = canvasRef.current; if (c && zoomRef.current) select(c).call(zoomRef.current.scaleBy, k); },
    fitAll: () => zoomTo(zoomIdentity),
    toPNG: () => canvasRef.current?.toDataURL("image/png") ?? null,
  }), [zoomTo]);

  // hit testing
  const nodeAt = (mx: number, my: number): number | null => {
    const p = propsRef.current;
    let best: number | null = null, bd = 12 * 12;
    for (let i = 0; i < p.n; i++) {
      if (p.visible && !p.visible[i]) continue;
      const [x, y] = toScreen(st.current.pos[2 * i], st.current.pos[2 * i + 1]);
      const d = (x - mx) ** 2 + (y - my) ** 2;
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  };
  const edgeAt = (mx: number, my: number): [number, number] | null => {
    const p = propsRef.current;
    for (const [i, j] of p.focusEdges ?? []) {
      const [x1, y1] = toScreen(st.current.pos[2 * i], st.current.pos[2 * i + 1]);
      const [x2, y2] = toScreen(st.current.pos[2 * j], st.current.pos[2 * j + 1]);
      const L = (x2 - x1) ** 2 + (y2 - y1) ** 2;
      if (L < 1) continue;
      const t = Math.max(0, Math.min(1, ((mx - x1) * (x2 - x1) + (my - y1) * (y2 - y1)) / L));
      const d = Math.hypot(mx - (x1 + t * (x2 - x1)), my - (y1 + t * (y2 - y1)));
      if (d < 5 && t > 0.08 && t < 0.92) return [i, j];
    }
    return null;
  };
  const rel = (e: React.PointerEvent | React.MouseEvent) => {
    const r = canvasRef.current!.getBoundingClientRect();
    return [e.clientX - r.left, e.clientY - r.top] as [number, number];
  };
  const down = useRef<[number, number] | null>(null);

  return (
    <div ref={hostRef} className="canvas-host" style={{ position: "relative" }}>
      <canvas
        ref={canvasRef}
        role="img"
        aria-label={props.ariaLabel}
        tabIndex={0}
        style={{ cursor: "grab", touchAction: (props.zoomMode ?? "full") === "gentle" ? "pan-y" : "none" }}
        onPointerDown={(e) => { down.current = [e.clientX, e.clientY]; }}
        onPointerMove={(e) => {
          if (e.buttons) return;
          const [mx, my] = rel(e);
          const i = nodeAt(mx, my);
          const c = canvasRef.current!;
          if (i !== null && props.tooltip) {
            const content = props.tooltip(i);
            setTip(content ? { x: e.clientX, y: e.clientY, c: content } : null);
            c.style.cursor = "pointer";
          } else {
            setTip(null);
            c.style.cursor = edgeAt(mx, my) ? "pointer" : "grab";
          }
        }}
        onPointerLeave={() => setTip(null)}
        onClick={(e) => {
          if (down.current && Math.hypot(e.clientX - down.current[0], e.clientY - down.current[1]) > 5) return;
          const [mx, my] = rel(e);
          const i = nodeAt(mx, my);
          if (i !== null) { props.onSelect?.(i); return; }
          const ed = edgeAt(mx, my);
          if (ed && props.onEdgeClick) { props.onEdgeClick(ed[0], ed[1]); return; }
          props.onSelect?.(null);
        }}
        onKeyDown={(e) => {
          if (e.key === "+" || e.key === "=") { props.onSelect && zoomRef.current && select(canvasRef.current!).call(zoomRef.current.scaleBy, 1.3); }
          if (e.key === "-") { zoomRef.current && select(canvasRef.current!).call(zoomRef.current.scaleBy, 1 / 1.3); }
          if (e.key === "Escape") props.onSelect?.(null);
        }}
      />
      {(props.zoomMode ?? "full") === "gentle" && (
        <div className="row" style={{ position: "absolute", right: 8, top: 8, gap: 4, zIndex: 4 }}>
          <button type="button" className="btn small" aria-label="Zoom in" onClick={() => { const c = canvasRef.current; if (c && zoomRef.current) select(c).call(zoomRef.current.scaleBy, 1.4); }}>＋</button>
          <button type="button" className="btn small" aria-label="Zoom out" onClick={() => { const c = canvasRef.current; if (c && zoomRef.current) select(c).call(zoomRef.current.scaleBy, 1 / 1.4); }}>－</button>
          {zoomed && <button type="button" className="btn small" onClick={() => zoomTo(zoomIdentity)}>Reset zoom</button>}
        </div>
      )}
      {(props.zoomMode ?? "full") === "full" && zoomed && (
        <button type="button" className="btn small" style={{ position: "absolute", right: 8, top: 8, zIndex: 4 }} onClick={() => zoomTo(zoomIdentity)}>Reset zoom</button>
      )}
      {tip && (
        <div className="tooltip" style={{ left: Math.min(tip.x + 14, window.innerWidth - 310), top: tip.y + 14 }} role="status">
          <div className="t">{tip.c.title}</div>
          {tip.c.lines.map((l, k) => <div key={k}>{l}</div>)}
        </div>
      )}
    </div>
  );
});
