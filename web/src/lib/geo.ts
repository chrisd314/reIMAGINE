import { geoEqualEarth, geoPath, type GeoProjection } from "d3";
import { feature } from "topojson-client";
import type { FeatureCollection, Geometry } from "geojson";
import { WORLD_H, WORLD_W } from "../components/NetworkCanvas";

let landPromise: Promise<FeatureCollection<Geometry>> | null = null;

/** Natural Earth 1:110m land (world-atlas), loaded lazily. */
export function loadLand(): Promise<FeatureCollection<Geometry>> {
  if (!landPromise) {
    landPromise = import("world-atlas/land-110m.json").then((m) => {
      const topo = (m as unknown as { default: unknown }).default ?? m;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const t = topo as any;
      return feature(t, t.objects.land) as unknown as FeatureCollection<Geometry>;
    });
  }
  return landPromise;
}

/** Equal Earth projection fitted to the shared world space (same space as network layouts). */
export function worldProjection(): GeoProjection {
  return geoEqualEarth().fitExtent([[10, 10], [WORLD_W - 10, WORLD_H - 10]], { type: "Sphere" } as never);
}

export function drawLand(land: FeatureCollection<Geometry>, proj: GeoProjection) {
  return (ctx: CanvasRenderingContext2D, alpha: number) => {
    const path = geoPath(proj, ctx);
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.beginPath();
    path({ type: "Sphere" } as never);
    ctx.fillStyle = "#eef0ea";
    ctx.fill();
    ctx.beginPath();
    path(land);
    ctx.fillStyle = "#ddd3bf";
    ctx.fill();
    ctx.lineWidth = 0.6;
    ctx.strokeStyle = "#c6b99e";
    ctx.stroke();
    ctx.restore();
  };
}

const GOLDEN = Math.PI * (3 - Math.sqrt(5));

/**
 * Deterministic display displacement: tales that share one representative point are
 * spread on a phyllotaxis spiral around it (rank order = sorted narrative IDs).
 * This is drawing displacement only, never a location claim.
 */
export function spiralOffset(rank: number, spacing = 3.4): [number, number] {
  if (rank === 0) return [0, 0];
  const r = spacing * Math.sqrt(rank);
  const a = rank * GOLDEN;
  return [r * Math.cos(a), r * Math.sin(a)];
}

/** Great-circle distance (haversine), same radius as the pipeline. */
export function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number, R = 6371.0088): number {
  const toRad = Math.PI / 180;
  const dphi = (lat2 - lat1) * toRad, dl = (lon2 - lon1) * toRad;
  const a = Math.sin(dphi / 2) ** 2 + Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) * Math.sin(dl / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
}
