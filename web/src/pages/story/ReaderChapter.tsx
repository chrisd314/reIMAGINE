import { useEffect, useState } from "react";
import { load, taleUrl } from "../../data/load";
import type { TalePayload } from "../../data/types";
import { lexicalCosine, semanticCosine } from "../../data/vectors";
import { HowMade } from "../../components/ui";
import { fmt } from "../../lib/format";

const PAIRS = [
  { key: "opening", title: "A recognisable family", blurb: "The opening pair: same ATU type, recorded in Russia and China." },
  { key: "unexpected", title: "An unexpected match", blurb: "Very similar under embeddings, but catalogued as different tale types from different regions." },
  { key: "weak", title: "A weak match inside one type", blurb: "Same ATU type, yet among the least similar pairs: one type, very different tellings." },
];

function PairCard({ a, b, title, blurb, onRead }: { a: string; b: string; title: string; blurb: string; onRead: (a: string, b: string) => void }) {
  const [t, setT] = useState<[TalePayload, TalePayload] | null>(null);
  useEffect(() => { Promise.all([load<TalePayload>(taleUrl(a)), load<TalePayload>(taleUrl(b))]).then(([x, y]) => setT([x, y])); }, [a, b]);
  return (
    <article className="figure" style={{ margin: 0 }}>
      <div className="figure-title">{title}</div>
      <p className="sans small" style={{ color: "var(--ink-2)" }}>{blurb}</p>
      {t ? (
        <>
          <p style={{ fontSize: 16, margin: "0 0 4px" }}><strong>{t[0].title}</strong> <span className="muted small">({t[0].provenance.place}, ATU {t[0].atu.id})</span></p>
          <p style={{ fontSize: 16, margin: "0 0 10px" }}><strong>{t[1].title}</strong> <span className="muted small">({t[1].provenance.place}, ATU {t[1].atu.id})</span></p>
          <p className="sans small">Whole-tale similarity: embeddings <strong>{fmt(semanticCosine(t[0], t[1]))}</strong> · TF–IDF <strong>{fmt(lexicalCosine(t[0], t[1]))}</strong></p>
        </>
      ) : <p className="muted small">loading…</p>}
      <button className="btn accent" onClick={() => onRead(a, b)}>Read this pair</button>
    </article>
  );
}

export function ReaderChapter({ pairs, onRead }: { pairs: Record<string, { a: string; b: string }>; onRead: (a: string, b: string) => void }) {
  return (
    <div>
      <p className="prose">Numbers only point to where to look; reading decides what a match means. The reader shows two tales side by side. In <em>Best passages</em> mode it shades the three closest passage pairs under the embeddings model, and clicking any passage finds its closest counterpart. In <em>Shared words</em> mode it shades words in both tales by their exact contribution to the TF–IDF cosine. Neither mode explains why the model scored the pair as it did.</p>
      <div className="grid-3">
        {PAIRS.map((p) => pairs[p.key] && <PairCard key={p.key} a={pairs[p.key].a} b={pairs[p.key].b} title={p.title} blurb={p.blurb} onRead={onRead} />)}
      </div>
      <p className="sans small muted" style={{ marginTop: 12 }}>Any edge in the network and any neighbour row also opens this reader. The weak and unexpected pairs are shown on purpose: similarity scores mix plot, genre, register and translation style.</p>
      <HowMade
        measured="Whole-tale cosine (both representations), best-passage cosine between ~200-token chunks, and each shared word's product of TF–IDF weights."
        records="The two selected tales; scores are recomputed in your browser from exported vectors (they match the pipeline to at least 3 decimals)."
        method="Cosine similarity (weeks 5–6); passage-level retrieval (week 7, §6)."
        infer="Where two texts overlap in wording or in passage-level content."
        cannot="A passage match is not a full narrative alignment, and shading is not a causal explanation of a model's score (except the exact TF–IDF decomposition shown in Shared words)." />
    </div>
  );
}
