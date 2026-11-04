export const fmt = (v: number | null | undefined, d = 3) => (v === null || v === undefined || Number.isNaN(v) ? "–" : v.toFixed(d));
export const pct = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? "–" : `${(v * 100).toFixed(d)}%`);
export const int = (v: number | null | undefined) => (v === null || v === undefined ? "–" : Math.round(v).toLocaleString("en-GB"));
export const times = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? "–" : `${v.toFixed(d)}×`);
export const densityLabel = (d: number) => `${Math.round(d * 100)}%`;
export const repLabel = (r: string) =>
  ({ lexical: "TF–IDF (words)", semantic: "Embeddings (meaning)", lexical_names: "TF–IDF, names masked",
     semantic_tokw: "Embeddings, token-weighted pooling", semantic_c128: "Embeddings, 128-token chunks" } as Record<string, string>)[r] ?? r;
export const labelName = (l: string) =>
  ({ atu: "ATU tale type", place: "Place (country/community)", region: "Broad region (UN M49)", source: "Bibliographic source (diagnostic)" } as Record<string, string>)[l] ?? l;
export const cohortName = (c: string) =>
  ({ joint: "Joint cohort", text: "All usable tales", joint_balanced: "Region-balanced subset", joint_nodup: "Near-duplicates removed",
     joint_nofrag: "Suspected fragments removed" } as Record<string, string>)[c] ?? c;
