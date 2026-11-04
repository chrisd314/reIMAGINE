import { useCallback, useEffect, useState } from "react";

// Hash routing keeps the static build working from any folder.
// Form: #/explore?tale=tale-0123&rep=semantic&d=10 ...

export interface Route { path: string; params: Record<string, string> }

export function parseHash(hash: string = window.location.hash): Route {
  const h = hash.replace(/^#/, "") || "/";
  const [path, query = ""] = h.split("?");
  const params: Record<string, string> = {};
  new URLSearchParams(query).forEach((v, k) => { params[k] = v; });
  return { path: path || "/", params };
}

export function buildHash(path: string, params: Record<string, string | null | undefined>): string {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== "") q.set(k, v); });
  const s = q.toString();
  return `#${path}${s ? `?${s}` : ""}`;
}

export function useRoute(): [Route, (path: string, params?: Record<string, string | null | undefined>, replace?: boolean) => void] {
  const [route, setRoute] = useState<Route>(() => parseHash());
  useEffect(() => {
    const on = () => setRoute(parseHash());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  const navigate = useCallback((path: string, params: Record<string, string | null | undefined> = {}, replace = false) => {
    const h = buildHash(path, params);
    if (replace) {
      history.replaceState(null, "", h);
      setRoute(parseHash(h));
    } else {
      window.location.hash = h;
    }
  }, []);
  return [route, navigate];
}

/** Update some params of the current route without adding history entries. */
export function patchParams(route: Route, patch: Record<string, string | null | undefined>): string {
  const params: Record<string, string | null | undefined> = { ...route.params, ...patch };
  return buildHash(route.path, params);
}
