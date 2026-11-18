import { useNear, useNetwork, useStory } from "../../data";
import { useRep } from "../../components/rep";
import { Failed, Loading, PageHead, Result } from "../../components/ui";
import { int } from "../../lib/format";
import { CorpusSection, SimilaritySection } from "./corpus";
import { CentralSection, NetworkSection } from "./network";
import { CommunitiesSection } from "./communities";
import { ChoicesSection, OrganiseSection } from "./organise";

export const FOLKTALE_SECTIONS = [
  { id: "corpus", label: "Tale types" },
  { id: "similarity", label: "Similarity" },
  { id: "network", label: "The network" },
  { id: "communities", label: "Communities" },
  { id: "organise", label: "Story, place or book?" },
  { id: "choices", label: "Edges as a choice" },
  { id: "central", label: "Central tales" },
];

export function FolktalesPage() {
  const { data: d, error } = useStory();
  const { data: net, error: e2 } = useNetwork();
  const { data: near } = useNear();
  const { rep } = useRep();
  if (error || e2) return <Failed error={(error ?? e2) as string} />;
  if (!d || !net) return <Loading what="the folktales" />;
  const maps = net.maps;
  const org = maps[rep].organise.find((o) => o.label === "atu_type" && o.measure === "nmi" && o.null === "label shuffle");
  return (
    <>
      <PageHead page="folktales" kicker="reIMAGINE · part 1 and 2" title="The folktale network"
        lede={<>Before parables can land anywhere, the folktales need a map. This page builds a network of {int(d.corpus.folktales)} folktales from their texts, finds its communities, and asks what they follow: the kind of story, the place it was recorded, or the book it was printed in. Every map can be zoomed, every tale opened, read and followed to its source; the switch at each section turns the whole page from TF–IDF to embeddings.</>}
        sections={FOLKTALE_SECTIONS} />
      <CorpusSection d={d} maps={maps} />
      <SimilaritySection d={d} near={near} />
      <NetworkSection maps={maps} />
      <CommunitiesSection d={d} maps={maps} near={near} />
      <OrganiseSection d={d} maps={maps} />
      <ChoicesSection d={d} net={net} />
      <CentralSection d={d} maps={maps} near={near} />
      <section className="chapter" aria-label="Summary">
        <div className="wrap">
          <Result title="What the folktale network tells us">
            <p>Text similarity alone recovers the folklorists' story types: communities follow ATU tale type far above chance ({org ? org.excess.toFixed(2) : "–"} NMI above shuffles), across every way of drawing the links, and beyond the books the tales come from. Place adds little once the book is accounted for. So the communities are a fair map of <em>kinds of story</em>, and that is the map the parables are placed on.</p>
          </Result>
          <div className="next-page"><a href="#/">← Overview</a><a href="#/explore">Explore the whole network</a><a href="#/parables">Part 3: placing the parables →</a></div>
        </div>
      </section>
    </>
  );
}
