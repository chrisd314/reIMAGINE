import { useEffect, useRef, useState, type ReactNode } from "react";
import { useData } from "../../data/load";
import type { AgreementPayload, AgreementRow, NeighbourStats, NullsPayload, SummaryPayload } from "../../data/types";

export function Chapter({ id, num, title, children, onVisible }: { id: string; num: string; title: string; children: ReactNode; onVisible?: (id: string) => void }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!onVisible || !ref.current) return;
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) onVisible(id); }), { rootMargin: "-40% 0px -55% 0px" });
    io.observe(ref.current);
    return () => io.disconnect();
  }, [id, onVisible]);
  return (
    <section id={id} ref={ref} className="chapter" aria-labelledby={`${id}-title`}>
      <div className="chapter-head"><span className="chapter-num">{num}</span></div>
      <h2 id={`${id}-title`}>{title}</h2>
      {children}
    </section>
  );
}

/** Render children only once the element has come near the viewport (lazy data + paused offscreen work). */
export function WhenVisible({ children, minHeight = 300 }: { children: ReactNode; minHeight?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    if (!ref.current) return;
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { setSeen(true); io.disconnect(); } }, { rootMargin: "400px 0px" });
    io.observe(ref.current);
    return () => io.disconnect();
  }, []);
  return <div ref={ref} style={{ minHeight: seen ? undefined : minHeight }}>{seen ? children : null}</div>;
}

export function useFindings() {
  const summary = useData<SummaryPayload>("summary.json");
  const agreement = useData<AgreementPayload>("agreement.json");
  const neighbours = useData<NeighbourStats>("neighbour_stats.json");
  const nulls = useData<NullsPayload>("nulls.json");
  const row = (graph: string, label: string, seed = 42): AgreementRow | undefined =>
    agreement.data?.rows.find((r) => r.graph_id === graph && r.label === label && r.seed === seed);
  return { summary: summary.data, agreement: agreement.data, neighbours: neighbours.data, nulls: nulls.data, row,
    loading: summary.loading || agreement.loading || neighbours.loading, error: summary.error || agreement.error || neighbours.error };
}

/** Pre-declared rule: an ordering is stated only if NMI excess, assortativity r and neighbour lift agree. */
export function verdict(a: { excess: number; r: number; lift: number }, b: { excess: number; r: number; lift: number }, nameA: string, nameB: string) {
  const s = [Math.sign(a.excess - b.excess), Math.sign(a.r - b.r), Math.sign(a.lift - b.lift)];
  if (s.every((x) => x > 0)) return { text: `${nameA} > ${nameB} on all three`, consistent: true, winner: nameA };
  if (s.every((x) => x < 0)) return { text: `${nameB} > ${nameA} on all three`, consistent: true, winner: nameB };
  return { text: "mixed (measures disagree)", consistent: false, winner: null };
}
