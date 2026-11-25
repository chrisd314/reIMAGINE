// Number formatting shared by every chapter. Every number shown comes from story.json.

export const fmt = (v: number | null | undefined, d = 3) => (v === null || v === undefined || Number.isNaN(v) ? "–" : v.toFixed(d));
export const int = (v: number | null | undefined) => (v === null || v === undefined ? "–" : Math.round(v).toLocaleString("en-GB"));
export const pct = (v: number | null | undefined, d = 0) => (v === null || v === undefined ? "–" : `${(v * 100).toFixed(d)}%`);
export const signed = (v: number, d = 3) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(d)}`;
/** Percentage points, signed: 0.17 -> "+17 pts". */
export const points = (v: number) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(Math.round(v * 100))} pts`;

/** The smallest p-value a permutation test can give, 1/(permutations + 1), written against the next one-digit bound: "< 0.001" for 1,000 shuffles. */
export function pMin(permutations: number): string {
  const floor = 1 / (permutations + 1);
  const step = 10 ** Math.floor(Math.log10(floor));
  const bound = Math.ceil(floor / step) * step;
  return `${floor < bound ? "<" : "≤"} ${Number(bound.toPrecision(1))}`;
}

/** A permutation p-value. The smallest value the test can give reads "p < 0.001", as in the report. */
export function pval(p: number, permutations: number): string {
  if (p < 1.5 / (permutations + 1)) return `p ${pMin(permutations)}`;   // p is stored rounded
  return `p = ${p < 0.01 ? p.toFixed(3) : p.toFixed(2)}`;
}

export function ordinal(n: number): string {
  const t = n % 100, u = n % 10;
  return `${n}${t >= 11 && t <= 13 ? "th" : u === 1 ? "st" : u === 2 ? "nd" : u === 3 ? "rd" : "th"}`;
}

/** "A", "A and B", "A, B and C". */
export function list(items: string[], none = "none"): string {
  if (items.length === 0) return none;
  if (items.length === 1) return items[0];
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** A small deterministic random generator, so the game and the jitter look the same on every visit. */
export function rng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}

export function hash01(s: string) {
  let h = 2166136261;
  for (const c of s) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); }
  return ((h >>> 0) % 1000) / 1000;
}
