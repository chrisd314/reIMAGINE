import { createContext, useContext } from "react";
import type { Rep } from "../data";
import { Segmented } from "./ui";

// One representation choice shared by every page: switching to embeddings anywhere switches the maps, the
// neighbours and the results everywhere, until switched back.

export const RepContext = createContext<{ rep: Rep; setRep: (r: Rep) => void }>({ rep: "tfidf", setRep: () => {} });
export const useRep = () => useContext(RepContext);

export function RepToggle({ label = "Text representation" }: { label?: string }) {
  const { rep, setRep } = useRep();
  return (
    <Segmented label={label} value={rep} onChange={setRep}
      options={[{ value: "tfidf", label: "TF–IDF (words)" }, { value: "embedding", label: "Embeddings (meaning)" }]} />
  );
}
