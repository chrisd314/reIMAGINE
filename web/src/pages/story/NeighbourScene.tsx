import { useEffect, useMemo, useRef, useState } from "react";
import { load, taleUrl } from "../../data/load";
import type { Rep, TalePayload } from "../../data/types";
import { NetworkCanvas } from "../../components/NetworkCanvas";
import { focusEdgesFor, useGraphModel } from "../../components/useGraphModel";
import { NeighbourList, type NeighbourItem } from "../../components/TalePanel";
import { HowMade, Loading, Segmented } from "../../components/ui";
import { repLabel } from "../../lib/format";

const SUGGESTED = ["tale-0086", "tale-0815", "tale-0532", "tale-1160", "tale-0595"];

export function NeighbourScene({ onRead, onExplore }: { onRead: (a: string, b: string) => void; onExplore: (id: string, rep: Rep) => void }) {
  const [rep, setRep] = useState<Rep>("lexical");
  const [selectedId, setSelectedId] = useState("tale-0086");
  const model = useGraphModel({ cohort: "joint", rep, density: 0.1, colourBy: "atu", layoutMode: "network" });
  const [tale, setTale] = useState<TalePayload | null>(null);
  useEffect(() => { load<TalePayload>(taleUrl(selectedId)).then(setTale); }, [selectedId]);
  const prev = useRef<{ rep: Rep; ids: Set<string> } | null>(null);
  const items: NeighbourItem[] = useMemo(() => {
    if (!tale) return [];
    const list = tale.neighbours.joint?.[rep] ?? [];
    const before = prev.current && prev.current.rep !== rep ? prev.current.ids : null;
    return list.map(([id, score]) => { const r = model.catalogue.get(id); return { id, score, title: r?.title ?? id, isNew: !!before && !before.has(id), atu: r?.atu, place: r?.place }; });
  }, [tale, rep, model.catalogue]);
  useEffect(() => { if (tale) prev.current = { rep, ids: new Set((tale.neighbours.joint?.[rep] ?? []).map((x) => x[0])) }; }, [tale, rep]);
  const other: Rep = rep === "lexical" ? "semantic" : "lexical";
  const overlap = tale ? (tale.neighbours.joint?.[rep] ?? []).filter(([id]) => (tale.neighbours.joint?.[other] ?? []).some(([j]) => j === id)).length : 0;
  const sameType = items.filter((n) => n.atu && n.atu === tale?.atu.id).length;
  const selected = model.index.get(selectedId) ?? null;
  const highlight = items.map((n) => model.index.get(n.id)).filter((x): x is number => x !== undefined);

  return (
    <div>
      <div className="row" style={{ marginBottom: 10 }}>
        <span className="control-label" style={{ margin: 0 }}>Representation</span>
        <Segmented label="Representation" value={rep} onChange={setRep} options={[{ value: "lexical", label: "TF–IDF (words)" }, { value: "semantic", label: "Embeddings (meaning)" }]} />
        <span className="control-label" style={{ margin: "0 0 0 10px" }}>Tale</span>
        <select aria-label="Choose a tale" value={selectedId} onChange={(e) => setSelectedId(e.target.value)}>
          {SUGGESTED.map((id) => <option key={id} value={id}>{model.catalogue.get(id)?.title ?? id}</option>)}
          {!SUGGESTED.includes(selectedId) && <option value={selectedId}>{model.catalogue.get(selectedId)?.title ?? selectedId}</option>}
        </select>
      </div>
      <div className="grid-main-side" style={{ ["--side" as string]: "380px" }}>
        <figure className="figure" style={{ margin: 0, padding: 10 }}>
          {!model.ready ? <Loading what="the network" /> : (
            <div style={{ height: 460, display: "flex", position: "relative" }}>
              <NetworkCanvas zoomMode="gentle" ariaLabel={`Shared network layout; the selected tale and its ten nearest tales under ${repLabel(rep)} are highlighted.`}
                n={model.nodes.length} positions={model.positions} colours={model.colours}
                focusEdges={focusEdgesFor(model, selected, 10)} selected={selected} highlight={highlight}
                labels={model.rows.map((r) => r?.title ?? "")}
                tooltip={(i) => { const r = model.rows[i]; return r ? { title: r.title, lines: [`ATU ${r.atu} · ${r.atu_chapter}`, `${r.place}`] } : null; }}
                onSelect={(i) => { if (i !== null) setSelectedId(model.nodes[i]); }}
                onEdgeClick={(i, j) => onRead(model.nodes[i], model.nodes[j])}
                transition={{ key: rep }} fit={{ key: `${selectedId}`, indices: selected != null ? [selected, ...highlight] : null }} radius={2.6} />
            </div>
          )}
          <figcaption className="caption">Positions stay fixed (one shared layout for both representations); only the highlighted neighbours, ranks and edges change. Colours show ATU chapters. Click any dot to follow its neighbours; click a red edge to read the pair.</figcaption>
        </figure>
        <div>
          <h3 style={{ marginBottom: 2 }}>{tale?.title ?? "…"}</h3>
          <div className="small muted sans" style={{ marginBottom: 8 }}>ATU {tale?.atu.id} · {tale?.provenance.place}</div>
          <div className="callout neutral sans small" style={{ marginBottom: 10 }}>
            {overlap} of 10 neighbours are shared by both representations; {sameType} of the 10 under {rep === "lexical" ? "TF–IDF" : "embeddings"} share this tale's ATU type.
          </div>
          {tale ? <NeighbourList items={items} rep={rep} maxScore={items[0]?.score ?? 1} onOpen={setSelectedId} onPair={(id) => onRead(selectedId, id)} /> : <Loading what="neighbours" />}
          <button className="btn small" style={{ marginTop: 10 }} onClick={() => onExplore(selectedId, rep)}>Open this tale in Explore →</button>
        </div>
      </div>
      <p className="prose" style={{ marginTop: 18 }}><strong>TF–IDF</strong> rewards words that are frequent in one tale but rare across the corpus. Names, places and distinctive objects pull tales together even when their plots differ. <strong>Embeddings</strong> summarise what each passage is about and average the passages. They see past vocabulary, but the average blurs a tale's sequence of events. The two scales differ (TF–IDF cosines are low, embedding cosines high), so scores are only compared <em>within</em> a representation, and both graphs keep exactly 10% of tale pairs.</p>
      <HowMade
        measured="The ten tales with the highest cosine similarity to the selected tale, computed in the original feature space within the joint cohort."
        records="Joint cohort (1,133 tales); identical node set for both representations."
        method="TF–IDF and cosine (week 6, §1); sentence embeddings averaged over chunks (week 7, §1–2); the ten-nearest-neighbour check (weeks 5–7)."
        infer="Which tales each representation treats as closest, and where the two agree."
        cannot="That neighbours share an origin or a plot: similarity is a measurement under a representation, not proof of common ancestry." />
    </div>
  );
}
