import { useEffect, useState } from "react";
import type { CatalogueRow, CataloguePayload, ManifestPayload, Stamp } from "./types";

const BASE = `${import.meta.env.BASE_URL}data/`;
const cache = new Map<string, Promise<unknown>>();
let manifestRun: string | null = null;
const mismatchListeners = new Set<(msg: string) => void>();

export function onRunMismatch(fn: (msg: string) => void) {
  mismatchListeners.add(fn);
  return () => { mismatchListeners.delete(fn); };
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(BASE + path);
  if (!res.ok) throw new Error(`Could not load ${path} (HTTP ${res.status})`);
  return (await res.json()) as T;
}

export function loadManifest(): Promise<ManifestPayload> {
  return load<ManifestPayload>("manifest.json");
}

/** Cached JSON loader. Every payload must carry the same run_id as the manifest. */
export function load<T extends Stamp | object>(path: string): Promise<T> {
  if (!cache.has(path)) {
    const p = (async () => {
      const data = await fetchJson<T>(path);
      const run = (data as Partial<Stamp>).run_id;
      if (path === "manifest.json") manifestRun = run ?? null;
      else if (run) {
        if (!manifestRun) {
          const m = await loadManifest();
          manifestRun = m.run_id;
        }
        if (manifestRun && run !== manifestRun) {
          mismatchListeners.forEach((fn) => fn(`${path} comes from run ${run}, but the site manifest is ${manifestRun}.`));
        }
      }
      return data;
    })();
    p.catch(() => cache.delete(path));
    cache.set(path, p);
  }
  return cache.get(path) as Promise<T>;
}

export interface Loaded<T> { data: T | null; error: string | null; loading: boolean }

export function useData<T extends object>(path: string | null): Loaded<T> {
  const [state, setState] = useState<Loaded<T>>({ data: null, error: null, loading: !!path });
  useEffect(() => {
    if (!path) { setState({ data: null, error: null, loading: false }); return; }
    let alive = true;
    setState((s) => ({ data: s.data && (s.data as unknown as { __path?: string }).__path === path ? s.data : null, error: null, loading: true }));
    load<T>(path).then(
      (d) => { if (alive) setState({ data: d, error: null, loading: false }); },
      (e: Error) => { if (alive) setState({ data: null, error: e.message, loading: false }); },
    );
    return () => { alive = false; };
  }, [path]);
  return state;
}

export function catalogueRows(p: CataloguePayload): CatalogueRow[] {
  return p.rows.map((r) => Object.fromEntries(p.fields.map((f, i) => [f, r[i]])) as unknown as CatalogueRow);
}

export function decodeFloat32(b64: string): Float32Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Float32Array(bytes.buffer);
}

export const taleUrl = (id: string) => `tales/${id}.json`;
export const graphUrl = (cohort: string, rep: string, density: number) =>
  `graphs/${cohort}-${rep}-d${String(Math.round(density * 100)).padStart(2, "0")}.json`;
