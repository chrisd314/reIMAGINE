import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { load, taleUrl } from "../data/load";
import type { TalePayload } from "../data/types";
import { lexicalCosine, passageMatches, semanticCosine, sharedTerms, chunkVectors } from "../data/vectors";
import { fmt } from "../lib/format";
import { useMotion } from "../lib/motion";
import { ErrorState, Loading, Segmented } from "./ui";

type Mode = "passages" | "words";

function TaleMeta({ t }: { t: TalePayload }) {
  return (
    <div className="sans small" style={{ color: "var(--ink-2)", marginBottom: 10 }}>
      <div><strong>Recorded provenance:</strong> {t.provenance.label.join(" | ") || "unknown"}{t.provenance.status !== "unique" && <span className="chip warn" style={{ marginLeft: 6 }}>no defensible place</span>}</div>
      <div><strong>ATU type:</strong> {t.atu.id ? `${t.atu.id} — ${t.atu.name ?? ""}` : `none (${t.atu.status}${t.atu.ids.length ? ": " + t.atu.ids.join(", ") : ""})`}</div>
      <div><strong>Source:</strong> {t.source ?? "not recorded"}</div>
      {t.flags.includes("suspected_truncated_start") && <div className="chip warn" style={{ marginTop: 4 }}>opening may be missing in the dataset</div>}
    </div>
  );
}

function wordSpans(text: string, terms: Map<string, number>, maxC: number) {
  const out: ReactNode[] = [];
  const re = /\p{L}+/gu;
  let last = 0, m: RegExpExecArray | null, k = 0;
  while ((m = re.exec(text))) {
    const w = m[0].toLowerCase();
    const c = terms.get(w);
    if (c !== undefined) {
      if (m.index > last) out.push(text.slice(last, m.index));
      const a = 0.25 + 0.75 * Math.sqrt(c / maxC);
      out.push(<mark key={k++} className="word" style={{ background: `rgba(45,106,106,${a * 0.45})` }} title={`share of lexical cosine: ${(c * 100).toFixed(2)} points`}>{m[0]}</mark>);
      last = m.index + m[0].length;
    }
  }
  out.push(text.slice(last));
  return out;
}

export function PairReader({ a, b, onClose, onSwap }: { a: string; b: string; onClose: () => void; onSwap?: () => void }) {
  const { enabled: motion } = useMotion();
  const [ta, setTa] = useState<TalePayload | null>(null);
  const [tb, setTb] = useState<TalePayload | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("passages");
  const [active, setActive] = useState<{ side: "a" | "b"; chunk: number } | null>(null);
  const [side, setSide] = useState<"a" | "b">("a");
  const [compact, setCompact] = useState(false);
  const refsA = useRef<(HTMLSpanElement | null)[]>([]);
  const refsB = useRef<(HTMLSpanElement | null)[]>([]);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setTa(null); setTb(null); setErr(null); setActive(null);
    Promise.all([load<TalePayload>(taleUrl(a)), load<TalePayload>(taleUrl(b))]).then(([x, y]) => { setTa(x); setTb(y); }, (e: Error) => setErr(e.message));
  }, [a, b]);
  useEffect(() => { closeRef.current?.focus(); }, []);
  useEffect(() => {
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onClose]);

  const scores = useMemo(() => {
    if (!ta || !tb) return null;
    const pm = passageMatches(ta, tb, 3);
    return { lex: lexicalCosine(ta, tb), sem: semanticCosine(ta, tb), pm, shared: sharedTerms(ta, tb, 40) };
  }, [ta, tb]);

  // best counterpart for any clicked chunk
  const counterpart = (sideOf: "a" | "b", chunk: number) => {
    if (!ta || !tb) return null;
    const va = chunkVectors(ta), vb = chunkVectors(tb);
    const [src, dst, nDst] = sideOf === "a" ? [va, vb, tb.chunks.length] : [vb, va, ta.chunks.length];
    let best = -1, bs = -Infinity;
    for (let j = 0; j < nDst; j++) {
      let s = 0;
      for (let d = 0; d < 384; d++) s += src[chunk * 384 + d] * dst[j * 384 + d];
      if (s > bs) { bs = s; best = j; }
    }
    return { chunk: best, score: bs };
  };
  const activeMatch = active ? counterpart(active.side, active.chunk) : null;

  useEffect(() => {
    if (!active || !activeMatch) return;
    const target = active.side === "a" ? refsB.current[activeMatch.chunk] : refsA.current[activeMatch.chunk];
    target?.scrollIntoView({ behavior: motion ? "smooth" : "auto", block: "center" });
    if (window.innerWidth < 860) setSide(active.side === "a" ? "b" : "a");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active?.side, active?.chunk]);

  const renderText = (t: TalePayload, which: "a" | "b") => {
    if (mode === "words" && scores) {
      const terms = new Map(scores.shared.map((s) => [s.term, s.contribution]));
      const maxC = scores.shared[0]?.contribution ?? 1;
      return <p>{wordSpans(t.text, terms, maxC)}</p>;
    }
    const best = scores?.pm.best ?? [];
    const rankOf = (c: number) => best.findIndex((m) => (which === "a" ? m.a : m.b) === c);
    const isActive = (c: number) => active && ((active.side === which && active.chunk === c) || (activeMatch && active.side !== which && activeMatch.chunk === c));
    const refs = which === "a" ? refsA : refsB;
    return (
      <p>
        {t.chunks.map(([s, e], c) => {
          const r = rankOf(c);
          if (compact && r < 0 && !isActive(c)) return <span key={c} className="muted"> […] </span>;
          const cls = ["passage", r >= 0 ? `match rank${r}` : "", isActive(c) ? "active" : ""].join(" ");
          return (
            <span key={c} ref={(el) => { refs.current[c] = el; }} className={cls} role="button" tabIndex={0}
              aria-label={`Passage ${c + 1}${r >= 0 ? `, best match rank ${r + 1}` : ""}. Activate to find its closest passage in the other tale.`}
              onClick={() => setActive({ side: which, chunk: c })}
              onKeyDown={(ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); setActive({ side: which, chunk: c }); } }}>
              {t.text.slice(s, e)}{" "}
            </span>
          );
        })}
      </p>
    );
  };

  return (
    <div className="overlay" role="dialog" aria-modal="true" aria-label="Paired reader" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="reader">
        <div className="reader-head">
          <div style={{ flex: 1, minWidth: 260 }}>
            <div className="sans small muted" style={{ textTransform: "uppercase", letterSpacing: "0.08em" }}>Read a connection</div>
            {scores ? (
              <div className="row sans small" style={{ gap: 14, marginTop: 4 }}>
                <span><strong>Whole-tale similarity</strong> — TF–IDF {fmt(scores.lex)} · embeddings {fmt(scores.sem)}</span>
                <span><strong>Best passage pair</strong> (one chunk pair, embeddings) {fmt(scores.pm.best[0]?.score)}</span>
                {activeMatch && <span className="chip accent">selected passage ↔ counterpart {fmt(activeMatch.score)}</span>}
              </div>
            ) : <div className="sans small muted">computing scores…</div>}
          </div>
          <div className="row">
            <Segmented label="Highlight mode" value={mode} onChange={setMode} options={[
              { value: "passages", label: "Best passages", title: "Closest chunk pairs (embeddings)" },
              { value: "words", label: "Shared words", title: "Words whose TF-IDF weights both tales share" }]} />
            {mode === "passages" && <button className="btn small" onClick={() => setCompact((c) => !c)} aria-pressed={compact}>{compact ? "Read in context" : "Matched passages only"}</button>}
            <span className="reader-ab"><Segmented label="Show tale" value={side} onChange={setSide} options={[{ value: "a", label: "Tale A" }, { value: "b", label: "Tale B" }]} /></span>
            {onSwap && <button className="btn small" onClick={onSwap}>Swap</button>}
            <button ref={closeRef} className="btn small primary" onClick={onClose} aria-label="Close reader">Close ✕</button>
          </div>
        </div>
        {err && <ErrorState message={err} />}
        {!err && (!ta || !tb) && <Loading what="both tales" />}
        {ta && tb && scores && (
          <>
            <div className="sans small" style={{ padding: "8px 18px", borderBottom: "1px solid var(--rule)", background: "#fbf7ef", color: "var(--ink-2)" }}>
              {mode === "passages"
                ? "Shaded passages are the three closest chunk pairs under the embeddings model; click any passage to find and scroll to its closest counterpart. A passage match is not a full narrative alignment, and shading is not a word-level explanation."
                : <>Green words occur in both tales and carry TF–IDF weight in both. Shading is proportional to the word's exact share of the TF–IDF cosine (w<sub>A</sub>·w<sub>B</sub>). Top shared words: {scores.shared.slice(0, 12).map((s) => s.term).join(", ") || "none"}.</>}
            </div>
            <div className="reader-body">
              {(["a", "b"] as const).map((w) => {
                const t = w === "a" ? ta : tb;
                return (
                  <div key={w} className={`reader-col${side !== w ? " hidden-mobile" : ""}`}>
                    <div className="sans small muted">Tale {w.toUpperCase()} · {t.id} · {t.n_words.toLocaleString()} words</div>
                    <h3>{t.title}</h3>
                    <TaleMeta t={t} />
                    {mode === "words" && (
                      <div className="sans small" style={{ marginBottom: 10 }}>
                        <span className="muted">Most frequent content words here (normalised frequency, not TF–IDF): </span>
                        {t.frequencies.slice(0, 8).map(([term, f]) => `${term} ${(f * 100).toFixed(1)}%`).join(" · ")}
                      </div>
                    )}
                    {t.text_is_excerpt && <div className="callout warn sans small">Only an excerpt is shown in this build (full-text publication disabled).</div>}
                    {renderText(t, w)}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
