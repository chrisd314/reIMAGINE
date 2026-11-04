import { useMemo, useRef, useState } from "react";
import { NetworkCanvas, type NetworkCanvasHandle } from "../../components/NetworkCanvas";
import { useGraphModel, useLand } from "../../components/useGraphModel";
import { HowMade, Legend, Loading, Segmented } from "../../components/ui";
import { drawLand, worldProjection } from "../../lib/geo";
import { useMotion, DUR } from "../../lib/motion";

type Stage = "collapsed" | "places" | "network";

export function MorphScene({ focusId }: { focusId: string }) {
  const { enabled: motion } = useMotion();
  const [stage, setStage] = useState<Stage>("collapsed");
  const [goal, setGoal] = useState<"places" | "network">("places");
  const [selectedId, setSelectedId] = useState<string>(focusId);
  const model = useGraphModel({ cohort: "joint", rep: "semantic", density: 0.1, colourBy: "region", layoutMode: stage === "collapsed" ? "places_collapsed" : stage === "places" ? "places" : "network" });
  const land = useLand(true);
  const proj = useMemo(() => worldProjection(), []);
  const background = useMemo(() => (land ? drawLand(land, proj) : null), [land, proj]);
  const ref = useRef<NetworkCanvasHandle>(null);
  const selected = model.index.get(selectedId) ?? null;
  // all tales in the morph are distance-cohort tales; others are listed separately
  const visible = model.located;
  const unlocated = useMemo(() => model.rows.filter((r, i) => r && !model.located[i]), [model.rows, model.located]);
  const unlocatedLabels = useMemo(() => {
    const m = new Map<string, number>();
    unlocated.forEach((r) => m.set(r!.place ?? "?", (m.get(r!.place ?? "?") ?? 0) + 1));
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  }, [unlocated]);

  const go = (g: "places" | "network") => {
    setGoal(g);
    if (g === "network") setStage(stage === "collapsed" && motion ? "places" : "network");
    else setStage("places");
  };
  const onEnd = (key: string) => {
    if (key.startsWith("places") && goal === "network") setStage("network");
  };

  if (!model.ready) return <Loading what="the map and network layout" />;
  return (
    <div>
      <div className="grid-main-side" style={{ ["--side" as string]: "320px" }}>
        <figure className="figure" style={{ margin: 0, padding: 10 }}>
          <div className="row" style={{ marginBottom: 8 }}>
            <Segmented label="Arrangement" value={goal} onChange={go} options={[{ value: "places", label: "Places" }, { value: "network", label: "Network layout (text similarity)" }]} />
            <span className="small muted sans">{stage === "network" ? "Arrangement: ForceAtlas2 layout of the shared similarity backbone" : stage === "places" ? "Arrangement: recorded country points, tales spread on a spiral (display displacement)" : "Arrangement: recorded country points (count markers)"}</span>
          </div>
          <div style={{ height: 470, position: "relative", display: "flex" }}>
            <NetworkCanvas zoomMode="gentle" ref={ref}
              ariaLabel="Morph between recorded places and the text-similarity network layout for the 1,084 tales with documented coordinates. Selected tale highlighted."
              n={model.nodes.length} positions={model.positions} colours={model.colours} visible={visible}
              selected={selected} labels={model.rows.map((r) => r?.title ?? "")}
              tooltip={(i) => { const r = model.rows[i]; return r ? { title: r.title, lines: [`${r.place} · ${r.region}`, `ATU ${r.atu} ${r.atu_name ?? ""}`] } : null; }}
              onSelect={(i) => { if (i !== null) setSelectedId(model.nodes[i]); }}
              background={background} backgroundAlpha={stage === "network" ? 0 : 1}
              markers={model.markers} markersAlpha={stage === "collapsed" ? 1 : 0}
              transition={{ key: `${stage === "places" ? "places" : stage}-${goal}`, duration: stage === "places" && goal === "network" ? DUR.expand : DUR.layout }}
              onTransitionEnd={onEnd} radius={2.6} drawTrail />
          </div>
          <Legend title="Colour: broad region (recorded label)" items={model.legend.items.filter((x) => x.label !== "unknown / not defensible")} />
        </figure>
        <div className="prose small sans" style={{ fontSize: 14.5 }}>
          <p><strong>Same tales, two arrangements.</strong> In <em>Places</em> each tale sits at the representative point of the country, nation or territory where it was recorded. Tales that share a point fan out on a small spiral; this is display displacement, not a location. In the <em>Network layout</em> the same tales are arranged by textual similarity, using the precomputed layout of each tale's strongest embedding and TF–IDF ties.</p>
          <p>Watch the selected tale (ringed). If tales recorded near each other were also textually similar, colours would stay clustered after the move. They mostly mix, with some regional pockets.</p>
          <p className="muted">The movement only rearranges the same records. It does not show stories travelling, borders moving or cultures evolving.</p>
          <details>
            <summary style={{ cursor: "pointer", color: "var(--teal)", fontWeight: 600 }}>{unlocated.length} joint-cohort tales not shown here</summary>
            <p>They have a defensible place label but no documented point: communities without a recorded country, and regions spanning several countries. They are never given invented coordinates.</p>
            <ul style={{ columns: 2, paddingLeft: 18 }}>{unlocatedLabels.map(([l, n]) => <li key={l}>{l} ({n})</li>)}</ul>
          </details>
        </div>
      </div>
      <HowMade
        measured="Nothing new: this changes positions only. Map points are recorded associations; network positions come from a ForceAtlas2 drawing of each tale's five strongest edges in both 10% graphs."
        records="The 1,084 joint-cohort tales with documented coordinates (distance cohort)."
        method="Drawing rules: backbone first, layout of the backbone (week 4, §8); projection vs original space (week 7, §2)."
        infer="Whether the visual grouping by place survives when the same tales are arranged by text."
        cannot="Distances on screen are not measurements. Similarities are always computed in the original 384-dimensional or TF–IDF space." />
    </div>
  );
}
