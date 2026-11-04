import { useEffect, useMemo, useState } from "react";
import { load, taleUrl, useData } from "../data/load";
import type { TalePayload, ValidationPayload } from "../data/types";
import { ErrorState, Loading, Segmented, downloadText, toCsv, toast } from "../components/ui";

type Ann = Record<string, string> & { item_id: string; reviewer_id: string; note: string; timestamp: string };
const KEY = "ouaw-annotations-v1";

function loadAnns(): Record<string, Ann> {
  try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
}
function saveAnns(a: Record<string, Ann>) {
  try { localStorage.setItem(KEY, JSON.stringify(a)); } catch { toast("Could not save in this browser; export your CSV now."); }
}

export function Validation() {
  const v = useData<ValidationPayload>("validation.json");
  const [reviewer, setReviewer] = useState(() => { try { return localStorage.getItem("ouaw-reviewer") ?? ""; } catch { return ""; } });
  const [split, setSplit] = useState<"development" | "final">("development");
  const [pos, setPos] = useState(0);
  const [anns, setAnns] = useState<Record<string, Ann>>(loadAnns);
  const [texts, setTexts] = useState<[TalePayload, TalePayload] | null>(null);
  const items = useMemo(() => (v.data?.items ?? []).filter((i) => i.split === split), [v.data, split]);
  const item = items[pos];
  useEffect(() => { setTexts(null); if (item) Promise.all([load<TalePayload>(taleUrl(item.a)), load<TalePayload>(taleUrl(item.b))]).then(([a, b]) => setTexts([a, b])); }, [item]);
  useEffect(() => { try { localStorage.setItem("ouaw-reviewer", reviewer); } catch { /* ignore */ } }, [reviewer]);
  if (v.error) return <div className="page"><ErrorState message={v.error} /></div>;
  if (!v.data) return <div className="page"><Loading what="the review sample" /></div>;
  const d = v.data;
  const key = item ? `${reviewer}|${item.item_id}` : "";
  const cur = anns[key];
  const done = items.filter((i) => anns[`${reviewer}|${i.item_id}`]).length;
  const setAspect = (asp: string, val: string) => {
    if (!item || !reviewer) return;
    const next = { ...anns, [key]: { ...(cur ?? { item_id: item.item_id, reviewer_id: reviewer, note: "" }), [asp]: val, timestamp: new Date().toISOString() } as Ann };
    setAnns(next); saveAnns(next);
  };
  const setNote = (note: string) => {
    if (!item || !reviewer) return;
    const next = { ...anns, [key]: { ...(cur ?? { item_id: item.item_id, reviewer_id: reviewer }), note, timestamp: new Date().toISOString() } as Ann };
    setAnns(next); saveAnns(next);
  };
  const exportCsv = () => {
    const mine = Object.values(anns).filter((a) => !reviewer || a.reviewer_id === reviewer);
    downloadText(`annotations-${reviewer || "all"}.csv`, toCsv([["reviewer_id", "item_id", ...d.aspects, "note", "timestamp", "label_source"], ...mine.map((a) => [a.reviewer_id, a.item_id, ...d.aspects.map((x) => a[x] ?? ""), a.note ?? "", a.timestamp, "human"])]));
  };
  const importCsv = async (f: File) => {
    const lines = (await f.text()).split(/\r?\n/).filter(Boolean);
    const head = lines[0].split(",");
    const next = { ...anns };
    for (const ln of lines.slice(1)) {
      const cells = ln.match(/("([^"]|"")*"|[^,]*)(,|$)/g)?.map((c) => c.replace(/,$/, "").replace(/^"|"$/g, "").replace(/""/g, '"')) ?? [];
      const rec = Object.fromEntries(head.map((h, k) => [h, cells[k] ?? ""])) as Ann;
      if (rec.item_id && rec.reviewer_id) next[`${rec.reviewer_id}|${rec.item_id}`] = rec;
    }
    setAnns(next); saveAnns(next); toast("Annotations imported into this browser.");
  };
  const labels: Record<string, string> = { shared_vocabulary: "Shared vocabulary", shared_topic: "Shared broad topic", shared_plot: "Shared narrative event or plot structure", different_outcome: "Notable difference in outcome or moral", insufficient_evidence: "Insufficient evidence / uncertain" };

  return (
    <div className="page">
      <h1 style={{ fontSize: "clamp(2rem, 4vw, 3rem)" }}>Validation</h1>
      <div className="grid-2">
        <div className="prose">
          <p><strong>Status: {d.status}.</strong> No human annotations have been collected yet, so this site reports <em>no</em> validation accuracy or agreement. Similarity scores are measurements whose meaning still has to be checked against readers' judgements.</p>
          <p>The review sample has {d.items.length} tale pairs from the joint cohort. It is stratified by embedding-similarity band, same/different ATU type and same/different region, and split into a development set (to refine this rubric) and a final set (to report). It was drawn with a fixed seed before any annotation. Reviewers see only the two texts: titles, tale types, places, model and scores are hidden.</p>
        </div>
        <div className="callout neutral sans small">
          <strong>How to take part.</strong> Enter a reviewer code (initials are enough; no personal data). Judge each aspect separately and add a short note. Your answers stay in this browser until you export a CSV; put exported files in <span className="mono">outputs/validation/annotations/</span> and rerun <span className="mono">uv run python -m analysis validation export</span>. Two people should annotate an overlapping set independently; agreement will be reported as raw agreement with disagreement counts.
        </div>
      </div>
      <div className="figure">
        <div className="row" style={{ marginBottom: 10 }}>
          <label className="sans small">Reviewer code <input type="text" value={reviewer} onChange={(e) => setReviewer(e.target.value.replace(/[^\w-]/g, "").slice(0, 12))} placeholder="e.g. AB" style={{ width: 90 }} /></label>
          <Segmented label="Set" value={split} onChange={(s) => { setSplit(s); setPos(0); }} options={[{ value: "development", label: `Development (${d.items.filter((i) => i.split === "development").length})` }, { value: "final", label: `Final (${d.items.filter((i) => i.split === "final").length})` }]} />
          <span className="sans small muted">{reviewer ? `${done}/${items.length} done` : "enter a reviewer code to record answers"}</span>
          <span className="spacer" />
          <button className="btn small" onClick={exportCsv}>Export CSV</button>
          <label className="btn small">Import CSV<input type="file" accept=".csv" style={{ display: "none" }} onChange={(e) => e.target.files?.[0] && importCsv(e.target.files[0])} /></label>
        </div>
        {item && (
          <>
            <div className="row sans small" style={{ marginBottom: 8 }}>
              <button className="btn small" disabled={pos === 0} onClick={() => setPos((p) => p - 1)}>← Previous</button>
              <strong>Item {item.item_id}</strong> <span className="muted">({pos + 1} of {items.length})</span>
              <button className="btn small" disabled={pos >= items.length - 1} onClick={() => setPos((p) => p + 1)}>Next →</button>
            </div>
            <div className="review-grid">
              {!texts ? <Loading what="the two texts" /> : texts.map((t, k) => (
                <div key={k}>
                  <h3 style={{ marginBottom: 4 }}>Tale {k === 0 ? "A" : "B"}</h3>
                  <div className="review-text" tabIndex={0} aria-label={`Text of tale ${k === 0 ? "A" : "B"}`}>{t.text}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 14 }}>
              {d.aspects.map((asp) => (
                <div key={asp} className="aspect">
                  <div><strong>{labels[asp] ?? asp}</strong><div className="small muted">{d.rubric[asp]}</div></div>
                  <Segmented label={labels[asp] ?? asp} value={(cur?.[asp] as "yes" | "no" | "unsure") ?? ("" as "yes")} onChange={(val) => setAspect(asp, val)} options={d.values.map((x) => ({ value: x as "yes", label: x }))} />
                </div>
              ))}
              <label className="sans small" style={{ display: "block", marginTop: 10 }}>Note (optional)<textarea value={cur?.note ?? ""} onChange={(e) => setNote(e.target.value)} disabled={!reviewer} /></label>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
