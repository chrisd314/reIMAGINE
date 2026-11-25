import { useEffect, useState } from "react";

// The pipeline (python -m reimagine.run --stage site) writes three files into data/site/, copied into the build by
// scripts/copy-data.mjs. Every number on the site is read from them:
//   story.json    results of both representations, every parable / baseline passage / retelling
//   network.json  the folktale networks of both representations
//   near.json     nearest folktales of every tale and text, the words behind each match, openings (loaded lazily)

export type Kind = "parable" | "baseline";
export type Rep = "tfidf" | "embedding";
export const REP_NAME: Record<string, string> = { tfidf: "TF–IDF (words)", embedding: "Embeddings (meaning)", tfidf_nouns_masked: "TF–IDF, nouns masked", tfidf_masked: "TF–IDF, names masked", embedding_masked: "Embeddings, names masked" };

export interface Community { name: string; size: number; share: number; words: string; courseWords: string; lda: string; types: string; regions: string; collections: string }
export interface Organise { label: string; null: string; measure: "nmi" | "assortativity"; observed: number; nullMean: number; nullLow: number | null; nullHigh: number | null; excess: number; z: number; p: number; n: number }
export interface SweepRow {
  rep: Rep; by: string; value: number; key: string; canonical: boolean; edges: number; communities: number; modularity: number; nmiCanonical: number;
  type: number; region: number; collection: number; typeWithin: number; regionWithin: number;
}
export interface DensityStats { density: number; edges: number; threshold: number; components: number; largest: number; isolates: number; communities: number; major: number; modularity: number; nullMean: number; z: number }
export interface NetMap {
  x: number[]; y: number[]; group: number[]; degree: number[]; pagerank: number[]; pagerankZ: number[]; edges: number[]; communities: Community[];
  stats: { n: number; edges: number; threshold: number; modularity: number; nullMean: number; z: number; major: number; communities: number;
    components: number; isolates: number; largest: number; shuffles: number; seedNmiMin: number; seedNmiMax: number; density: number };
  densities: { stats: DensityStats[]; degrees: Record<string, number[]> };
  seeds: { partitions: Record<string, number[]>; nmi: Record<string, number> };
  partitions: Record<string, number[]>;
  structure: { measure: string; observed: number; null: string | null; nullMean: number | null; z: number | null; shuffles: number }[];
  organise: Organise[];
  labelTest: { nodes: number[]; part: number[] };
  backbone: { filtered: string; alpha: number; edgesIn: number; kept: number; nodes: number; within: number }[];
  archetypes: { node: number; title: string; atu: string; community: string; degree: number; pagerank: number; nullMean: number; z: number; null: number[] }[];
  degreeLength: { spearman: number; hubTokens: number; medianTokens: number };
}
export interface Network { reps: Rep[]; primary: Rep; maps: Record<Rep, NetMap>; sweep: { graphs: number; typeBeatsRegion: number; rows: SweepRow[] } }

export interface CalItem {
  id: string; title: string; tradition: string; collection: string; atu: string; atuName: string; opening: string;
  rank: number; vote: string; voteName: string; sameType: number; ranks: Record<Rep, number>; near: Record<Rep, { idx: number[]; cos: number[] }>;
}
export interface Calibration {
  queries: number; hits: number; recall: number; low: number; high: number; chance: number; vote: number; voteChance: number; k: number;
  byRep: Record<string, { recall: number; low: number; high: number; vote: number }>; other: Record<string, number>; options: number;
  items: CalItem[]; maxCosine: number;
}
export interface TextRep { closeness: number; nearest: number[]; cos: number[]; community: string | null; voted: string | null }
export interface Text {
  id: string; kind: Kind; tradition: string; title: string; tokens: number; source: string; year: string; url: string; opening: string;
  rep: Record<Rep, TextRep>;
}
export interface Headline {
  tradition: string; nPar: number; nBase: number; par: number; base: number; diff: number; low: number; high: number; p: number;
  closer: boolean; jsd: number; jsdNull: number; jsdP: number; differs: boolean; topCommunity: string; topExcess: number; topSig: boolean;
  topCollection: string; topCollectionShare: number;
}
export interface Cell { tradition: string; community: string; words: string; map: number; par: number; base: number; excess: number; p: number; sig: boolean }
export interface TypeRow { tradition: string; kind: Kind; rank: number; atu: string; name: string; share: number }
export interface RepResults {
  headline: Headline[]; cells: Cell[]; types: TypeRow[]; folkBand: { q25: number; q50: number; q75: number };
  lengthControl: { tradition: string; diff: number; low: number; high: number; above: number }[];
}
export interface Robust { variant: string; tradition: string; closer: boolean; p: number; diff: number }
export interface Table1Row { check: string; variant: string; holds: "yes" | "partly" | "no"; agreement: string; key: string }
export interface Driver { tradition: string; kind: Kind; terms: string; nounShare: number; percentile: number; percentileMasked: number }

export interface Story {
  built: string; commit: string; primary: Rep; reps: Rep[]; traditions: string[];
  settings: { permutations: number; closenessK: number; attachK: number; labelShuffles: number; openingWords: number; nearK: number };
  corpus: { folktales: number; calibration: number; typed: number; types: number; withRegion: number; regions: number; europeShare: number;
    collectionKnown: number; collections: number; translatorKnown: number; regionCounts: Record<string, number>; parables: number; baseline: number };
  sources: { tradition: string; kind: Kind; n: number; tokens: number; sources: string }[];
  folktales: { id: string[]; title: string[]; atu: string[]; atuName: string[]; region: string[]; collection: string[]; tokens: number[] };
  links: { typePages: Record<string, string[]>; index: string; dataset: string };
  calibration: Calibration;
  texts: Text[];
  byRep: Record<Rep, RepResults>;
  length: { matching: { tradition: string; par: number; base: number; p: number; matched: boolean }[]; slope: number; slopeP: number; orderRaw: string; orderEqual: string };
  drivers: Driver[];
  secondMethod: { scope: string; n: number; spearman: number; jaccard: number; sameNearest: number }[];
  robust: Robust[];
  table1: Table1Row[];
}
export interface Near {
  folk: Record<Rep, { idx: number[][]; cos: number[][]; words: string[][] }>;
  texts: Record<Rep, Record<string, string[]>>;
  opening: string[];
  calibrationOpening: Record<string, string>;
}

// ---------------------------------------------------------------- loading (each file once)
const cache = new Map<string, Promise<unknown>>();
function load<T>(name: string): Promise<T> {
  if (!cache.has(name)) {
    cache.set(name, fetch(`${import.meta.env.BASE_URL}data/${name}`).then((r) => {
      if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
      return r.json();
    }));
  }
  return cache.get(name) as Promise<T>;
}
function useFile<T>(name: string): { data: T | null; error: string | null } {
  const [state, setState] = useState<{ data: T | null; error: string | null }>({ data: null, error: null });
  useEffect(() => {
    let live = true;
    load<T>(name).then((data) => live && setState({ data, error: null }), (e: Error) => live && setState({ data: null, error: e.message }));
    return () => { live = false; };
  }, [name]);
  return state;
}
export const useStory = () => useFile<Story>("story.json");
export const useNetwork = () => useFile<Network>("network.json");
export const useNear = () => useFile<Near>("near.json");

// ---------------------------------------------------------------- helpers
/** Community name of a map group: groups 0..8 are C1..C9, -1 marks the small groups. */
export const communityOf = (g: number) => (g < 0 ? "small" : `C${g + 1}`);

/** A tale-type name without the catalogue's "(previously …)" notes, short enough for a chip or a list. */
export function shortType(name: string, max = 44): string {
  const s = name.replace(/\s*\(previously[^)]*\)/gi, "").replace(/\s*\[[^\]]*\]/g, "").trim();
  return s.length > max ? `${s.slice(0, max - 1).trimEnd()}…` : s;
}

/** The ATU chapter of a tale-type number (Uther 2004). */
export const ATU_CHAPTERS: { name: string; lo: number; hi: number }[] = [
  { name: "Animal tales", lo: 1, hi: 299 },
  { name: "Tales of magic", lo: 300, hi: 749 },
  { name: "Religious tales", lo: 750, hi: 849 },
  { name: "Realistic tales", lo: 850, hi: 999 },
  { name: "Tales of the stupid ogre", lo: 1000, hi: 1199 },
  { name: "Anecdotes and jokes", lo: 1200, hi: 1999 },
  { name: "Formula tales", lo: 2000, hi: 2399 },
];
export function atuChapter(atu: string): string {
  const n = parseInt(atu, 10);
  return ATU_CHAPTERS.find((c) => n >= c.lo && n <= c.hi)?.name ?? "";
}

/** Where to read a folktale in full: the page(s) of D. L. Ashliman's Folktexts it was taken from (the corpus took
 *  every tale from the page of its tale type), opened at its title; else the collection's index. */
export function readLinks(links: Story["links"], atu: string, title: string): { href: string; label: string }[] {
  const t = title.replace(/\s*\([^)]*\)\s*$/, "").trim();
  const frag = t ? `#:~:text=${encodeURIComponent(t)}` : "";
  const pages = atu ? links.typePages[atu] : undefined;
  if (!pages || !pages.length) return [{ href: links.index, label: "Folktexts index" }];
  return pages.map((p, k) => ({ href: p + frag, label: pages.length > 1 ? `Folktexts page ${k + 1}` : "Read it on Folktexts" }));
}
