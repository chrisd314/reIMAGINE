// Same formulas as analysis/metrics.py (normalised mutual information, arithmetic normalisation).

export function codes(values: (string | null)[]): Int32Array {
  const map = new Map<string, number>();
  const out = new Int32Array(values.length);
  values.forEach((v, i) => {
    const key = v ?? "∅";
    if (!map.has(key)) map.set(key, map.size);
    out[i] = map.get(key)!;
  });
  return out;
}

function entropy(counts: number[], n: number): number {
  let h = 0;
  for (const c of counts) if (c > 0) { const p = c / n; h -= p * Math.log(p); }
  return h;
}

export function nmi(a: ArrayLike<number>, b: ArrayLike<number>): number {
  const n = a.length;
  let ka = 0, kb = 0;
  for (let i = 0; i < n; i++) { if (a[i] + 1 > ka) ka = a[i] + 1; if (b[i] + 1 > kb) kb = b[i] + 1; }
  const cont = new Float64Array(ka * kb);
  const ra = new Array(ka).fill(0), rb = new Array(kb).fill(0);
  for (let i = 0; i < n; i++) { cont[a[i] * kb + b[i]]++; ra[a[i]]++; rb[b[i]]++; }
  const ha = entropy(ra, n), hb = entropy(rb, n);
  if (ha === 0 && hb === 0) return 1;
  let mi = 0;
  for (let x = 0; x < ka; x++) for (let y = 0; y < kb; y++) {
    const c = cont[x * kb + y];
    if (c > 0) mi += (c / n) * Math.log((c * n) / (ra[x] * rb[y]));
  }
  return ha + hb > 0 ? (2 * mi) / (ha + hb) : 0;
}

/** Fisher–Yates shuffle with a small seeded generator (mulberry32). */
export function shuffled<T>(arr: ArrayLike<T>, seed: number): T[] {
  const out = Array.from(arr);
  let s = seed >>> 0;
  const rnd = () => { s += 0x6d2b79f5; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  for (let i = out.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [out[i], out[j]] = [out[j], out[i]]; }
  return out;
}

export function quantile(sorted: number[], q: number): number {
  if (!sorted.length) return NaN;
  const p = (sorted.length - 1) * q, lo = Math.floor(p), hi = Math.ceil(p);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (p - lo);
}
