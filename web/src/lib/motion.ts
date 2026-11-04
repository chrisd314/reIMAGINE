import { createContext, useContext } from "react";

export type MotionPref = "system" | "on" | "off";

export function systemReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

export function readMotionPref(): MotionPref {
  try {
    const v = localStorage.getItem("ouaw-motion");
    if (v === "on" || v === "off") return v;
  } catch { /* storage may be unavailable */ }
  return "system";
}

export function writeMotionPref(p: MotionPref) {
  try { localStorage.setItem("ouaw-motion", p); } catch { /* ignore */ }
}

export function motionEnabled(p: MotionPref): boolean {
  return p === "on" ? true : p === "off" ? false : !systemReducedMotion();
}

export const MotionContext = createContext<{ enabled: boolean; pref: MotionPref; setPref: (p: MotionPref) => void }>({
  enabled: true, pref: "system", setPref: () => {},
});
export const useMotion = () => useContext(MotionContext);

export const DUR = { feedback: 180, layout: 700, expand: 400, recolour: 500, list: 500 };
export const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
