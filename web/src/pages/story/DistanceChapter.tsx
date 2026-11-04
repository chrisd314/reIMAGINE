import { useEffect, useMemo, useRef, useState } from "react";
import { scaleLinear } from "d3";
import { catalogueRows, useData } from "../../data/load";
import type { CataloguePayload, DistancePayload, Rep } from "../../data/types";
import { CoverageMap, NullHistogram, pointsByCoordinate, type MapPoint } from "../../components/charts";
import { useLand } from "../../components/useGraphModel";
import { HowMade, Loading, Segmented } from "../../components/ui";
import { fmt, int } from "../../lib/format";
import { REGION_COLOURS } from "../../lib/colours";

type Subset = "all" | "same_atu" | "different_atu";

function Curves({ d, rep }: { d: DistancePayload; rep: Rep }) {
  const W = 560, H = 230, m = { l: 44, r: 12, t: 12, b: 46 };
  const res = d.results[rep];
  const subsets: { k: Subset; colour: string; label: string }[] = [
    { k: "same_atu", colour: "#b4532a", label: "same ATU type" }, { k: "different_atu", colour: "#55636b", label: "different ATU type" }];
  const all = subsets.flatMap((s) => res[s.k].curve.flatMap((c) => [c.q25 ?? 0, c.q75 ?? 0]));
  const y = scaleLinear().domain([Math.min(...all) * 0.95, Math.max(...all) * 1.03]).range([H - m.b, m.t]);
  const x = (k: number) => m.l + (k + 0.5) * ((W - m.l - m.r) / d.bins.length);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label={`Mean ${rep} similarity by distance bin for same- and different-type pairs.`}>
      {y.ticks(4).map((t) => <g key={t}><line x1={m.l} x2={W - m.r} y1={y(t)} y2={y(t)} stroke="#e3d8c4" /><text x={m.l - 6} y={y(t) + 3} fontSize={10} textAnchor="end" fill="#6b767c" fontFamily="Inter Variable, sans-serif">{t.toFixed(2)}</text></g>)}
      {subsets.map((s) => {
        const c = res[s.k].curve;
        const band = c.map((r, k) => `${x(k)},${y(r.q75 ?? 0)}`).join(" ") + " " + [...c].reverse().map((r, k) => `${x(c.length - 1 - k)},${y(r.q25 ?? 0)}`).join(" ");
        return (
          <g key={s.k}>
            <polygon points={band} fill={s.colour} opacity={0.12} />
            <polyline points={c.map((r, k) => `${x(k)},${y(r.mean ?? 0)}`).join(" ")} fill="none" stroke={s.colour} strokeWidth={2.2} />
            {c.map((r, k) => <circle key={k} cx={x(k)} cy={y(r.mean ?? 0)} r={3} fill={s.colour}><title>{`${s.label}, ${r.bin}: mean ${fmt(r.mean)} (${int(r.pairs)} pairs)`}</title></circle>)}
          </g>
        );
      })}
      {d.bins.map((b, k) => <text key={b} x={x(k)} y={H - m.b + 14} fontSize={9.5} textAnchor="middle" fill="#6b767c" fontFamily="Inter Variable, sans-serif">{b.replace(" km", "").replace("same point (0)", "same pt")}</text>)}
      <text x={(W + m.l) / 2} y={H - 8} fontSize={10.5} textAnchor="middle" fill="#3f4d55" fontFamily="Inter Variable, sans-serif">great-circle distance between recorded points (km)</text>
      {subsets.map((s, k) => <g key={s.k} transform={`translate(${m.l + 8 + k * 150},${m.t + 4})`}><rect width={14} height={3} y={4} fill={s.colour} /><text x={20} y={9} fontSize={10.5} fill="#3f4d55" fontFamily="Inter Variable, sans-serif">{s.label}</text></g>)}
    </svg>
  );
}

function Scatter({ d, rep, subset, onPick, picked }: { d: DistancePayload; rep: Rep; subset: Subset; onPick: (k: number) => void; picked: number | null }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const W = 560, H = 260, m = { l: 44, r: 12, t: 10, b: 34 };
  const yi = rep === "lexical" ? 3 : 4;
  const pts = useMemo(() => d.pairs_sample.map((p, k) => ({ k, km: p[2], s: p[yi] as number, same: !!p[5] })).filter((p) => subset === "all" || (subset === "same_atu") === p.same), [d, yi, subset]);
  const x = scaleLinear().domain([0, 20100]).range([m.l, W - m.r]);
  const ys = pts.map((p) => p.s);
  const y = scaleLinear().domain([Math.min(...ys), Math.max(...ys)]).nice().range([H - m.b, m.t]);
  useEffect(() => {
    const c = ref.current!;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    c.width = W * dpr; c.height = H * dpr;
    const ctx = c.getContext("2d")!;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.font = "10px Inter Variable, sans-serif"; ctx.fillStyle = "#6b767c";
    y.ticks(4).forEach((t) => { ctx.fillText(t.toFixed(2), 6, y(t) + 3); ctx.strokeStyle = "#e3d8c4"; ctx.beginPath(); ctx.moveTo(m.l, y(t)); ctx.lineTo(W - m.r, y(t)); ctx.stroke(); });
    x.ticks(5).forEach((t) => ctx.fillText(`${t / 1000}k`, x(t) - 8, H - m.b + 14));
    ctx.fillText("distance (km)", W / 2 - 30, H - 4);
    for (const p of pts) {
      ctx.fillStyle = p.same ? "rgba(180,83,42,0.55)" : "rgba(85,99,107,0.18)";
      ctx.fillRect(x(p.km) - 1.5, y(p.s) - 1.5, 3, 3);
    }
    if (picked !== null) {
      const p = d.pairs_sample[picked];
      ctx.strokeStyle = "#1d2b33"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(x(p[2]), y(p[yi] as number), 7, 0, Math.PI * 2); ctx.stroke();
    }
  }, [pts, picked, d, yi, x, y]);
  return (
    <canvas ref={ref} style={{ width: "100%", aspectRatio: `${W}/${H}`, cursor: "crosshair" }} role="img"
      aria-label={`Scatter of ${pts.length} displayed tale pairs: distance against ${rep} similarity. Click a point to read the pair.`}
      onClick={(e) => {
        const r = ref.current!.getBoundingClientRect();
        const mx = ((e.clientX - r.left) / r.width) * W, my = ((e.clientY - r.top) / r.height) * H;
        let best = -1, bd = 64;
        for (const p of pts) { const dd = (x(p.km) - mx) ** 2 + (y(p.s) - my) ** 2; if (dd < bd) { bd = dd; best = p.k; } }
        if (best >= 0) onPick(best);
      }} />
  );
}

export function DistanceChapter({ onRead }: { onRead: (a: string, b: string) => void }) {
  const dist = useData<DistancePayload>("distance.json");
  const cat = useData<CataloguePayload>("catalogue.json");
  const land = useLand(true);
  const [rep, setRep] = useState<Rep>("semantic");
  const [subset, setSubset] = useState<Subset>("all");
  const [picked, setPicked] = useState<number | null>(null);
  const rows = useMemo(() => new Map((cat.data ? catalogueRows(cat.data) : []).map((r) => [r.id, r])), [cat.data]);
  const points: MapPoint[] = useMemo(() => pointsByCoordinate([...rows.values()].filter((r) => r.in_distance), (reg) => REGION_COLOURS[reg ?? ""] ?? "#2d6a6a"), [rows]);
  const labelAt = (lat: number | null, lon: number | null) => points.find((p) => p.lat === lat && p.lon === lon)?.label ?? "";
  if (!dist.data || !cat.data) return <Loading what="distance results" />;
  const d = dist.data;
  const res = d.results[rep];
  const pp = picked !== null ? d.pairs_sample[picked] : null;
  const ra = pp ? rows.get(pp[0] as string) : undefined, rb = pp ? rows.get(pp[1] as string) : undefined;
  return (
    <div>
      <div className="row" style={{ marginBottom: 10 }}>
        <Segmented label="Representation" value={rep} onChange={(v) => { setRep(v); }} options={[{ value: "lexical", label: "TF–IDF" }, { value: "semantic", label: "Embeddings" }]} />
        <Segmented label="Pairs" value={subset} onChange={setSubset} options={[{ value: "all", label: "All pairs" }, { value: "same_atu", label: "Same ATU" }, { value: "different_atu", label: "Different ATU" }]} />
      </div>
      <div className="grid-2">
        <figure className="figure" style={{ margin: 0 }}>
          <div className="figure-title">Similarity by distance (all {int(d.pairs)} pairs)</div>
          <Curves d={d} rep={rep} />
          <div className="figure-title" style={{ marginTop: 10 }}>Each dot is a pair of tales — click to read it</div>
          <Scatter d={d} rep={rep} subset={subset} onPick={setPicked} picked={picked} />
          <p className="caption">Curves and statistics use every eligible pair. The scatter shows a disclosed display sample: all {int(d.display_sample.same_atu_pairs_all_included)} same-type pairs plus {int(d.display_sample.random_other_pairs)} random other pairs (seed {d.display_sample.seed}). Tales from the same country share one point, so they sit at 0 km.</p>
        </figure>
        <div>
          <figure className="figure" style={{ marginTop: 0 }}>
            <div className="figure-title">Recorded points{pp ? ": selected pair" : ""}</div>
            <CoverageMap land={land} points={points} height={280}
              highlight={ra && rb ? [labelAt(ra.lat, ra.lon), labelAt(rb.lat, rb.lon)] : []}
              lines={ra && rb && ra.lat != null && rb.lat != null ? [{ a: [ra.lat, ra.lon!], b: [rb.lat, rb.lon!] }] : []} />
            {pp && ra && rb ? (
              <div className="sans small">
                <p style={{ margin: "6px 0" }}><strong>{ra.title}</strong> ({ra.place}, ATU {ra.atu}) and <strong>{rb.title}</strong> ({rb.place}, ATU {rb.atu}) — {int(pp[2] as number)} km apart (approximate); {rep === "lexical" ? "TF–IDF" : "embedding"} similarity {fmt(pp[rep === "lexical" ? 3 : 4] as number)}.</p>
                <button className="btn small accent" onClick={() => onRead(ra.id, rb.id)}>Read this pair</button>
                <span className="muted" style={{ marginLeft: 8 }}>The dashed line marks the comparison, not a travel route.</span>
              </div>
            ) : <p className="caption">Click a dot in the scatter to show its two recorded points here.</p>}
          </figure>
          <figure className="figure">
            <div className="figure-title">Does similarity fall with distance? Spearman ρ = {fmt(res.spearman_rho)}</div>
            <NullHistogram values={res.spearman_null.values} observed={res.spearman_rho} label="Spearman rho against whole-location shuffles" colour="#b4532a" />
            <p className="caption">Grey: 1,000 reassignments of whole recorded locations to tales (each tale's location moves as one unit; pair distances are never shuffled independently). The observed correlation is {res.spearman_rho < res.spearman_null.min ? "more negative than every shuffle" : "within the shuffle range"}, but weak: same-type pairs are far more similar than different-type pairs at every distance.</p>
          </figure>
        </div>
      </div>
      <HowMade
        measured="Great-circle (haversine, R = 6371.0088 km) distance between the representative points of two tales' recorded countries, against their whole-tale cosine similarity."
        records={`Distance cohort: ${int(d.cohort_size)} tales at ${d.distinct_points} points; ${int(d.pairs)} pairs.`}
        method="Distance is a supporting calculation (not course material); the permutation idea follows the label-shuffle logic (week 2, §7; week 3 Goodies), moving whole locations."
        infer="A weak tendency for tales recorded far apart to be less similar in this sample, beyond what random location assignments produce."
        cannot="Transmission, migration, borrowing or direction of influence. Pairs share tales and sources, so no independence-based p-values are given; country points are approximations." />
    </div>
  );
}
