import { decodeFloat32 } from "./load";
import type { TalePayload } from "./types";

const DIM = 384;
const chunkCache = new WeakMap<TalePayload, Float32Array>();
const vecCache = new WeakMap<TalePayload, Float32Array>();

export function chunkVectors(t: TalePayload): Float32Array {
  let v = chunkCache.get(t);
  if (!v) { v = decodeFloat32(t.chunk_vectors); chunkCache.set(t, v); }
  return v;
}
export function taleVector(t: TalePayload): Float32Array {
  let v = vecCache.get(t);
  if (!v) { v = decodeFloat32(t.vector); vecCache.set(t, v); }
  return v;
}

function dot(a: Float32Array, ao: number, b: Float32Array, bo: number): number {
  let s = 0;
  for (let k = 0; k < DIM; k++) s += a[ao + k] * b[bo + k];
  return s;
}

/** Whole-tale semantic cosine (vectors are unit length). */
export function semanticCosine(a: TalePayload, b: TalePayload): number {
  return dot(taleVector(a), 0, taleVector(b), 0);
}

/** Whole-tale lexical cosine from the exported TF-IDF weights (L2-normalised). */
export function lexicalCosine(a: TalePayload, b: TalePayload): number {
  const m = new Map(a.tfidf);
  let s = 0;
  for (const [t, w] of b.tfidf) { const x = m.get(t); if (x !== undefined) s += x * w; }
  return s;
}

/** Shared terms ranked by their exact contribution w_a(t) * w_b(t) to the lexical cosine. */
export function sharedTerms(a: TalePayload, b: TalePayload, limit = 30): { term: string; contribution: number }[] {
  const m = new Map(a.tfidf);
  const out: { term: string; contribution: number }[] = [];
  for (const [t, w] of b.tfidf) { const x = m.get(t); if (x !== undefined) out.push({ term: t, contribution: x * w }); }
  out.sort((p, q) => q.contribution - p.contribution);
  return out.slice(0, limit);
}

/**
 * Text of one passage (chunk), or null when this build does not contain it.
 * Excerpt-only builds carry the opening of each tale plus the few passages the story quotes;
 * a passage cut off by the excerpt ends with an ellipsis.
 */
export function passageText(t: TalePayload, chunk: number): string | null {
  const quoted = t.passages?.[String(chunk)];
  if (quoted !== undefined) return quoted;
  const span = t.chunks[chunk];
  if (!span) return null;
  const [s, e] = span;
  if (!t.text_is_excerpt) return t.text.slice(s, e);
  if (s >= t.text.length) return null;
  return e > t.text.length ? `${t.text.slice(s)} …` : t.text.slice(s, e);
}

/** The text a build may show for a tale: all of it, or its opening followed by an ellipsis. */
export function shownText(t: TalePayload): string {
  return t.text_is_excerpt ? `${t.text} …` : t.text;
}

export interface PassageMatch { a: number; b: number; score: number }

/** Best-matching chunk pairs between two tales (cosine of chunk vectors), greedy distinct chunks. */
export function passageMatches(a: TalePayload, b: TalePayload, k = 3): { best: PassageMatch[]; all: PassageMatch[] } {
  const va = chunkVectors(a), vb = chunkVectors(b);
  const na = a.chunks.length, nb = b.chunks.length;
  const all: PassageMatch[] = [];
  for (let i = 0; i < na; i++) for (let j = 0; j < nb; j++) all.push({ a: i, b: j, score: dot(va, i * DIM, vb, j * DIM) });
  all.sort((p, q) => q.score - p.score);
  const usedA = new Set<number>(), usedB = new Set<number>(), best: PassageMatch[] = [];
  for (const m of all) {
    if (best.length >= k) break;
    if (usedA.has(m.a) || usedB.has(m.b)) continue;
    best.push(m); usedA.add(m.a); usedB.add(m.b);
  }
  return { best, all };
}
