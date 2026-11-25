"""Links from each folktale to the D. L. Ashliman Folktexts page it was taken from.

The corpus (Annotated Folktales) keeps no URL per tale, but its scraper (`fetch_ashliman.R` in the trilogy
repository) took every tale from a tale-type page listed on the collection's two index pages, and derived the
tale's ATU type from that page's name. The same rules, applied to the two saved index pages
(data/raw/metadata/ashliman_folktexts*.html), give back the page of every type. A few types have two pages.
Then both are listed. Links point at the pages' current address, https://sites.pitt.edu/~dash/.
"""
from __future__ import annotations

import re
from collections import defaultdict
from urllib.parse import quote

from .core.common import RAW

BASE = "https://sites.pitt.edu/~dash/"
INDEX_PAGES = ["metadata/ashliman_folktexts.html", "metadata/ashliman_folktexts2.html"]
# pages whose names do not contain their tale type (as recoded in fetch_ashliman.R)
RECODE = {"alibaba": "type0676", "animalindian": "type0402", "norway034": "type0402", "norway133": "type0133",
          "type2033": "type0020c", "friday": "type0779j*", "frog": "type0440", "hand": "type0958e*", "type1066": "type1343",
          "hog": "type0441", "monkey": "type0441", "melusina": "type4080", "norway010": "type1408", "norway120": "type0313",
          "midwife": "type5070"}
SUFFIX = re.compile(r"jack$|ast$|#longfellow$|#nigeria$|Blit$|fairy$|#shewolf$|abc$")
SKIP = {"ashliman.html", "folktexts.html", "folktexts2.html", "folklinks.html"}


def dataset_type(page_type: str) -> str:
    """'0910b' -> '910B', the form of `atu_id` in the corpus."""
    m = re.match(r"^0*(\d+)(.*)$", page_type)
    return (m.group(1) + m.group(2).upper()) if m else page_type.upper()


def type_pages() -> dict[str, list[str]]:
    """ATU type (corpus form) -> the Folktexts page(s) its tales were taken from, as full URLs."""
    pages: dict[str, list[str]] = defaultdict(list)
    for name in INDEX_PAGES:
        path = RAW / name
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        for href in re.findall(r'<a\s[^>]*?href\s*=\s*"([^"]+)"', html, flags=re.I):
            if href.startswith(("http", "mailto")) or re.search(r"#[a-z]$", href) or href in SKIP:
                continue
            short = href.replace(".html", "")
            rev = RECODE.get(short, short)
            if not rev.lower().startswith("type"):
                continue
            atu = dataset_type(SUFFIX.sub("", rev[4:]))
            url = BASE + href.split("#")[0]
            if url not in pages[atu]:
                pages[atu].append(url)
    return dict(pages)


def title_fragment(title: str) -> str:
    """A text fragment (#:~:text=...) that scrolls a browser to the tale's title on its page. The corpus adds a
    source tag in brackets to some titles, which the page does not print."""
    t = re.sub(r"\s*\([^)]*\)\s*$", "", str(title)).strip()
    return "#:~:text=" + quote(t, safe="") if t else ""
