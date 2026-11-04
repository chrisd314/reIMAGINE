import { useEffect, useMemo, useRef, useState } from "react";
import { load, taleUrl, useData } from "../data/load";
import type { Cohort, ManifestPayload, Rep, TalePayload } from "../data/types";
import { NetworkCanvas, type NetworkCanvasHandle } from "../components/NetworkCanvas";
import { backboneEdges, focusEdgesFor, useGraphModel, useLand, type ColourBy, type LayoutMode } from "../components/useGraphModel";
import { NeighbourList, TaleDetails, type NeighbourItem } from "../components/TalePanel";
import { PairReader } from "../components/PairReader";
import { copyLink, downloadDataUrl, downloadText, ErrorState, HowMade, Legend, Loading, Segmented, toCsv } from "../components/ui";
import { drawLand, worldProjection } from "../lib/geo";
import { cohortName, densityLabel, fmt, int, repLabel } from "../lib/format";
import { ATU_CHAPTER_ORDER, REGION_ORDER } from "../lib/colours";
import { buildHash, type Route } from "../lib/router";

const DEFAULTS = { cohort: "joint", rep: "semantic", d: "10", colour: "community", layout: "network", seed: "42", view: "network" };

export function Explore({ route, navigate }: { route: Route; navigate: (p: string, params?: Record<string, string | null | undefined>, replace?: boolean) => void }) {
  const P: Record<string, string> = { ...DEFAULTS, ...route.params };
  const cohort = (P.cohort === "text" ? "text" : "joint") as Cohort;
  const rep = (P.rep === "lexical" ? "lexical" : "semantic") as Rep;
  const density = [5, 10, 15].includes(Number(P.d)) ? Number(P.d) / 100 : 0.1;
  const colourBy = (["community", "atu", "region"].includes(P.colour) ? P.colour : "community") as ColourBy;
  const layoutMode = (["network", "relayout", "pca", "places"].includes(P.layout) ? P.layout : "network") as LayoutMode;
  const seed = [42, 7, 19].includes(Number(P.seed)) ? Number(P.seed) : 42;
  const set = (patch: Record<string, string | null | undefined>, replace = true) => navigate("/explore", { ...route.params, ...patch }, replace);

  const manifest = useData<ManifestPayload>("manifest.json");
  const model = useGraphModel({ cohort, rep, density, colourBy, layoutMode, seed });
  const land = useLand(layoutMode === "places");
  const canvasRef = useRef<NetworkCanvasHandle>(null);
  const [narrow, setNarrow] = useState(() => window.innerWidth < 900);
  useEffect(() => { const on = () => setNarrow(window.innerWidth < 900); window.addEventListener("resize", on); return () => window.removeEventListener("resize", on); }, []);
  const view = P.view === "list" || (narrow && !route.params.view) ? "list" : "network";

  const selectedId = P.tale && model.index.has(P.tale) ? P.tale : null;
  const selected = selectedId ? model.index.get(selectedId)! : null;
  const sideRef = useRef<HTMLElement>(null);
  // on narrow screens the tale panel moves above the list; bring it into view on selection
  useEffect(() => { if (narrow && selectedId) sideRef.current?.scrollIntoView({ block: "start" }); }, [narrow, selectedId]);
  const [tale, setTale] = useState<TalePayload | null>(null);
  useEffect(() => { setTale(null); if (selectedId) load<TalePayload>(taleUrl(selectedId)).then(setTale); }, [selectedId]);

  // neighbours for current and previous representation (FLIP "new" marks)
  const prevRep = useRef<{ rep: Rep; ids: string[] } | null>(null);
  const neighbourItems: NeighbourItem[] = useMemo(() => {
    if (!tale) return [];
    const list = tale.neighbours[cohort]?.[rep] ?? tale.neighbours.text?.[rep] ?? [];
    const before = prevRep.current && prevRep.current.rep !== rep ? new Set(prevRep.current.ids) : null;
    return list.map(([id, score]) => {
      const r = model.catalogue.get(id);
      return { id, score, title: r?.title ?? id, isNew: !!before && !before.has(id), atu: r?.atu, place: r?.place };
    });
  }, [tale, rep, cohort, model.catalogue]);
  useEffect(() => { if (tale) prevRep.current = { rep, ids: (tale.neighbours[cohort]?.[rep] ?? []).map((x) => x[0]) }; }, [tale, rep, cohort]);
  const highlight = useMemo(() => neighbourItems.map((n) => model.index.get(n.id)).filter((x): x is number => x !== undefined), [neighbourItems, model.index]);

  // search + filters (visual only)
  const [query, setQuery] = useState("");
  const regionF = P.fregion ?? "";
  const chapterF = P.fchapter ?? "";
  const dimmed = useMemo(() => {
    if (!regionF && !chapterF) return undefined;
    return model.rows.map((r) => (regionF && r?.region !== regionF) || (chapterF && r?.atu_chapter !== chapterF) ? true : false);
  }, [model.rows, regionF, chapterF]);
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    return model.rows.map((r, i) => ({ r, i })).filter(({ r }) => r && (r.title.toLowerCase().includes(q) || (r.atu ?? "").toLowerCase() === q || (r.place ?? "").toLowerCase().includes(q) || (r.atu_name ?? "").toLowerCase().includes(q))).slice(0, 12);
  }, [query, model.rows]);

  const proj = useMemo(() => worldProjection(), []);
  const background = useMemo(() => (land ? drawLand(land, proj) : null), [land, proj]);
  const focusEdges = useMemo(() => focusEdgesFor(model, selected), [model, selected]);
  const backbone = useMemo(() => backboneEdges(model), [model]);
  const pair = P.pair ? (P.pair.split(",") as [string, string]) : null;
  // a pair stays pinned (drawn on the graph, kept in the URL) after the reader closes
  const pinned = pair ?? (P.pin ? (P.pin.split(",") as [string, string]) : null);
  const pairIdx = pinned && model.index.has(pinned[0]) && model.index.has(pinned[1]) ? [model.index.get(pinned[0])!, model.index.get(pinned[1])!] as [number, number] : null;

  const g = model.graph;
  const stats = g?.partition_stats[String(seed)];
  const runMismatch = route.params.run && manifest.data && route.params.run !== manifest.data.run_id;
  const shareUrl = () => window.location.href.split("#")[0] + buildHash("/explore", { ...route.params, run: manifest.data?.run_id });

  const select = (i: number | null) => set({ tale: i === null ? null : model.nodes[i], pair: null, pin: null });
  const tooltip = (i: number) => {
    const r = model.rows[i];
    if (!r) return null;
    return { title: r.title, lines: [`ATU ${r.atu ?? "—"}${r.atu_name ? ` · ${r.atu_name}` : ""}`, `${r.place ?? "geography unknown"}${r.region ? ` · ${r.region}` : ""}`,
      colourBy === "community" ? `community ${g ? g.colour_index[String(seed)][model.communities[i]] + 1 : "?"} (size ${stats?.sizes[model.communities[i]] ?? "?"})` : ""].filter(Boolean) };
  };

  if (model.error) return <div className="page"><ErrorState message={model.error} /></div>;

  return (
    <div className={`workspace${selected != null ? " has-selection" : ""}`}>
      <aside className="rail" aria-label="Explore controls">
        <section>
          <label className="control-label" htmlFor="search">Find a tale</label>
          <input id="search" type="search" placeholder="title, ATU number, place…" value={query} onChange={(e) => setQuery(e.target.value)} style={{ width: "100%" }} />
          {matches.length > 0 && (
            <ul className="nlist" style={{ marginTop: 6 }} aria-label="Search results">
              {matches.map(({ r, i }) => (
                <li key={r!.id} style={{ gridTemplateColumns: "1fr" }}><button className="linklike" onClick={() => { select(i); setQuery(""); }}>{r!.title} <span className="muted small">· {r!.atu} · {r!.place ?? "?"}</span></button></li>
              ))}
            </ul>
          )}
          {query.trim().length >= 2 && matches.length === 0 && <p className="small muted" style={{ marginTop: 6 }}>No tale in this cohort matches “{query}”.</p>}
        </section>
        <details className="rail-more" open={!narrow}>
        <summary>View settings: cohort, representation, density, colour, arrangement</summary>
        <section>
          <span className="control-label">Cohort</span>
          <Segmented label="Cohort" value={cohort} onChange={(v) => set({ cohort: v, tale: null, pair: null })} options={[{ value: "joint", label: "Joint (1,133)" }, { value: "text", label: "All usable" }]} />
          <p className="small muted" style={{ margin: "4px 0 0" }}>{cohort === "joint" ? "Primary comparison cohort: tales with an ATU label and defensible geography." : "Exploratory: every usable narrative (1,498). Agreement statistics are only computed on the joint cohort."}</p>
        </section>
        <section>
          <span className="control-label">Representation</span>
          <Segmented label="Representation" value={rep} onChange={(v) => set({ rep: v })} options={[{ value: "lexical", label: "TF–IDF" }, { value: "semantic", label: "Embeddings" }]} />
        </section>
        <section>
          <span className="control-label">Edge density</span>
          <Segmented label="Density" value={P.d} onChange={(v) => set({ d: v })} options={[{ value: "5", label: "5%" }, { value: "10", label: "10% (primary)" }, { value: "15", label: "15%" }]} />
        </section>
        <section>
          <span className="control-label">Colour by</span>
          <Segmented label="Colour by" value={colourBy} onChange={(v) => set({ colour: v })} options={[{ value: "community", label: "Community" }, { value: "atu", label: "ATU" }, { value: "region", label: "Region" }]} />
        </section>
        <section>
          <span className="control-label">Arrangement</span>
          <Segmented label="Arrangement" value={layoutMode} onChange={(v) => set({ layout: v })} options={[
            { value: "network", label: "Network", title: "Shared ForceAtlas2 layout of both backbones" },
            { value: "relayout", label: "Relayout", title: "Layout of the current representation's backbone only" },
            { value: "pca", label: "PCA", title: "PC1/PC2 of the embeddings" },
            { value: "places", label: "Places", title: "Recorded country points (distance cohort only)" }]} />
          <p className="small muted" style={{ margin: "4px 0 0" }}>
            {layoutMode === "pca" && model.layout ? `PCA of embedding vectors: PC1 ${(model.layout.pca_explained_variance[0] * 100).toFixed(1)}% + PC2 ${(model.layout.pca_explained_variance[1] * 100).toFixed(1)}% of variance. Neighbours are still computed in the full 384-dimensional space.`
              : layoutMode === "places" ? `Only tales with documented coordinates are shown (${model.located.filter(Boolean).length}); tales sharing a country point are spread on a spiral (display displacement, not location).`
              : layoutMode === "relayout" ? `Layout of the ${repLabel(rep)} backbone only.` : "One shared layout for both representations, so switching representation changes edges, not positions."}
          </p>
        </section>
        <section>
          <span className="control-label">Highlight (filters dim; nothing is recomputed)</span>
          <select aria-label="Highlight region" value={regionF} onChange={(e) => set({ fregion: e.target.value || null })} style={{ width: "100%", marginBottom: 6 }}>
            <option value="">All regions</option>
            {REGION_ORDER.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <select aria-label="Highlight ATU chapter" value={chapterF} onChange={(e) => set({ fchapter: e.target.value || null })} style={{ width: "100%" }}>
            <option value="">All ATU chapters</option>
            {ATU_CHAPTER_ORDER.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </section>
        <section>
          <span className="control-label">Louvain seed</span>
          <Segmented label="Seed" value={String(seed)} onChange={(v) => set({ seed: v })} options={[{ value: "42", label: "42 (primary)" }, { value: "7", label: "7" }, { value: "19", label: "19" }]} />
        </section>
        </details>
        <section className="small">
          {model.legend.items.length > 0 && <Legend title={model.legend.title} items={model.legend.items.slice(0, 16)} ring={model.legend.ring} />}
        </section>
      </aside>

      <div className="stage">
        <div className="stage-bar">
          <strong>{cohortName(cohort)} · {repLabel(rep)} · {densityLabel(density)}</strong>
          {g && stats && <span className="muted">{int(g.n)} tales · {int(g.m)} edges (cosine ≥ {fmt(g.similarity_threshold)}) · {stats.communities} communities · Q {fmt(stats.modularity)}{g.modularity_null ? ` (shuffled ${fmt(g.modularity_null.null_mean)})` : ""} · {g.isolates.length} isolates</span>}
          <span className="spacer" />
          <Segmented label="View" value={view} onChange={(v) => set({ view: v })} options={[{ value: "network", label: "Graph" }, { value: "list", label: "List" }]} />
          <button className="btn small" onClick={() => copyLink(shareUrl())}>Copy view link</button>
          <button className="btn small" onClick={() => navigate("/explore", {}, false)}>Reset view</button>
        </div>
        {runMismatch && <div className="callout warn sans small" style={{ margin: 8 }}>This link was made with run {route.params.run}; the loaded data are run {manifest.data?.run_id}. Values may differ.</div>}
        {!model.ready ? <Loading what="the network" /> : view === "network" ? (
          <div style={{ position: "relative", flex: 1, display: "flex" }}>
            <NetworkCanvas
              ref={canvasRef}
              ariaLabel={`${cohortName(cohort)} similarity network, ${repLabel(rep)}, ${densityLabel(density)} density, coloured by ${colourBy}. Use the List view for an accessible table.`}
              n={model.nodes.length} positions={model.positions} colours={model.colours} visible={model.visible} dimmed={dimmed}
              edges={layoutMode === "places" ? [] : backbone} edgeAlpha={0.07} focusEdges={focusEdges} selected={selected} highlight={highlight}
              pair={pairIdx} labels={model.rows.map((r) => r?.title ?? "")} tooltip={tooltip}
              onSelect={select} onEdgeClick={(i, j) => set({ pair: `${model.nodes[i]},${model.nodes[j]}` }, false)}
              background={layoutMode === "places" ? background : null} backgroundAlpha={layoutMode === "places" && background ? 1 : 0}
              transition={{ key: `${layoutMode}|${rep}|${colourBy}|${P.d}|${seed}` }}
              fit={{ key: `${selectedId ?? "all"}|${layoutMode}`, indices: selected != null ? [selected, ...highlight] : null }}
              drawTrail
            />
            {selected == null && <div className="canvas-hint">Choose a story to trace its neighbours</div>}
            <div className="canvas-overlay">
              <button className="btn small" onClick={() => canvasRef.current?.zoomBy(1.4)} aria-label="Zoom in">＋</button>
              <button className="btn small" onClick={() => canvasRef.current?.zoomBy(1 / 1.4)} aria-label="Zoom out">－</button>
              <button className="btn small" onClick={() => canvasRef.current?.fitAll()}>Fit all</button>
              <button className="btn small" onClick={() => { const u = canvasRef.current?.toPNG(); if (u) downloadDataUrl(`once-upon-a-world-${rep}-${P.d}.png`, u); }}>Download PNG</button>
            </div>
          </div>
        ) : (
          <ListView model={model} selected={selected} onSelect={select} dimmed={dimmed} seed={seed} />
        )}
        <p className="small muted sans" style={{ padding: "6px 12px", margin: 0, borderTop: "1px solid var(--rule)" }}>
          Faint lines: display backbone ({g?.backbone.length.toLocaleString() ?? "–"} of {int(g?.m)} edges; {g?.backbone_rule}). Statistics always use all edges. On selection, up to 20 strongest edges are drawn; click an edge to read the pair. Positions are a drawing aid, not measurements.
        </p>
      </div>

      <aside className="side" aria-label="Selected tale" ref={sideRef}>
        <div className="side-inner">
          {selected == null ? (
            <div className="sans small">
              <h3 style={{ fontFamily: "var(--serif)" }}>Explore the neighbourhoods</h3>
              <p>Each dot is one recorded tale. Click one (or search, or use the List view) to see its ten nearest tales under the current representation, its strongest edges in the current graph, and why it belongs to this cohort.</p>
              <p className="muted">These are constructed text-similarity networks, not records of storytelling or transmission. A chain of edges is a chain of similarities, not a route.</p>
              {g && <GraphFacts g={g} seed={seed} />}
              <HowMade
                measured={`Edges join the ${densityLabel(density)} most similar pairs of tales (cosine similarity, ${repLabel(rep)}); colours show weighted Louvain communities (seed ${seed}) or recorded labels.`}
                records={cohort === "joint" ? "Joint cohort: tales with one ATU label and a defensible place and broad region." : "All usable narratives; agreement statistics are only computed on the joint cohort."}
                method="Global threshold and weighted networks (week 4 §7–8); Louvain and modularity (week 4 §3–4); TF–IDF and embeddings (weeks 6–7). Positions: ForceAtlas2 layout of a display backbone, or PCA (week 7 §2)."
                infer="Which tales a representation places close together, and how the discovered groups line up with recorded labels."
                cannot="Distances on screen are not measurements, communities are one partition among many, and nothing here shows transmission or origin." />
            </div>
          ) : (
            <>
              <div className="row" style={{ marginBottom: 8 }}>
                <button className="btn small" onClick={() => select(null)}>← Overview</button>
                <button className="btn small" onClick={() => downloadText(`${selectedId}-neighbours-${rep}.csv`, toCsv([["rank", "tale", "title", "cosine", "representation", "cohort", "run_id"], ...neighbourItems.map((n, k) => [k + 1, n.id, n.title, n.score, rep, cohort, manifest.data?.run_id ?? ""])]))}>Download neighbours (CSV)</button>
              </div>
              <TaleDetails tale={tale} row={selectedId ? model.catalogue.get(selectedId) : undefined} />
              <h4 style={{ marginTop: 16 }}>Ten nearest tales · {repLabel(rep)}</h4>
              <p className="small muted sans" style={{ marginTop: 0 }}>Cosine similarity in the original feature space, within the {cohortName(cohort).toLowerCase()}. Switch representation to see which neighbours persist.</p>
              {tale ? <NeighbourList items={neighbourItems} rep={rep} maxScore={neighbourItems[0]?.score ?? 1} onOpen={(id) => set({ tale: id, pair: null })} onPair={(id) => set({ pair: `${selectedId},${id}` }, false)} /> : <Loading what="neighbours" />}
            </>
          )}
        </div>
      </aside>
      {pinned && !pair && <div className="sans small" style={{ position: "fixed", left: "50%", bottom: 14, transform: "translateX(-50%)", zIndex: 25 }}><span className="chip accent">Pinned pair: {model.catalogue.get(pinned[0])?.title ?? pinned[0]} ↔ {model.catalogue.get(pinned[1])?.title ?? pinned[1]}</span> <button className="btn small" onClick={() => set({ pair: pinned.join(",") }, false)}>Reopen</button> <button className="btn small" onClick={() => set({ pin: null })}>Unpin</button></div>}
      {pair && <PairReader a={pair[0]} b={pair[1]} onClose={() => set({ pair: null, pin: pair.join(",") })} onSwap={() => set({ pair: `${pair[1]},${pair[0]}` })} />}
    </div>
  );
}

function GraphFacts({ g, seed }: { g: NonNullable<ReturnType<typeof useGraphModel>["graph"]>; seed: number }) {
  const st = g.partition_stats[String(seed)];
  return (
    <div className="table-wrap" style={{ marginTop: 10 }}>
      <table className="data">
        <tbody>
          <tr><td>Tales / edges</td><td className="num">{int(g.n)} / {int(g.m)}</td></tr>
          <tr><td>Achieved density</td><td className="num">{(g.density_achieved * 100).toFixed(2)}%</td></tr>
          <tr><td>Cosine threshold</td><td className="num">{fmt(g.similarity_threshold)}</td></tr>
          <tr><td>Components / isolates</td><td className="num">{g.components} / {g.isolates.length}</td></tr>
          <tr><td>Communities (seed {seed})</td><td className="num">{st.communities} ({st.sizes.filter((s) => s >= 5).length} with ≥ 5 tales)</td></tr>
          <tr><td>Weighted modularity Q</td><td className="num">{fmt(st.modularity)}</td></tr>
          {g.modularity_null && <tr><td>Degree-preserving shuffles</td><td className="num">{fmt(g.modularity_null.null_mean)} ± {fmt(g.modularity_null.null_sd)} (n={g.modularity_null.shuffles})</td></tr>}
          <tr><td>Seed agreement (NMI)</td><td className="num">{Object.entries(g.seed_agreement_nmi).map(([k, v]) => `${k}: ${fmt(v, 2)}`).join(" · ")}</td></tr>
        </tbody>
      </table>
    </div>
  );
}

function ListView({ model, selected, onSelect, dimmed, seed }: { model: ReturnType<typeof useGraphModel>; selected: number | null; onSelect: (i: number | null) => void; dimmed?: boolean[]; seed: number }) {
  const [sort, setSort] = useState<"title" | "atu" | "place" | "community" | "degree">("title");
  const [limit, setLimit] = useState(150);
  const g = model.graph!;
  const gi = useMemo(() => new Map(g.nodes.map((id, i) => [id, i])), [g]);
  const rows = useMemo(() => {
    const out = model.rows.map((r, i) => ({ r, i, comm: model.communities[i], deg: g.degree[gi.get(model.nodes[i])!] ?? 0 })).filter((x) => x.r && !(dimmed?.[x.i]));
    const key = (x: (typeof out)[number]) => sort === "title" ? x.r!.title : sort === "atu" ? x.r!.atu ?? "" : sort === "place" ? x.r!.place ?? "~" : sort === "community" ? String(1000 + (g.colour_index[String(seed)][x.comm] ?? 999)) : String(100000 - x.deg).padStart(6, "0");
    return out.sort((a, b) => key(a).localeCompare(key(b)));
  }, [model, sort, dimmed, g, gi, seed]);
  return (
    <div style={{ flex: 1, overflow: "auto", padding: 10 }}>
      <div className="row small sans" style={{ marginBottom: 6 }}>
        <span>{rows.length.toLocaleString()} tales · sort by</span>
        <select value={sort} onChange={(e) => setSort(e.target.value as typeof sort)} aria-label="Sort list">
          <option value="title">title</option><option value="atu">ATU</option><option value="place">place</option><option value="community">community</option><option value="degree">degree (edges)</option>
        </select>
      </div>
      <div className="table-wrap">
        <table className="data">
          <thead><tr><th>Title</th><th>ATU</th><th>Place</th><th className="hide-narrow">Region</th><th className="num hide-narrow">Community</th><th className="num hide-narrow">Edges</th></tr></thead>
          <tbody>
            {rows.slice(0, limit).map(({ r, i, comm, deg }) => (
              <tr key={r!.id} className={selected === i ? "sel" : ""}>
                <td><button className="btn small ghost" style={{ border: 0, padding: 0, textAlign: "left" }} onClick={() => onSelect(i)}>{r!.title}</button></td>
                <td>{r!.atu}</td><td>{r!.place ?? <span className="muted">unknown</span>}</td><td className="hide-narrow">{r!.region ?? "–"}</td>
                <td className="num hide-narrow">{(g.colour_index[String(seed)][comm] ?? 0) + 1}</td><td className="num hide-narrow">{deg}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > limit && <button className="btn small" style={{ marginTop: 8 }} onClick={() => setLimit((l) => l + 300)}>Show more</button>}
    </div>
  );
}
