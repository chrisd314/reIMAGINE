import { useEffect, useState, type ReactNode } from "react";

export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; label: string;
}) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

export interface Tip { x: number; y: number; body: ReactNode }

export function Tooltip({ tip }: { tip: Tip | null }) {
  if (!tip) return null;
  const left = Math.max(8, Math.min(tip.x + 14, window.innerWidth - 310));
  return <div className="tooltip" role="status" style={{ left, top: tip.y + 16 }}>{tip.body}</div>;
}

/** Chart colours come from CSS tokens so light and dark mode stay in step; canvas code reads them here. */
export function useTokens(names: string[]): Record<string, string> {
  const read = () => {
    const s = getComputedStyle(document.documentElement);
    return Object.fromEntries(names.map((n) => [n, s.getPropertyValue(`--${n}`).trim()]));
  };
  const [tokens, setTokens] = useState(read);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const on = () => setTokens(read());
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return tokens;
}

/** True on phone-width screens, where charts switch to a narrower drawing so their text stays readable. */
export function useNarrow(px = 600): boolean {
  const q = `(max-width: ${px}px)`;
  const [narrow, setNarrow] = useState(() => window.matchMedia(q).matches);
  useEffect(() => {
    const mq = window.matchMedia(q);
    const on = () => setNarrow(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, [q]);
  return narrow;
}

/** A collapsed table under a chart: the same numbers as text. */
export function DataTable({ head, rows, caption = "Show the numbers" }: { head: string[]; rows: (string | number)[][]; caption?: string }) {
  return (
    <details className="table">
      <summary>{caption}</summary>
      <div className="table-wrap">
        <table className="data">
          <thead><tr>{head.map((h, i) => <th key={h} className={i ? "n" : undefined}>{h}</th>)}</tr></thead>
          <tbody>{rows.map((r, k) => <tr key={k}>{r.map((c, i) => <td key={i} className={i ? "n" : undefined}>{c}</td>)}</tr>)}</tbody>
        </table>
      </div>
    </details>
  );
}

/** One analysis section of a page: a kicker (page · step), a heading, then its content. */
export function Chapter({ id, num, title, children }: { id: string; num: string; title: string; children: ReactNode }) {
  return (
    <section className="chapter" id={id} aria-labelledby={`${id}-h`}>
      <div className="wrap">
        <div className="chapter-head"><div className="num">{num}</div><h2 id={`${id}-h`}>{title}</h2></div>
        {children}
      </div>
    </section>
  );
}

/** What was analysed and why, side by side, at the start of every section; `course` names the course week. */
export function Why({ what, why, course }: { what: ReactNode; why: ReactNode; course?: string }) {
  return (
    <div className="why">
      <div><h4>What we did</h4><p>{what}</p></div>
      <div><h4>Why</h4><p>{why}</p>{course && <p className="course-ref">Course: {course}</p>}</div>
    </div>
  );
}

export function Result({ title = "What we found", children }: { title?: string; children: ReactNode }) {
  return <div className="result"><h4>{title}</h4>{children}</div>;
}

/** The header of an analysis page, with links to each of its sections. */
export function PageHead({ kicker, title, lede, sections, page }: {
  kicker: string; title: string; lede: ReactNode; sections: { id: string; label: string }[]; page: string;
}) {
  return (
    <header className="page-head">
      <div className="wrap">
        <div className="kicker">{kicker}</div>
        <h1>{title}</h1>
        <p className="lede">{lede}</p>
        <nav className="toc" aria-label="Sections of this page">
          {sections.map((s, k) => <a key={s.id} href={`#/${page}/${s.id}`}><span className="n">{k + 1}</span>{s.label}</a>)}
        </nav>
      </div>
    </header>
  );
}

/** Horizontal bars with the value written at the end; hover shows the label in full. With `onPick`, each bar is a
 *  button that selects its item (pressed bars are outlined). */
export function BarList({ items, max, format = (v) => String(v), tone = "c1", label, onPick, selected }: {
  items: { label: string; value: number; note?: string; key?: string }[]; max?: number; format?: (v: number) => string; tone?: string; label: string;
  onPick?: (key: string) => void; selected?: string | null;
}) {
  const top = max ?? Math.max(...items.map((i) => i.value), 1e-9);
  return (
    <ul className={`barlist${onPick ? " pickable" : ""}`} aria-label={label}>
      {items.map((i) => {
        const key = i.key ?? i.label;
        const body = <>
          <span className="bl-label">{i.label}</span>
          <span className="bl-bar"><span style={{ width: `${(100 * i.value) / top}%`, background: `var(--${tone})` }} /></span>
          <span className="bl-value">{format(i.value)}</span>
        </>;
        return (
          <li key={key} title={i.note ?? i.label}>
            {onPick ? <button type="button" aria-pressed={selected === key} onClick={() => onPick(key)}>{body}</button> : body}
          </li>
        );
      })}
    </ul>
  );
}

export function Loading({ what = "the data" }: { what?: string }) {
  return <div className="state">Opening {what}…</div>;
}

export function Failed({ error }: { error: string }) {
  return <div className="state error" role="alert">The data could not be loaded ({error}).</div>;
}
