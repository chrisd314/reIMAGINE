import { useMemo, useState } from "react";

// A search box with a short list of matches: type part of a title, pick a result with the mouse or the keyboard.

export interface SearchItem { key: string; label: string; sub: string }

export function Search({ items, onPick, placeholder = "Search a tale or a parable by title…", label = "Search" }: {
  items: SearchItem[]; onPick: (key: string) => void; placeholder?: string; label?: string;
}) {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const hits = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (s.length < 2) return [];
    const starts: SearchItem[] = [], contains: SearchItem[] = [];
    for (const it of items) {
      const l = it.label.toLowerCase();
      if (l.startsWith(s)) starts.push(it); else if (l.includes(s)) contains.push(it);
      if (starts.length > 12) break;
    }
    return [...starts, ...contains].slice(0, 12);
  }, [q, items]);
  const pick = (k: string) => { onPick(k); setQ(""); setActive(0); };
  return (
    <div className="search">
      <input type="search" value={q} placeholder={placeholder} aria-label={label} role="combobox" aria-expanded={hits.length > 0} aria-controls="search-list"
        onChange={(e) => { setQ(e.target.value); setActive(0); }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") { setActive((a) => Math.min(hits.length - 1, a + 1)); e.preventDefault(); }
          if (e.key === "ArrowUp") { setActive((a) => Math.max(0, a - 1)); e.preventDefault(); }
          if (e.key === "Enter" && hits[active]) pick(hits[active].key);
          if (e.key === "Escape") setQ("");
        }} />
      {hits.length > 0 && (
        <ul className="search-list" id="search-list" role="listbox">
          {hits.map((h, k) => (
            <li key={h.key} role="option" aria-selected={k === active}>
              <button type="button" onMouseDown={(e) => { e.preventDefault(); pick(h.key); }}>{h.label}<span className="muted"> · {h.sub}</span></button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
