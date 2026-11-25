"""The website's data files: excerpt-only, complete, consistent with each other and with the pipeline's results."""
import json
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "data" / "site"
FILES = ("story.json", "network.json", "near.json")


@pytest.fixture(scope="module")
def site():
    if not all((SITE / f).exists() for f in FILES):
        pytest.skip("data/site is not built yet")
    return {f.split(".")[0]: json.loads((SITE / f).read_text(encoding="utf-8")) for f in FILES}


def openings(obj, key=""):
    """Every string stored under a key that names an opening, anywhere in a payload."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from openings(v, key if "opening" in key.lower() else k)
    elif isinstance(obj, list):
        for v in obj:
            yield from openings(v, key)
    elif isinstance(obj, str) and "opening" in key.lower():
        yield obj


def test_only_short_openings_are_published(site):
    limit = site["story"]["settings"]["openingWords"]
    found = [o for payload in site.values() for o in openings(payload)]
    assert len(found) >= 1462 + 449 + 2 * 36, "openings of folktales, texts and retellings expected"
    assert max(len(o.replace(" …", "").split()) for o in found) <= limit
    assert not any("text" in t for t in site["story"]["texts"]), "full texts must never be in the site data"


def test_indices_and_counts_agree(site):
    s, net, near = site["story"], site["network"], site["near"]
    n = len(s["folktales"]["title"])
    assert n == s["corpus"]["folktales"] == len(near["opening"])
    for rep, m in net["maps"].items():
        assert len(m["x"]) == len(m["group"]) == len(m["degree"]) == len(m["pagerank"]) == n
        assert all(0 <= i < n for i in m["edges"]) and len(m["edges"]) % 2 == 0
        assert all(len(p) == n for p in m["partitions"].values()) and all(len(p) == n for p in m["seeds"]["partitions"].values())
        assert all(len(v) == n for v in m["densities"]["degrees"].values())
        assert sum(m["degree"]) == 2 * m["stats"]["edges"]
        assert {c["name"] for c in m["communities"]} >= {f"C{g + 1}" for g in set(m["group"]) if g >= 0}
        nn = near["folk"][rep]
        assert len(nn["idx"]) == n and all(i not in row and all(0 <= j < n for j in row) for i, row in enumerate(nn["idx"]))
    for t in s["texts"]:
        for rep in s["reps"]:
            assert all(0 <= i < n for i in t["rep"][rep]["nearest"])
            assert t["id"] in near["texts"][rep]
    assert sum(t["kind"] == "parable" for t in s["texts"]) == s["corpus"]["parables"]
    assert len(s["calibration"]["items"]) == s["calibration"]["queries"]


def test_browser_shuffles_start_from_the_published_values(site):
    """The label test of the site recomputes NMI from exported arrays; it must equal the pipeline's value."""
    from reimagine.core.metrics import codes, nmi
    F = site["story"]["folktales"]
    for rep, m in site["network"]["maps"].items():
        nodes, part = m["labelTest"]["nodes"], m["labelTest"]["part"]
        for label, col in (("atu_type", "atu"), ("region", "region"), ("source_collection", "collection")):
            ref = next(o["observed"] for o in m["organise"] if o["label"] == label and o["measure"] == "nmi" and o["null"] == "label shuffle")
            assert nmi(codes(part)[0], codes([F[col][i] for i in nodes])[0]) == pytest.approx(ref, abs=1e-4), (rep, label)


def test_every_tale_can_be_read_at_its_source(site):
    s = site["story"]
    pages = s["links"]["typePages"]
    typed = [a for a in s["folktales"]["atu"] if a]
    linked = sum(a in pages for a in typed)
    assert linked / len(typed) > 0.95, f"only {linked} of {len(typed)} typed tales link to their Folktexts page"
    assert all(u.startswith("https://sites.pitt.edu/~dash/") for urls in pages.values() for u in urls)
    assert all(t["url"].startswith("https://") for t in s["texts"])


def test_every_check_of_the_site_exists_in_the_data(site):
    variants = {r["variant"] for r in site["story"]["robust"]}
    expected = {"tfidf (headline)", "embedding", "tfidf, regression at equal length", "tfidf_nouns_masked",
                "tfidf, names and formulae masked", "tfidf, hubs removed"}
    assert expected <= variants, expected - variants
    assert any(v.startswith("tfidf, communities of") for v in variants)


def test_folktexts_page_rules():
    """The corpus's scraper derived a tale's ATU type from its page name; the links invert that rule."""
    from reimagine.folktexts import dataset_type, title_fragment
    assert dataset_type("0910b") == "910B" and dataset_type("0001") == "1" and dataset_type("0779j*") == "779J*"
    assert title_fragment("The Race (Parsons2)") == "#:~:text=The%20Race"
    assert title_fragment("Cinderella") == "#:~:text=Cinderella"
