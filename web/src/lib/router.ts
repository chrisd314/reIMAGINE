import { useEffect, useState } from "react";

// Hash routing keeps the static build working from any folder: #/ is the story, #/methods the methods page,
// and #/chapter-id scrolls the story to a chapter.

export function useHashPath(): string {
  const read = () => (window.location.hash.replace(/^#/, "").split("?")[0] || "/");
  const [path, setPath] = useState(read);
  useEffect(() => {
    const on = () => setPath(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return path;
}
