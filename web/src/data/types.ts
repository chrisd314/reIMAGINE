// Payload types mirror analysis/export.py (schema_version 1.0.0).

export interface Stamp { run_id: string; schema_version: string }

export type Rep = "lexical" | "semantic";
export type Cohort = "joint" | "text";
export type LabelSystem = "atu" | "place" | "region" | "source";

export interface NullSummary {
  observed: number; null_mean: number; null_sd: number; null_p95: number; null_p99: number; null_max: number;
  excess: number; z: number | null; p_upper: number; exceeds_all: boolean;
}

export interface AgreementRow {
  graph_id: string; group: string; cohort: string; rep: string; density: number; seed: number; label: LabelSystem;
  diagnostic: boolean; categories: number; nmi: NullSummary; assortativity: NullSummary; same_label_edge_share: NullSummary;
  non_isolates?: { n: number; isolates: number; nmi: NullSummary; categories: number };
}

export interface GraphPayload extends Stamp {
  graph_id: string; group: string; cohort: string; rep: string; density: number; n: number; m: number; m_target: number;
  density_achieved: number; similarity_threshold: number; components: number; largest_component: number;
  isolates: string[]; mean_degree: number; seed_agreement_nmi: Record<string, number>;
  nodes: string[]; partitions: Record<string, number[]>; colour_index: Record<string, number[]>;
  partition_stats: Record<string, { communities: number; modularity: number; sizes: number[] }>;
  colour_reference: string; backbone: [number, number, number][]; backbone_rule: string;
  top_edges: [number, number][][]; top_edges_rule: string; degree: number[]; strength: number[];
  modularity_null: null | { observed: number; shuffles: number; null_mean: number; null_sd: number; null_min: number; null_max: number; difference: number; z: number | null; values: number[]; preserved: string; randomised: string };
}

export interface LayoutPayload extends Stamp {
  cohort: Cohort; nodes: string[]; shared: [number, number][]; lexical: [number, number][]; semantic: [number, number][];
  pca: [number, number][]; pca_explained_variance: number[]; notes: Record<string, string>;
}

export interface CatalogueRow {
  id: string; title: string; atu: string | null; atu_name: string | null; atu_chapter: string | null;
  place: string | null; region: string | null; provenance: string; entity_kind: string; source_key: string;
  n_words: number; in_atu: boolean; in_joint: boolean; in_distance: boolean; lat: number | null; lon: number | null;
  n_records: number; flags: string[]; fragment: boolean; geo_status: string;
}

export interface CataloguePayload extends Stamp {
  fields: string[]; rows: unknown[][];
  excluded_records: { record_id: string; title: string; atu_id: string; provenance: string; excluded_reason: string }[];
}

export interface TalePayload extends Stamp {
  id: string; title: string; titles: string[]; record_ids: string[]; n_words: number;
  /** Full text, or (excerpt-only builds) a verbatim prefix of it, so `chunks` offsets stay valid for the part kept. */
  text: string; text_is_excerpt: boolean;
  /** Excerpt-only builds: full text of the few passages the story quotes, keyed by chunk index. */
  passages?: Record<string, string>;
  atu: { id: string | null; ids: string[]; name: string | null; chapter: string | null; status: string };
  provenance: {
    raw: string[]; label: string[]; kinds: string[]; status: string; place: string | null; place_kind: string | null;
    detail: string | null; region: string | null; confidence: string | null; lat: number | null; lon: number | null;
    coordinate_meaning: string | null;
  };
  source: string | null; sources: string[]; source_key: string; notes: string | null; flags: string[];
  cohorts: { text: boolean; atu: boolean; joint: boolean; distance: boolean };
  exclusion_reasons: string; near_duplicates: string[];
  chunks: [number, number, number][]; chunk_vectors: string; vector: string;
  tfidf: [string, number][]; frequencies: [string, number][]; n_tokens_lexical: number;
  neighbours: Partial<Record<Cohort, Partial<Record<Rep, [string, number][]>>>>;
}

export interface NeighbourCategory { category: string; n: number; rate: number; baseline: number }
export interface NeighbourEntry {
  mean_rate: number; mean_baseline: number; lift: number; mean_rate_excl_same_source: number;
  mean_baseline_excl_same_source: number; lift_excl_same_source: number; share_of_categories_above_baseline: number;
  per_category: NeighbourCategory[];
}
export interface NeighbourStats extends Stamp {
  k: number; results: Record<string, { atu: NeighbourEntry; place: NeighbourEntry; region: NeighbourEntry; share_neighbours_same_source: number }>;
}

export interface DistanceCurveRow { bin: string; pairs: number; mean: number | null; q25: number | null; median: number | null; q75: number | null }
export interface DistancePayload extends Stamp {
  cohort_size: number; pairs: number; distinct_points: number; earth_radius_km: number; formula: string; coordinate_meaning: string;
  bins: string[];
  results: Record<Rep, {
    all: { curve: DistanceCurveRow[]; pairs: number }; same_atu: { curve: DistanceCurveRow[]; pairs: number };
    different_atu: { curve: DistanceCurveRow[]; pairs: number }; spearman_rho: number;
    spearman_null: { mean: number; sd: number; p2_5: number; p97_5: number; min: number; max: number; share_at_least_as_negative: number; values: number[] };
    mean_similarity_same_point: number; mean_similarity_different_point: number;
  }>;
  display_sample: { pairs: number; same_atu_pairs_all_included: number; random_other_pairs: number; seed: number };
  pairs_sample: [string, string, number, number, number, boolean][]; pairs_sample_fields: string[];
}

export interface ValidationPayload extends Stamp {
  status: string; annotations: Record<string, unknown>; rubric: Record<string, string>; aspects: string[]; values: string[];
  items: { item_id: string; split: string; a: string; b: string }[];
}

export interface SummaryPayload extends Stamp {
  generated: string;
  run: { run_id: string; created: string; config_hash: string; versions: Record<string, string>; cohort_sizes: Record<string, number> };
  counts: Record<string, number>;
  audit: Record<string, { expected: number; measured: number; match: boolean }>;
  cleaning: { removals_by_rule: Record<string, number>; records_with_removals: number; words_removed: number; mojibake_repaired_texts: number; excluded_non_narrative: { record_id: string; excluded_reason: string }[]; flags: Record<string, number> };
  lexical: Record<string, unknown> & { vocabulary_size: number; vocabulary_size_names_masked: number };
  semantic: Record<string, unknown> & { model: string; revision: string; dimension: number; settings: Record<string, { max_tokens: number; chunks: number; max_observed_tokens: number; median_tokens: number }> };
  graphs: {
    graph_id: string; group: string; cohort: string; rep: string; density: number; n: number; m: number;
    isolates: number; communities: number; modularity: number; seed_agreement_nmi: Record<string, number>;
    modularity_null: null | { null_mean: number; null_sd: number; shuffles: number; z: number | null };
  }[];
  primary: { density: number; seed: number };
  config: { densities: number[]; seeds: number[]; permutations: number; balanced_cap: number };
  layouts: Record<string, { pca_explained_variance: number[]; backbone_edges: Record<string, number>; shared_edges: number }>;
  validation_status: string; full_texts_included: boolean; excerpt_words?: number; public_build?: boolean;
  opening: null | { a: string; b: string; a_chunk: number; b_chunk: number; note: string };
  story_pairs: Record<string, { a: string; b: string; note: string }>;
}

export interface MappingPayload extends Stamp { fields: string[]; rows: string[][] }
export interface SourcesPayload extends Stamp {
  manifest: { trilogy_repository: string; trilogy_commit: string; files: { filename: string; url: string; version: string; retrieved_at: string; sha256: string; bytes: number; format: string; role: string; citation: string; stated_licence: string }[] };
  model: { name: string; revision: string; licence: string; url: string };
}
export interface NullsPayload extends Stamp { nmi: Record<string, number[]> }
export interface AgreementPayload extends Stamp { rows: AgreementRow[] }
export interface ManifestPayload extends Stamp {
  generated: string; tales: number; files: Record<string, { bytes: number }>;
  full_texts_included?: boolean; public_build?: boolean;
}
