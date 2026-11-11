import { useLayoutEffect, useRef } from "react";
import type { CatalogueRow, Rep, TalePayload } from "../data/types";
import { shownText } from "../data/vectors";
import { DUR, useMotion } from "../lib/motion";
import { fmt, repLabel } from "../lib/format";
import { Loading } from "./ui";

export interface NeighbourItem { id: string; score: number; title: string; isNew: boolean; atu?: string | null; place?: string | null }

/** Ranked neighbour list with FLIP animation: persistent neighbours slide to their new rank. */
export function NeighbourList({ items, onOpen, onPair, rep, maxScore }: { items: NeighbourItem[]; onOpen: (id: string) => void; onPair: (id: string) => void; rep: Rep; maxScore: number }) {
  const { enabled: motion } = useMotion();
  const refs = useRef(new Map<string, HTMLLIElement>());
  const prev = useRef(new Map<string, number>());
  useLayoutEffect(() => {
    const now = new Map<string, number>();
    refs.current.forEach((el, id) => { if (el.isConnected) now.set(id, el.getBoundingClientRect().top); });
    if (motion) {
      now.forEach((top, id) => {
        const el = refs.current.get(id)!;
        const before = prev.current.get(id);
        if (before !== undefined && Math.abs(before - top) > 1) {
          el.animate([{ transform: `translateY(${before - top}px)` }, { transform: "translateY(0)" }], { duration: DUR.list, easing: "cubic-bezier(.65,0,.35,1)" });
        } else if (before === undefined) {
          el.animate([{ opacity: 0, transform: "translateX(8px)" }, { opacity: 1, transform: "none" }], { duration: DUR.list, easing: "ease-out" });
        }
      });
    }
    prev.current = now;
  }, [items, motion]);
  return (
    <ol className="nlist" aria-label={`Ten nearest tales under ${repLabel(rep)}`}>
      {items.map((it, k) => (
        <li key={it.id} ref={(el) => { if (el) refs.current.set(it.id, el); else refs.current.delete(it.id); }} className={it.isNew ? "new" : ""}>
          <span className="rank">{k + 1}</span>
          <span>
            <button className="linklike" onClick={() => onOpen(it.id)} title="Select this tale">{it.title}</button>
            <div className="small muted">{[it.atu ? `ATU ${it.atu}` : null, it.place].filter(Boolean).join(" · ")}{it.isNew && <span className="chip warn" style={{ marginLeft: 6 }}>new in this view</span>}</div>
            <div className="scorebar" aria-hidden><span style={{ width: `${Math.max(4, (it.score / maxScore) * 100)}%` }} /></div>
          </span>
          <span className="row" style={{ gap: 4, flexDirection: "column", alignItems: "flex-end" }}>
            <span className="score" title="cosine similarity in the original feature space">{fmt(it.score)}</span>
            <button className="btn small" onClick={() => onPair(it.id)} aria-label={`Read ${it.title} side by side`}>Read pair</button>
          </span>
        </li>
      ))}
    </ol>
  );
}

export function TaleDetails({ tale, row }: { tale: TalePayload | null; row: CatalogueRow | undefined }) {
  if (!tale) return <Loading what="the tale" />;
  const p = tale.provenance;
  return (
    <div>
      <h3 style={{ marginBottom: 4 }}>{tale.title}</h3>
      <div className="row" style={{ gap: 6, marginBottom: 8 }}>
        {tale.atu.id ? <span className="chip">ATU {tale.atu.id}</span> : <span className="chip warn">ATU {tale.atu.status}</span>}
        {tale.atu.chapter && <span className="chip">{tale.atu.chapter}</span>}
        {p.place ? <span className="chip">{p.place}</span> : <span className="chip warn">geography unknown</span>}
        {p.region && <span className="chip">{p.region}</span>}
        {tale.flags.includes("suspected_truncated_start") && <span className="chip warn">opening may be missing</span>}
      </div>
      <dl className="sans small" style={{ display: "grid", gridTemplateColumns: "110px 1fr", gap: "4px 10px", margin: "0 0 10px" }}>
        <dt className="muted">Tale type</dt><dd style={{ margin: 0 }}>{tale.atu.id ? `${tale.atu.id} — ${tale.atu.name ?? ""}` : `${tale.atu.status} ${tale.atu.ids.join(", ")}`}</dd>
        <dt className="muted">Recorded</dt><dd style={{ margin: 0 }}>{p.label.join(" | ") || "—"} <span className="muted">({p.kinds.join(", ")})</span></dd>
        {p.place && <><dt className="muted">Place label</dt><dd style={{ margin: 0 }}>{p.place}{p.detail ? ` (${p.detail})` : ""} · confidence {p.confidence}</dd></>}
        {p.coordinate_meaning && <><dt className="muted">Map point</dt><dd style={{ margin: 0 }}>{p.coordinate_meaning}</dd></>}
        <dt className="muted">Source</dt><dd style={{ margin: 0 }}>{tale.source ?? "not recorded"}</dd>
        <dt className="muted">Length</dt><dd style={{ margin: 0 }}>{tale.n_words.toLocaleString()} words · {tale.chunks.length} passages</dd>
        <dt className="muted">Records</dt><dd style={{ margin: 0 }}>{tale.record_ids.join(", ")}{tale.record_ids.length > 1 ? " (identical copies merged)" : ""}</dd>
      </dl>
      <div className="callout neutral sans small" style={{ marginBottom: 10 }}>
        <strong>Why it is in this cohort:</strong>{" "}
        {row?.in_joint ? "it has one unambiguous ATU label and a defensible place and broad region, so it is part of the joint comparison cohort."
          : row?.in_atu ? "it is a usable narrative with one ATU label, but its geography is not defensible for the comparison: " + (tale.exclusion_reasons || "unknown")
          : "it is a usable narrative, but: " + (tale.exclusion_reasons || "—")}
      </div>
      <details>
        <summary className="sans small" style={{ cursor: "pointer", color: "var(--teal)", fontWeight: 600 }}>{tale.text_is_excerpt ? "Read the opening" : "Read the tale"}</summary>
        <p style={{ fontSize: 16, whiteSpace: "pre-wrap" }}>{shownText(tale)}</p>
        {tale.text_is_excerpt && <p className="sans small muted">This public build shows only the opening of each tale. The full text is in the source cited above.</p>}
      </details>
    </div>
  );
}
