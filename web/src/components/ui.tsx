import { useEffect, useState, type ReactNode } from "react";

export function Loading({ what = "data" }: { what?: string }) {
  return <div className="state" role="status"><span className="spinner" aria-hidden /> Loading {what}…</div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="state error" role="alert">Something went wrong: {message}. Try reloading; if it persists, regenerate the data with the export step.</div>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="state">{children}</div>;
}

export interface HowMadeProps {
  measured: ReactNode; records: ReactNode; method: ReactNode; infer: ReactNode; cannot: ReactNode; open?: boolean;
}

/** "How this was made": what is measured, which records, method + course section, what can and cannot be inferred. */
export function HowMade({ measured, records, method, infer, cannot, open }: HowMadeProps) {
  return (
    <details className="how" open={open}>
      <summary>How this was made</summary>
      <dl>
        <dt>What is measured</dt><dd>{measured}</dd>
        <dt>Which records</dt><dd>{records}</dd>
        <dt>Method (course)</dt><dd>{method}</dd>
        <dt>What can be inferred</dt><dd>{infer}</dd>
        <dt>What cannot</dt><dd>{cannot}</dd>
      </dl>
    </details>
  );
}

export function Legend({ title, items, ring }: { title: string; items: { label: string; colour: string; count?: number }[]; ring?: boolean }) {
  return (
    <div>
      <div className="legend-title">{title}</div>
      <div className="legend">
        {items.map((it) => (
          <span key={it.label} className="item">
            <span className={`swatch${ring ? " ring" : ""}`} style={ring ? { borderColor: it.colour } : { background: it.colour }} />
            {it.label}{it.count !== undefined && <span className="muted">&nbsp;{it.count}</span>}
          </span>
        ))}
      </div>
    </div>
  );
}

export function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: { value: T; label: string; title?: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} title={o.title} onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

let toastSetter: ((m: string | null) => void) | null = null;
export function toast(msg: string) { toastSetter?.(msg); }
export function ToastHost() {
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => { toastSetter = setMsg; return () => { toastSetter = null; }; }, []);
  useEffect(() => { if (!msg) return; const t = setTimeout(() => setMsg(null), 2600); return () => clearTimeout(t); }, [msg]);
  return msg ? <div className="toast" role="status" aria-live="polite">{msg}</div> : null;
}

export function downloadText(filename: string, text: string, type = "text/csv") {
  const blob = new Blob([text], { type: `${type};charset=utf-8` });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

export function downloadDataUrl(filename: string, url: string) {
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
}

export function toCsv(rows: (string | number | boolean | null | undefined)[][]): string {
  return rows.map((r) => r.map((v) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }).join(",")).join("\n");
}

export async function copyLink(url: string) {
  try {
    await navigator.clipboard.writeText(url);
    toast("View link copied. It points to this local preview.");
  } catch {
    window.prompt("Copy this link (local preview URL):", url);
  }
}
