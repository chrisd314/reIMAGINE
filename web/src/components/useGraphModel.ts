import { useEffect, useMemo, useState } from "react";
import { catalogueRows, graphUrl, useData } from "../data/load";
import type { CatalogueRow, CataloguePayload, Cohort, GraphPayload, LayoutPayload, Rep } from "../data/types";
import { ATU_CHAPTER_COLOURS, ATU_CHAPTER_ORDER, communityColour, REGION_COLOURS, REGION_ORDER, UNKNOWN } from "../lib/colours";
import { loadLand, spiralOffset, worldProjection } from "../lib/geo";
import { WORLD_H, WORLD_W } from "./NetworkCanvas";
import type { FeatureCollection, Geometry } from "geojson";

export type LayoutMode = "network" | "relayout" | "pca" | "places" | "places_collapsed";
export type ColourBy = "community" | "atu" | "region";

export function fitToWorld(xy: [number, number][], pad = 24): Float32Array {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of xy) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  const s = Math.min((WORLD_W - 2 * pad) / Math.max(x1 - x0, 1e-9), (WORLD_H - 2 * pad) / Math.max(y1 - y0, 1e-9));
  const ox = (WORLD_W - (x1 - x0) * s) / 2, oy = (WORLD_H - (y1 - y0) * s) / 2;
  const out = new Float32Array(xy.length * 2);
  xy.forEach(([x, y], i) => { out[2 * i] = ox + (x - x0) * s; out[2 * i + 1] = oy + (y - y0) * s; });
  return out;
}

export function useLand(enabled: boolean) {
  const [land, setLand] = useState<FeatureCollection<Geometry> | null>(null);
  useEffect(() => { if (enabled && !land) loadLand().then(setLand); }, [enabled, land]);
  return land;
}

export interface GraphModel {
  ready: boolean; error: string | null;
  nodes: string[]; index: Map<string, number>; rows: (CatalogueRow | undefined)[];
  layout: LayoutPayload | null; graph: GraphPayload | null;
  positions: Float32Array; colours: string[]; visible: boolean[] | undefined;
  legend: { title: string; ring: boolean; items: { label: string; colour: string; count?: number }[] };
  communities: number[]; markers: { x: number; y: number; count: number; label: string }[];
  located: boolean[]; catalogue: Map<string, CatalogueRow>;
}

export function useGraphModel(opts: { cohort: Cohort; rep: Rep; density: number; colourBy: ColourBy; layoutMode: LayoutMode; seed?: number; labelOverride?: (string | null)[] | null }): GraphModel {
  const { cohort, rep, density, colourBy, layoutMode } = opts;
  const seed = String(opts.seed ?? 42);
  const lay = useData<LayoutPayload>(`layouts/${cohort}.json`);
  const gr = useData<GraphPayload>(graphUrl(cohort, rep, density));
  const cat = useData<CataloguePayload>("catalogue.json");
  const catalogue = useMemo(() => new Map((cat.data ? catalogueRows(cat.data) : []).map((r) => [r.id, r])), [cat.data]);
  const nodes = lay.data?.nodes ?? [];
  const index = useMemo(() => new Map(nodes.map((id, i) => [id, i])), [nodes]);
  const rows = useMemo(() => nodes.map((id) => catalogue.get(id)), [nodes, catalogue]);

  const proj = useMemo(() => worldProjection(), []);
  const placesPositions = useMemo(() => {
    const collapsed = new Float32Array(nodes.length * 2), expanded = new Float32Array(nodes.length * 2);
    const groups = new Map<string, number[]>();
    rows.forEach((r, i) => {
      if (r?.lat != null && r?.lon != null && r.in_distance) {
        const key = `${r.lat},${r.lon}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key)!.push(i);
      }
    });
    const markers: { x: number; y: number; count: number; label: string }[] = [];
    const located = nodes.map(() => false);
    groups.forEach((members) => {
      const r0 = rows[members[0]]!;
      const [x, y] = proj([r0.lon!, r0.lat!]) ?? [0, 0];
      markers.push({ x, y, count: members.length, label: r0.place ?? "" });
      members.sort((a, b) => nodes[a].localeCompare(nodes[b])).forEach((i, rank) => {
        const [dx, dy] = spiralOffset(rank);
        collapsed[2 * i] = x; collapsed[2 * i + 1] = y;
        expanded[2 * i] = x + dx; expanded[2 * i + 1] = y + dy;
        located[i] = true;
      });
    });
    // unlocated tales park at the bottom edge (they are hidden in place modes)
    rows.forEach((_, i) => { if (!located[i]) { collapsed[2 * i] = expanded[2 * i] = WORLD_W / 2; collapsed[2 * i + 1] = expanded[2 * i + 1] = WORLD_H + 40; } });
    return { collapsed, expanded, markers, located };
  }, [rows, nodes, proj]);

  const positions = useMemo(() => {
    if (!lay.data) return new Float32Array(0);
    switch (layoutMode) {
      case "pca": return fitToWorld(lay.data.pca);
      case "relayout": return fitToWorld(lay.data[rep]);
      case "places": return placesPositions.expanded;
      case "places_collapsed": return placesPositions.collapsed;
      default: return fitToWorld(lay.data.shared);
    }
  }, [lay.data, layoutMode, rep, placesPositions]);

  const communities = useMemo(() => {
    if (!gr.data || !lay.data) return [] as number[];
    const gi = new Map(gr.data.nodes.map((id, i) => [id, i]));
    return nodes.map((id) => gr.data!.partitions[seed][gi.get(id)!]);
  }, [gr.data, lay.data, nodes, seed]);

  const { colours, legend } = useMemo(() => {
    const items = new Map<string, { label: string; colour: string; count: number }>();
    let cols: string[] = [];
    let title = "";
    let ring = false;
    if (colourBy === "community" && gr.data) {
      const sizes = gr.data.partition_stats[seed].sizes;
      const cidx = gr.data.colour_index[seed];
      cols = communities.map((c) => (c === undefined ? UNKNOWN : communityColour(cidx[c], sizes[c])));
      title = `Discovered communities (Louvain, seed ${seed})`;
      ring = true;
      communities.forEach((c) => {
        if (c === undefined) return;
        const big = sizes[c] >= 5;
        const label = big ? `Community ${cidx[c] + 1}` : "Small communities and isolates (< 5)";
        const colour = communityColour(cidx[c], sizes[c]);
        const it = items.get(label) ?? { label, colour, count: 0 };
        it.count++; items.set(label, it);
      });
    } else {
      const labels = opts.labelOverride ?? rows.map((r) => (colourBy === "atu" ? r?.atu_chapter ?? null : r?.region ?? null));
      const palette = colourBy === "atu" ? ATU_CHAPTER_COLOURS : REGION_COLOURS;
      const order = colourBy === "atu" ? ATU_CHAPTER_ORDER : REGION_ORDER;
      cols = labels.map((l) => (l ? palette[l] ?? UNKNOWN : UNKNOWN));
      title = colourBy === "atu" ? "Recorded label: ATU chapter (tale family group)" : "Recorded label: broad region (UN M49)";
      labels.forEach((l) => {
        const label = l ?? "unknown / not defensible";
        const it = items.get(label) ?? { label, colour: l ? palette[l] ?? UNKNOWN : UNKNOWN, count: 0 };
        it.count++; items.set(label, it);
      });
      const sorted = [...items.values()].sort((a, b) => (order.indexOf(a.label) + 1 || 99) - (order.indexOf(b.label) + 1 || 99));
      return { colours: cols, legend: { title, ring, items: sorted } };
    }
    const sorted = [...items.values()].sort((a, b) => b.count - a.count);
    return { colours: cols, legend: { title, ring, items: sorted } };
  }, [colourBy, gr.data, communities, rows, seed, opts.labelOverride]);

  const visible = useMemo(() => (layoutMode === "places" || layoutMode === "places_collapsed" ? placesPositions.located : undefined),
    [layoutMode, placesPositions]);

  return {
    ready: !!(lay.data && gr.data && cat.data), error: lay.error || gr.error || cat.error,
    nodes, index, rows, layout: lay.data, graph: gr.data, positions, colours, visible, legend, communities,
    markers: placesPositions.markers, located: placesPositions.located, catalogue,
  };
}

/** Map a graph's top-edge list (graph node order) into model node indices. */
export function focusEdgesFor(model: GraphModel, selected: number | null, limit = 20): [number, number, number][] {
  if (selected == null || !model.graph) return [];
  const gidx = model.graph.nodes.indexOf(model.nodes[selected]);
  if (gidx < 0) return [];
  return model.graph.top_edges[gidx].slice(0, limit).map(([j, w]) => [selected, model.index.get(model.graph!.nodes[j])!, w] as [number, number, number]);
}

export function backboneEdges(model: GraphModel): [number, number, number][] {
  if (!model.graph) return [];
  const g = model.graph;
  const map = g.nodes.map((id) => model.index.get(id)!);
  return g.backbone.map(([i, j, w]) => [map[i], map[j], w] as [number, number, number]);
}
