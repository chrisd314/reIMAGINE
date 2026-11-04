"""Draft generator for data/mappings/provenance_map.csv.

This script produced the first version of the provenance mapping table from the
distinct raw provenance strings in the pinned aft.csv. The CSV it writes is the
version-controlled source of truth; the pipeline only reads and validates it.
Re-running this script overwrites manual edits, so prefer editing the CSV.

Decisions encoded here (see LIMITATIONS.md and the rationale column):
- A raw string yields a place only if it names a country, a sub-national or
  historical region inside one modern country, or a community. Author-only and
  collection-only strings stay geographically unknown.
- Sub-national/historical regions are located at their modern country's
  Natural Earth label point (country resolution); the region is kept as detail.
- Communities keep their own label; they receive coordinates only when the
  string or the cited source establishes the country of recording.
- Strings naming several places get no place label; they get a broad region
  only when all places share one UN M49 sub-region.
- Broad regions are UN M49 sub-regions (Natural Earth SUBREGION, with the
  African and American intermediate regions merged into "Sub-Saharan Africa"
  and "Latin America and the Caribbean").
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "mappings" / "provenance_map.csv"

NE_SOURCE = "Natural Earth 1:50m Admin 0 v5.1.2 (LABEL_X/LABEL_Y, SUBREGION)"
NE_MEANING = ("Natural Earth label point of the modern country/territory: an approximate "
              "representative point for the recorded association, not a place of origin")
M49_URL = "https://unstats.un.org/unsd/methodology/m49/"

MERGE_SUBREGION = {
    "Eastern Africa": "Sub-Saharan Africa", "Western Africa": "Sub-Saharan Africa",
    "Middle Africa": "Sub-Saharan Africa", "Southern Africa": "Sub-Saharan Africa",
    "Caribbean": "Latin America and the Caribbean", "Central America": "Latin America and the Caribbean",
    "South America": "Latin America and the Caribbean",
}

# place key -> (label, kind, iso code or None, coordinate source, broad region if not from NE)
# coordinate source: ("ne", ISO_A2_EH) | ("sub", SU_A3) | None
PLACES = {
    # countries / territories located with Natural Earth
    **{k: (k, "country", iso, ("ne", iso), None) for k, iso in {
        "Germany": "DE", "India": "IN", "Italy": "IT", "Ireland": "IE", "Norway": "NO", "Russia": "RU",
        "Denmark": "DK", "Philippines": "PH", "Switzerland": "CH", "Romania": "RO", "France": "FR",
        "Turkey": "TR", "Pakistan": "PK", "Hungary": "HU", "Sri Lanka": "LK", "Austria": "AT",
        "Serbia": "RS", "Greece": "GR", "Sweden": "SE", "Poland": "PL", "Finland": "FI", "Japan": "JP",
        "Iceland": "IS", "Spain": "ES", "Netherlands": "NL", "Georgia": "GE", "Jamaica": "JM",
        "Palestine": "PS", "Portugal": "PT", "Lithuania": "LT", "Ukraine": "UA", "South Africa": "ZA",
        "China": "CN", "Croatia": "HR", "Estonia": "EE", "Belgium": "BE", "Czechia": "CZ", "Albania": "AL",
        "Fiji": "FJ", "Bulgaria": "BG", "Somalia": "SO", "Mongolia": "MN", "Egypt": "EG", "Syria": "SY",
        "Iran": "IR", "Algeria": "DZ", "Canada": "CA", "Bahamas": "BS", "Madagascar": "MG", "Brazil": "BR",
        "Antigua and Barbuda": "AG", "Malaysia": "MY", "Tanzania": "TZ", "USA": "US", "Slovakia": "SK",
        "Bangladesh": "BD", "Nepal": "NP", "Australia": "AU", "Isle of Man": "IM", "Guernsey": "GG",
        "Greenland": "GL", "North Macedonia": "MK",
    }.items()},
    # constituent nations of the United Kingdom (Natural Earth map subunits)
    "England": ("England", "constituent nation", "GB-ENG", ("sub", "ENG"), None),
    "Scotland": ("Scotland", "constituent nation", "GB-SCT", ("sub", "SCT"), None),
    "Wales": ("Wales", "constituent nation", "GB-WLS", ("sub", "WLS"), None),
    # regions not representable by one modern country: label kept, no coordinates
    "Kashmir": ("Kashmir", "region", None, None, "Southern Asia"),
    "Tibet": ("Tibet", "region", None, None, "Eastern Asia"),
    "Punjab": ("Punjab", "region", None, None, "Southern Asia"),
    "Korea": ("Korea", "region", None, None, "Eastern Asia"),
    # communities: own label kept; coordinates only where the record establishes the country
    **{k: (k, "community", None, None, "Northern America") for k in [
        "Zuni", "Chickasaw", "Cherokee", "Shasta", "Biloxi", "Ojibwe", "Sanpoil", "Blackfeet",
        "Passamaquoddy", "Tsimshian", "Okanagan", "Nez Perce", "Skidi Pawnee", "Nlaka'pamux"]},
    "African American": ("African American", "community", "US", ("ne", "US"), None),
    "Irish American": ("Irish American", "community", "US", ("ne", "US"), None),
    "German American": ("German American", "community", "US", ("ne", "US"), None),
    "Armenian American": ("Armenian American", "community", "US", ("ne", "US"), None),
    "Louisiana French": ("Louisiana French", "community", "US", ("ne", "US"), None),
    "Greenlandic Inuit": ("Greenlandic Inuit", "community", "GL", ("ne", "GL"), None),
    "Basque": ("Basque", "community", None, None, "Western Europe"),
    "Swahili": ("Swahili", "community", None, None, "Sub-Saharan Africa"),
    "Kabyle": ("Kabyle", "community", None, None, "Northern Africa"),
    "Telugu": ("Telugu", "community", None, None, "Southern Asia"),
    "Sorbian": ("Sorbian (Wendish)", "community", None, None, "Western Europe"),
    "Romani (Czech lands and Slovakia)": ("Romani (Czech lands and Slovakia)", "community", None, None, "Eastern Europe"),
}

# Aliases: substrings of raw strings that denote a place key, with optional detail
ALIASES = [
    # (regex, place key, detail)
    (r"\bUnited States of America\b|\bUSA\b|North Carolina|Virginia|Idaho|New York|Connecticut|Florida|Georgia, USA", "USA", None),
    (r"\bGermany\b|\bGerman\b(?! Language| Hungary)|Swabia|Lower Lusatia", "Germany", None),
    (r"\bEngland\b|Devonshire|Yorkshire|Cornwall|Derbyshire|Nottinghamshire|Herefordshire|Northumberland|Sunderland|\bEnglish\b(?! Proverb)", "England", None),
    (r"\bScotland\b|Orkney|Shetland", "Scotland", None),
    (r"\bWales\b", "Wales", None),
    (r"\bIreland\b", "Ireland", None),
    (r"Isle of Man", "Isle of Man", None),
    (r"Guernsey", "Guernsey", None),
    (r"\bIndia\b|Southern India|Northern India", "India", None),
    (r"\bItaly\b|Sicily|Tuscany", "Italy", None),
    (r"\bNorway\b", "Norway", None),
    (r"\bRussia\b", "Russia", None),
    (r"\bDenmark\b", "Denmark", None),
    (r"\bPhilippines\b", "Philippines", None),
    (r"\bSwitzerland\b", "Switzerland", None),
    (r"\bRomania\b|Transylvania", "Romania", None),
    (r"\bFrance\b|Alsace", "France", None),
    (r"\bTurkey\b", "Turkey", None),
    (r"\bPakistan\b", "Pakistan", None),
    (r"\bHungary\b", "Hungary", None),
    (r"Sri Lanka", "Sri Lanka", None),
    (r"\bAustria\b", "Austria", None),
    (r"\bSerbia\b", "Serbia", None),
    (r"\bGreece\b", "Greece", None),
    (r"\bSweden\b", "Sweden", None),
    (r"\bPoland\b", "Poland", None),
    (r"\bFinland\b", "Finland", None),
    (r"\bJapan\b", "Japan", None),
    (r"\bIceland\b", "Iceland", None),
    (r"\bSpain\b|Catalonia", "Spain", None),
    (r"\bPortugal\b", "Portugal", None),
    (r"\bNetherlands\b", "Netherlands", None),
    (r"^Georgia$", "Georgia", None),
    (r"\bJamaica\b", "Jamaica", None),
    (r"\bPalestine\b", "Palestine", None),
    (r"\bLithuania\b", "Lithuania", None),
    (r"\bUkraine\b", "Ukraine", None),
    (r"South Africa", "South Africa", None),
    (r"\bChina\b", "China", None),
    (r"\bCroatia\b", "Croatia", None),
    (r"\bEstonia\b", "Estonia", None),
    (r"\bBelgium\b|Flanders", "Belgium", None),
    (r"Czech Republic|\bCzechia\b|Bohemia\b|Moravia\b", "Czechia", None),
    (r"\bAlbania\b", "Albania", None),
    (r"\bFiji\b", "Fiji", None),
    (r"\bBulgaria\b", "Bulgaria", None),
    (r"\bSomalia\b", "Somalia", None),
    (r"\bMongolia\b", "Mongolia", None),
    (r"\bEgypt\b", "Egypt", None),
    (r"\bSyria\b", "Syria", None),
    (r"\bIran\b|^Persia$|India/Persia", "Iran", None),
    (r"\bAlgeria\b", "Algeria", None),
    (r"\bCanada\b", "Canada", None),
    (r"\bBahamas\b", "Bahamas", None),
    (r"\bMadagascar\b", "Madagascar", None),
    (r"\bBrazil\b", "Brazil", None),
    (r"\bAntigua\b", "Antigua and Barbuda", None),
    (r"\bMalaya\b", "Malaysia", None),
    (r"\bZanzibar\b", "Tanzania", None),
    (r"\bBangladesh\b", "Bangladesh", None),
    (r"\bNepal\b", "Nepal", None),
    (r"\bAustralia\b", "Australia", None),
    (r"^Kashmir$", "Kashmir", None),
    (r"\bTibet\b", "Tibet", None),
    (r"^Punjab$", "Punjab", None),
    (r"^Korea$", "Korea", None),
    (r"\(Zuni\)", "Zuni", None), (r"\(Chickasaw\)", "Chickasaw", None), (r"\(Cherokee\)", "Cherokee", None),
    (r"\(Shasta\)", "Shasta", None), (r"\(Biloxi\)", "Biloxi", None), (r"\(Ojibwa\)", "Ojibwe", None),
    (r"\(Sanpoil\)", "Sanpoil", None), (r"\(Blackfeet\)", "Blackfeet", None),
    (r"^Passamaquoddy$", "Passamaquoddy", None), (r"^Tsimshian$", "Tsimshian", None),
    (r"^Okanagon$", "Okanagan", None), (r"^Nez Percé$", "Nez Perce", None), (r"^Skidi Pawnee$", "Skidi Pawnee", None),
    (r"Ntlakyapamuk", "Nlaka'pamux", None),
    (r"African[- ]America", "African American", None),
    (r"^Irish-American$", "Irish American", None), (r"^German-American$", "German American", None),
    (r"^Armenian-American$", "Armenian American", None), (r"^French Louisiana$", "Louisiana French", None),
    (r"^Eskimo$", "Greenlandic Inuit", None),
    (r"^Basque", "Basque", None),
    (r"Swahili", "Swahili", None),
    (r"\(Kabyl\)", "Kabyle", None),
    (r"^Telugu Folktale$", "Telugu", None),
    (r"^Wendish$", "Sorbian", None),
    (r"^Gypsy \(Slovak, Moravian, and Bohemian\)$", "Romani (Czech lands and Slovakia)", None),
]

# Strings that name no defensible single place but do name one UN M49 sub-region.
REGION_ONLY = {
    "Scandinavia": ("Northern Europe", "region",
                    "Scandinavia spans several countries that all lie in UN M49 Northern Europe."),
    "West Africa": ("Sub-Saharan Africa", "region", "Multi-country region inside UN M49 Sub-Saharan Africa."),
    "French North Africa": ("Northern Africa", "region", "Former French territories of several North African states."),
    "Native American": ("Northern America", "community",
                        "Umbrella term for hundreds of distinct nations: no single community or place label."),
    "American Indian": ("Northern America", "community",
                        "Umbrella term for hundreds of distinct nations: no single community or place label."),
    "American Indian (Pueblo)": ("Northern America", "community",
                                 "'Pueblo' covers many distinct Pueblo communities; none specified."),
    "Salish": ("Northern America", "community", "'Salish' names a language family spanning many communities."),
    "Czechoslovakia": ("Eastern Europe", "region", "Historical state spanning modern Czechia and Slovakia."),
    "Bukovina": ("Eastern Europe", "region", "Historical region now split between Romania and Ukraine."),
}

UNKNOWN_NOTES = {
    "Europe": "Continent-scale label; too broad for a place or sub-region.",
    "Europe (Joseph Jacobs)": "Continent-scale label from a retelling collection; too broad.",
    "Slavic": "Ethnolinguistic umbrella spanning several UN sub-regions.",
    "A Slav Folktale": "Ethnolinguistic umbrella spanning several UN sub-regions.",
    "South Slavonic": "South Slavic speakers span UN Southern and Eastern Europe.",
    "Arabic": "Language, not a place.",
    "from the Arabic": "Language of the source text, not a place.",
    "Jewish": "Diaspora community; no place recorded.",
    "Macedonia": "Historical region now divided between Greece, North Macedonia and Bulgaria (two UN sub-regions).",
    "Austria-Hungary": "Historical state spanning several modern countries in two UN sub-regions.",
    "East Prussia": "Historical province now divided between Russia, Poland and Lithuania.",
    "Germany Finland (Wuokkiniemi)": "Contradictory string: names Germany and a Karelian village; source cites Baader's Baden collection. Left unresolved.",
    "German Hungary": "Ambiguous: German-speaking areas of historical Hungary include land now in Austria.",
    "Type 510B tales in the German Language": "Page section heading (language), not a provenance.",
    "Retold by D. L. Ashliman": "Retelling credit, not a provenance.",
    "A Modern Fable": "Genre description, not a provenance.",
    "Children's Story, USA": None,  # handled by alias (USA)
}

AUTHOR_PATTERNS = r"Aesop|Æsop|Fontaine|Grimm|Bierce|Chandler Harris|Perrault|Tolstoy|Basile|Jacobs|Boccaccio|Bartsch|Vitry|Lang\b|Chaucer|Luther|Kuhn|Straparola|Bracciolini|Poggio|Andersen|Grimmelshausen|Longfellow|Saxe|Marie de France|Abstemius|Kirchhof|Montanus|Alphonsi|Parnell|Wagenfeld|Baader|Grässe|Temme|Haas|Baring-Gould|Homer|Ovid|Horace|Pliny|Lucian|Shakespeare|Lessing|Goethe|Potter|Marelles|Irving|Buel|Wendover|Whitney|Babrius|Anianus|Avianus|Scott|Moore|MacDonald|Heine|Twain|Burton|Scudder|Parsons|Hartland|Taylor|Ramakrishna|Rumi|Sanai|Hodja|Richard the Lionheart|Bechstein|Djurklo|Dracott|Bompas|Juan Manuel|Busch|Schambach|Webster|Vernaleken|Crane|Halliwell|Gower|Rabelais|Kingscote|Hebel|Hofberg|Lando|Bebel|Sachs|Dickens|Burns|Pauli|North\b|Ludewig|Wolf\b|Niderberger|Beckwith|Asbjørnsen|Afanasyev"
COLLECTION_PATTERNS = r"1001 Nights|Panchatantra|Gesta Romanorum|Jataka|Bidpai|Kalila|Masnavi|Seven Wise Masters|Sindib|Mahabharata|Hitopadesa|Kath|Udāna|Talmud|First Book of Kings|Toledot Yeshu|Romance of the Rose|Odyssey|Metamorphoses|Suka Saptati|Forty Vezirs|Disciplina|Table Talk|Facetious|Pentamerone|Decameron|Facetiæ|cent nouvelles|Enclosed Garden|Wendunmuth|Blackwood|Voyage to New South Wales|Bacchante|English Proverb"

FLAG_PATTERNS = {
    "contaminated_string": r"Old Boreas|You certainly know|Exodus XX|Additional tales|Germany Germany|India India|Germany Finland",
    "pejorative_term_in_raw": r"Kaffir|Hottentot|Gypsy|Eskimo",
    "historical_name": r"Malaya|Persia|Bohemia|Moravia|Transylvania|Czechoslovakia|Austria-Hungary|East Prussia|Bukovina|Zanzibar|Swabia|Flanders|Lusatia|Korea",
}

DISPLAY_OVERRIDE = {
    "Kaffir (South Africa)": "South Africa (raw string uses a historical slur for Xhosa/Nguni peoples; not reproduced in labels)",
    "South Africa (Hottentot)": "South Africa (Khoekhoe; raw string uses a historical pejorative)",
    "Eskimo": "Greenlandic Inuit (raw string uses the exonym 'Eskimo')",
    "Gypsy (Slovak, Moravian, and Bohemian)": "Romani (Slovak, Moravian and Bohemian; raw string uses 'Gypsy')",
    "Wales (Romani)": "Wales (Romani)",
}

# Source evidence for community/region decisions that rely on the record's bibliographic source
EVIDENCE = {
    "Eskimo": "Record sources: F. Nansen, Eskimo Life (Greenland); H. Rink, Tales and Traditions of the Eskimo (Greenland).",
    "Basque": "Record source: W. Webster, Basque Legends: Collected Chiefly in the Labourd (1879) - Labourd is in France.",
    "Basque, Wentworth Webster": "Record source: W. Webster, Basque Legends: Collected Chiefly in the Labourd (1879) - Labourd is in France.",
    "Georgia": "Record sources: M. Wardrop, Georgian Folk Tales (1894) - the country Georgia, not the US state.",
    "English": "Record source: F. H. Groome, Gypsy Folk-Tales (1899) - an English Romani tale.",
    "Thompson (Ntlakyapamuk)": "Record source: F. Boas, Folk-Tales of Salishan and Sahaptin Tribes (1917).",
}


# Final per-string corrections found during the row-by-row review of the draft.
FORCE = {
    "A Voyage to New South Wales (1795)": dict(
        normalised_label="A Voyage to New South Wales (1795)", entity_kind="collection", place_label="",
        place_kind="", place_detail="", author_or_collection="A Voyage to New South Wales (1795)",
        country_code_if_applicable="", broad_region="", latitude="", longitude="", coordinate_meaning="",
        confidence="none", evidence_url_or_source="",
        rationale="Book title (a travel account cited for a Flying Dutchman legend); 'New South Wales' is not Wales. No place recorded."),
    "Marie de France": dict(
        normalised_label="Marie de France", entity_kind="author", place_label="", place_kind="", place_detail="",
        author_or_collection="Marie de France", country_code_if_applicable="", broad_region="", latitude="",
        longitude="", coordinate_meaning="", confidence="none", evidence_url_or_source="",
        rationale="Name of a 12th-century poet (who wrote in England); 'France' is part of the name, not a recorded place."),
    "Kaffir (South Africa)": dict(place_detail=""),
    "South Africa (Hottentot)": dict(place_detail="Khoekhoe"),
    "Alsace (Germany / France)": dict(
        normalised_label="France (Alsace)", place_detail="Alsace",
        rationale="Alsace lies in modern France; the string records its historical German/French alternation. Located at country resolution."),
    "United States of America": dict(place_detail="", confidence="high"),
    "Children's Story, USA": dict(place_detail="", rationale="String names the USA; 'Children's Story' is a genre note."),
}


def load_points():
    pts, sub = {}, {}
    g = json.load(open(RAW / "geo" / "ne_50m_admin_0_countries.geojson", encoding="utf-8"))
    for f in g["features"]:
        p = f["properties"]
        iso = p["ISO_A2_EH"]
        if iso and iso != "-99" and iso not in pts:
            pts[iso] = (round(p["LABEL_Y"], 4), round(p["LABEL_X"], 4),
                        MERGE_SUBREGION.get(p["SUBREGION"], p["SUBREGION"]), p["ADMIN"])
    s = json.load(open(RAW / "geo" / "ne_50m_admin_0_map_subunits.geojson", encoding="utf-8"))
    for f in s["features"]:
        p = f["properties"]
        sub[p["SU_A3"]] = (round(p["LABEL_Y"], 4), round(p["LABEL_X"], 4),
                           MERGE_SUBREGION.get(p["SUBREGION"], p["SUBREGION"]), p["SUBUNIT"])
    return pts, sub


def _display_label(s, label, detail, mixed):
    if mixed:
        rest = re.sub(r"^" + re.escape(label) + r",?\s*", "", s)
        return f"{label} — {rest}" if rest != s else s
    if detail:
        return f"{label} ({detail})"
    return label


def place_region(key, pts, sub):
    label, kind, iso, coord, region = PLACES[key]
    if region:
        return region
    src, code = coord
    return (pts if src == "ne" else sub)[code][2]


def build():
    df = pd.read_csv(RAW / "trilogy" / "aft.csv", dtype=str, keep_default_na=False, na_values=[], encoding="utf-8")
    counts = Counter(df["provenance"])
    pts, sub = load_points()
    rows = []
    for raw, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        s = raw.strip()
        flags = [name for name, pat in FLAG_PATTERNS.items() if re.search(pat, s)]
        found = []
        for pat, key, _ in ALIASES:
            if re.search(pat, s) and key not in found:
                found.append(key)
        # "German" inside "German-American"/"German Language" etc. handled by alias order:
        if "German American" in found and "Germany" in found:
            found.remove("Germany")
        if "Irish American" in found and "Ireland" in found:
            found.remove("Ireland")
        if s.startswith("Alsace"):
            found = ["France"]
        if s.startswith("Upper Lusatia"):
            found = ["Germany", "Poland"]
        if s in ("Wales (Romani)",):
            found = ["Wales"]
        if s in UNKNOWN_NOTES and UNKNOWN_NOTES[s] is not None:
            found = []
        author = re.search(AUTHOR_PATTERNS, s) is not None
        collection = re.search(COLLECTION_PATTERNS, s) is not None
        row = dict(raw_provenance=raw, n_records=n, normalised_label="", entity_kind="unknown",
                   place_label="", place_kind="", place_detail="", author_or_collection="",
                   country_code_if_applicable="", broad_region="", latitude="", longitude="",
                   coordinate_meaning="", confidence="none", evidence_url_or_source="", rationale="",
                   flags=";".join(flags), review_status="agent-drafted 2026-10-29; human review pending")
        if raw == "NA":
            row.update(normalised_label="(missing)", rationale="Provenance missing in source (literal NA).")
        elif s in REGION_ONLY:
            region, kind, why = REGION_ONLY[s]
            row.update(normalised_label=s, entity_kind=kind, broad_region=region, confidence="medium",
                       evidence_url_or_source=M49_URL, rationale=why + " No place-level label; broad region only.")
        elif len(found) == 1:
            key = found[0]
            label, kind, iso, coord, _ = PLACES[key]
            region = place_region(key, pts, sub)
            mixed = (author or collection) and kind in ("country", "constituent nation")
            ekind = "mixed" if mixed else ("country" if kind in ("country", "constituent nation") else kind)
            detail = ""
            m = re.search(r"\(([^)]*)\)", s)
            if kind in ("country", "constituent nation") and m and not re.search(AUTHOR_PATTERNS + "|" + COLLECTION_PATTERNS, m.group(1)):
                detail = m.group(1)
            if s != label and not detail and kind in ("country", "constituent nation") and not mixed:
                detail = s
            high = (s == label) or (s in ("United States of America", "Germany Germany", "India India", "Czech Republic"))
            conf = "high" if high else "medium"
            if "contaminated_string" in flags and not high:
                conf = "medium"
            if kind == "community":
                conf = "medium"
            lat = lon = ""
            meaning = ""
            if coord:
                src, code = coord
                lat, lon = (pts if src == "ne" else sub)[code][:2]
                meaning = NE_MEANING if kind != "community" else (
                    "Natural Earth label point of the country/territory where the community's tales were recorded "
                    "(approximate; the community label is preserved)")
            why = {
                "country": "String names a modern country.",
                "constituent nation": "String names a constituent nation of the United Kingdom; kept distinct from the UK.",
                "region": "Region that does not correspond to one modern country; label kept, no coordinates.",
                "community": "Community label preserved (not replaced by a nation state).",
            }[kind]
            if detail and kind != "community":
                why += f" Sub-national or historical detail '{detail}' preserved; located at country resolution."
            if mixed:
                why += " Place named explicitly alongside an author/collection; the place is the recorded association."
            if kind == "community" and not coord:
                why += " No coordinates: no single documented location is recorded."
            row.update(normalised_label=DISPLAY_OVERRIDE.get(s, _display_label(s, label, detail, mixed)),
                       entity_kind=ekind, place_label=label, place_kind=kind, place_detail=detail,
                       author_or_collection=re.sub(r"^.*?,\s*", "", s) if mixed else "",
                       country_code_if_applicable=iso or "", broad_region=region,
                       latitude=lat, longitude=lon, coordinate_meaning=meaning, confidence=conf,
                       evidence_url_or_source=EVIDENCE.get(s, f"{NE_SOURCE}; {M49_URL}" if coord else M49_URL),
                       rationale=why)
        elif len(found) > 1:
            regions = {place_region(k, pts, sub) for k in found}
            region = regions.pop() if len(regions) == 1 else ""
            row.update(normalised_label=" / ".join(PLACES[k][0] for k in found), entity_kind="mixed",
                       broad_region=region, confidence="medium" if region else "none",
                       evidence_url_or_source=M49_URL,
                       rationale=("Several places named; no single place label. " +
                                  (f"All lie in UN M49 {region}." if region else "They span different UN sub-regions, so no broad region.")))
            flags.append("cross_border_or_multi_place")
            row["flags"] = ";".join(flags)
        elif collection or author:
            row.update(normalised_label=s, entity_kind="collection" if collection and not author else "author",
                       author_or_collection=s,
                       rationale="Author or literary collection only: no place recorded. Author/collection "
                                 "identity is not used as a story-origin location.")
        else:
            row.update(normalised_label=s, rationale=UNKNOWN_NOTES.get(s) or "No recognisable place, community, author or collection.")
        if raw in FORCE:
            row.update(FORCE[raw])
        rows.append(row)
    return rows


def main(write=True):
    rows = build()
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = main(write="--dry" not in sys.argv)
    print(f"{len(rows)} provenance strings mapped")
