import { useEffect, useMemo, useState } from "react";
import { MotionContext, motionEnabled, readMotionPref, writeMotionPref, type MotionPref } from "./lib/motion";
import { useRoute } from "./lib/router";
import { onRunMismatch, useData } from "./data/load";
import type { ManifestPayload } from "./data/types";
import { ToastHost } from "./components/ui";
import { SectionBoundary } from "./components/SectionBoundary";
import { Story } from "./pages/Story";
import { Explore } from "./pages/Explore";
import { DataMethods } from "./pages/DataMethods";
import { Validation } from "./pages/Validation";
import { Sources } from "./pages/Sources";

const NAV = [
  { path: "/", label: "Story" },
  { path: "/explore", label: "Explore" },
  { path: "/data", label: "Data & Methods" },
  { path: "/validation", label: "Validation" },
  { path: "/sources", label: "Sources" },
];

function Logo() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden>
      <circle cx="16" cy="16" r="10.5" fill="none" stroke="#1d2b33" strokeWidth="2" />
      <path d="M5.5 16h21M16 5.5c3.6 3 3.6 18 0 21M16 5.5c-3.6 3-3.6 18 0 21" fill="none" stroke="#1d2b33" strokeWidth="1.4" />
      <circle cx="22" cy="11" r="2.6" fill="#b4532a" />
    </svg>
  );
}

export default function App() {
  const [route, navigate] = useRoute();
  const [pref, setPrefState] = useState<MotionPref>(readMotionPref());
  const enabled = motionEnabled(pref);
  const manifest = useData<ManifestPayload>("manifest.json");
  const [mismatch, setMismatch] = useState<string | null>(null);
  useEffect(() => onRunMismatch(setMismatch), []);
  useEffect(() => { document.documentElement.dataset.motion = enabled ? "on" : "off"; }, [enabled]);
  const setPref = (p: MotionPref) => { setPrefState(p); writeMotionPref(p); };
  const motionCtx = useMemo(() => ({ enabled, pref, setPref }), [enabled, pref]);
  const path = route.path === "" ? "/" : route.path;
  useEffect(() => {
    const titles: Record<string, string> = { "/": "Story", "/explore": "Explore", "/data": "Data & Methods", "/validation": "Validation", "/sources": "Sources" };
    document.title = `${titles[path] ?? "Story"} · Once Upon a World`;
    window.scrollTo({ top: 0 });
  }, [path]);

  let page;
  switch (path) {
    case "/explore": page = <Explore route={route} navigate={navigate} />; break;
    case "/data": page = <DataMethods route={route} navigate={navigate} />; break;
    case "/validation": page = <Validation />; break;
    case "/sources": page = <Sources />; break;
    default: page = <Story route={route} navigate={navigate} />;
  }

  return (
    <MotionContext.Provider value={motionCtx}>
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <header className="site-header">
        <a className="brand" href="#/" aria-label="Once Upon a World, home"><Logo /><span>Once Upon a World</span></a>
        <nav className="site-nav" aria-label="Main">
          {NAV.map((n) => <a key={n.path} href={`#${n.path}`} aria-current={path === n.path ? "page" : undefined}>{n.label}</a>)}
        </nav>
        <div className="header-tools">
          <button className="btn small" aria-pressed={enabled} onClick={() => setPref(enabled ? "off" : "on")} title={pref === "system" ? "Following your system motion setting" : "Motion preference saved in this browser"}>
            <span aria-hidden>{enabled ? "◐" : "○"}</span><span className="lbl">Motion {enabled ? "on" : "off"}</span>
          </button>
        </div>
      </header>
      {mismatch && <div className="callout warn sans small" role="alert" style={{ margin: 0, borderRadius: 0 }}>Data mismatch: {mismatch} Rebuild the site with a single pipeline export.</div>}
      <main id="main" tabIndex={-1}><SectionBoundary key={path} name={`page ${path}`}>{page}</SectionBoundary></main>
      {path !== "/explore" && (
        <footer className="site-footer">
          <div className="inner">
            <div>
              <strong>Once Upon a World</strong> — a DTU 02805 course project. Texts and labels: Annotated Folktales (Hagedorn &amp; Darányi 2022) from D. L. Ashliman's Folktexts, CC BY-NC-SA 4.0 per the repository LICENSE.md. Noncommercial, educational use with attribution. See <a href="#/sources">Sources</a>.
            </div>
            <div className="mono">run {manifest.data?.run_id ?? "…"} · schema {manifest.data?.schema_version ?? "…"} · local preview</div>
          </div>
        </footer>
      )}
      <ToastHost />
    </MotionContext.Provider>
  );
}
