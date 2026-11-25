// Small statistics for the shuffles that run in the browser. NMI follows scikit-learn's arithmetic normalisation,
// the definition the pipeline uses, so the observed values here equal the published ones.

/** Integer codes of a list of labels. */
export function codes(values: ArrayLike<string | number>): Int32Array {
  const seen = new Map<string | number, number>();
  const out = new Int32Array(values.length);
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (!seen.has(v)) seen.set(v, seen.size);
    out[i] = seen.get(v)!;
  }
  return out;
}

function entropy(counts: Iterable<number>, n: number): number {
  let h = 0;
  for (const c of counts) if (c > 0) { const p = c / n; h -= p * Math.log(p); }
  return h;
}

/** Normalised mutual information, MI / mean(H(a), H(b)). */
export function nmi(a: ArrayLike<number>, b: ArrayLike<number>): number {
  const n = a.length;
  const ca = new Map<number, number>(), cb = new Map<number, number>(), cab = new Map<string, number>();
  for (let i = 0; i < n; i++) {
    ca.set(a[i], (ca.get(a[i]) ?? 0) + 1);
    cb.set(b[i], (cb.get(b[i]) ?? 0) + 1);
    const k = `${a[i]}|${b[i]}`;
    cab.set(k, (cab.get(k) ?? 0) + 1);
  }
  const ha = entropy(ca.values(), n), hb = entropy(cb.values(), n);
  if (ha === 0 && hb === 0) return 1;
  let mi = 0;
  for (const [k, c] of cab) {
    const [x, y] = k.split("|").map(Number);
    mi += (c / n) * Math.log((c * n) / ((ca.get(x) as number) * (cb.get(y) as number)));
  }
  const denom = (ha + hb) / 2;
  return denom > 0 ? Math.max(0, mi / denom) : 0;
}

/** A seeded generator (xorshift). */
export function rng(seed: number) {
  let s = seed >>> 0 || 1;
  return () => { s ^= s << 13; s >>>= 0; s ^= s >>> 17; s ^= s << 5; s >>>= 0; return s / 4294967296; };
}

/** Fisher–Yates shuffle of a copy. */
export function shuffled<T>(arr: ArrayLike<T>, rand: () => number): T[] {
  const out = Array.from(arr);
  for (let i = out.length - 1; i > 0; i--) { const j = Math.floor(rand() * (i + 1)); [out[i], out[j]] = [out[j], out[i]]; }
  return out;
}

/** Shuffle values only among positions of the same stratum (a stratum with one member never moves). */
export function shuffledWithin<T>(arr: ArrayLike<T>, strata: ArrayLike<string | number>, rand: () => number): T[] {
  const out = Array.from(arr);
  const groups = new Map<string | number, number[]>();
  for (let i = 0; i < strata.length; i++) { const g = strata[i]; if (!groups.has(g)) groups.set(g, []); groups.get(g)!.push(i); }
  for (const idx of groups.values()) {
    const vals = shuffled(idx.map((i) => arr[i]), rand);
    idx.forEach((i, k) => { out[i] = vals[k]; });
  }
  return out;
}

export function median(xs: number[]): number {
  const s = [...xs].sort((a, b) => a - b), n = s.length;
  return n === 0 ? NaN : n % 2 ? s[(n - 1) / 2] : (s[n / 2 - 1] + s[n / 2]) / 2;
}
