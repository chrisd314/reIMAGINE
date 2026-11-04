"""Record the agent's review of the 30 sampled crosswalk links (Pilot A) next to their evidence.

Decision rules (fixed before reviewing):
  identity  validated  - same people: equal name or a documented ethnonym/alias, or the target is a named subgroup of
                         the Berezkin people (scope flagged), with compatible location and language family
            unresolved - the Berezkin unit pools several peoples, or identity is plausible but not shown
            rejected   - different people, different language family, or a proxy assignment between neighbours
  time      compatible - the target's focal year/period lies no more than 50 years before the tradition's first
                         source publication (M&X year_firstpub) and the Berezkin unit is not tied to another period
            incompatible / unclear otherwise
  final     validated only if identity is validated and time is compatible
All decisions are the coding agent's reading of the evidence columns; none has been checked by a person.
"""
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
D = {
    "A01": ("unresolved", "pooled", "compatible", "Berezkin unit pools Bribri and Cabecar; SCCS codes the Bribri only (58 km, both Chibchan). Religion of the Cabecar part not coded."),
    "A02": ("unresolved", "pooled", "compatible", "Berezkin unit pools Oromo, Konso and Sidamo, peoples with different religious histories; SCCS codes only the Konso (1935)."),
    "A03": ("validated", "same", "compatible", "Huichol = Wixarika (listed alternative name); 76 km apart; both Uto-Aztecan; focal year 1890 vs first source 1900."),
    "A04": ("validated", "subgroup", "compatible", "SCCS Zazzagawa (Zaria) Hausa is a subgroup of the Berezkin Hausa unit; 175 km; Chadic/Afro-Asiatic. Berezkin Hausa sources may include non-Muslim Hausa (scope caveat)."),
    "A05": ("validated", "same", "compatible", "Same ethnonym, 114 km, Semitic/Afro-Asiatic; focal 1953 within the 1889-2019 source window. SCCS code says Christian without branch."),
    "A06": ("validated", "same", "compatible", "Khalkha/Khalka spelling variant of the same Mongol people; 835 km between centroids reflects Mongolia's extent; Mongolic. Religious change (1930s suppression) falls inside the source window."),
    "A07": ("rejected", "different", "compatible", "Rwala are a Bedouin tribe of the Syrian desert; the Berezkin unit is settled Levantine Arabs of Palestine, Syria and Lebanon, including Christian communities. Proxy assignment, not identity."),
    "A08": ("validated", "subgroup", "compatible", "SCCS Dolbahanta is a northern Somali clan, subgroup of the Berezkin Somali unit; 573 km within Somali territory. Note the code is 'superficial Islamization', from a mourning-practice coding project."),
    "A09": ("unresolved", "pooled", "compatible", "Berezkin pools Gilbert Islands, Nauru and Banaba (Nauruan is a distinct people and language); SCCS Makin is one Gilbertese atoll, 746 km away. EA route only."),
    "A10": ("unresolved", "pooled", "compatible", "Berezkin pools Slavey and Dogrib; SCCS Dene Tha are Southern Slavey. Related Athabaskan neighbours, but Dogrib not covered by the code."),
    "A11": ("validated", "same", "compatible", "Same ethnonym, Tungusic; 513 km within Manchuria; focal 1915 vs first source 1903. 'Mahayana Buddhism' simplifies Manchu shamanic-Buddhist practice."),
    "A12": ("validated", "same", "compatible", "Same name, 65 km, Algic; focal 1930 within the 1911- source window."),
    "A13": ("validated", "same", "unclear", "SCCS Chinese is a Jiangsu village (31.0N 120.1E, 1936), inside the Berezkin 'Jiangsu and Zhejiang Chinese' unit; but that unit exists only in the 2019 Michalopoulos-Xue snapshot: no coordinates or source years in the coordinate snapshot. Chinese popular religion is syncretic."),
    "A14": ("rejected", "different-period", "incompatible", "Berezkin unit is explicitly 'Japan AD 700-1700' (classical and medieval texts); SCCS Japanese is an Okayama village in 1950. Same people, different period: the religion code does not date this folklore."),
    "A15": ("validated", "same", "compatible", "Same name, 8 km, Abkhaz-Adyge; focal 1880 vs first source 1892. Coded 'indigenous religion' although Abkhaz communities were also Christian and Muslim: the code simplifies a mixed situation."),
    "A16": ("unresolved", "pooled", "unclear", "Berezkin pools Tiv, Jukun, Mbete, Wute and Ekoi; the unit is only in the 2019 snapshot (no coordinates). SCCS codes the Tiv only."),
    "A17": ("rejected", "different", "compatible", "Palaung (Myanmar/China) vs Lamet (Laos), different peoples 441 km apart; EA-only proxy assignment between neighbouring Austroasiatic groups."),
    "A18": ("validated", "same", "compatible", "Same name, 60 km, Macro-Ge; focal 1958, 13 years before the first source (1971)."),
    "A19": ("validated", "same", "compatible", "Guajiro = Wayuu (listed alternative 'Goajiro'); 29 km; Arawakan; focal 1947 vs first source 1942."),
    "A20": ("validated", "same", "compatible", "Same name, 19 km, Salishan; focal 1860, 35 years before the first source (1895)."),
    "A21": ("validated", "same", "unclear", "Berezkin 'Japan' vs SCCS Japanese (Okayama, 1950), 127 km; found only by proximity because 'Japan' is a country name. The unit's source years are unknown in the matched snapshot, and may include ancient texts. Religion code ignores Shinto."),
    "A22": ("rejected", "different", "compatible", "Wintu and Eastern Pomo are different peoples and language families (Wintuan vs Pomoan); proximity only."),
    "A23": ("rejected", "different", "compatible", "Berezkin regional unit 'Torricelli Papuans' vs Kwoma, a Sepik-family people; proximity only."),
    "A24": ("validated", "same", "incompatible", "Same name, 31 km, Austronesian. Pulotu codes the pre-Christian state at 1843; the first folklore source is 1932, after a world religion became predominant (code 68=3). Usable only with the post-contact variables."),
    "A25": ("unresolved", "pooled", "incompatible", "Berezkin pools Wallis (Uvea) and Futuna; only 8 motifs. Pulotu Futuna time focus 1837 vs first source 1914."),
    "A26": ("validated", "same", "compatible", "Yami = Tao (listed ethnonym), 0 km; Pulotu time focus 1950 vs first source 1967. Only 14 motifs."),
    "A27": ("unresolved", "pooled", "compatible", "Berezkin pools Murut, Dusun, Tombonuvo and Bajau (Bajau are largely Muslim, the others not); Pulotu codes the Dusun only."),
    "A28": ("unresolved", "subgroup", "incompatible", "DRH entry describes the Naknenuk subgroup of the 'Botocudo' label, which itself covers unrelated societies; entry period 1869-1894 ends 52 years before the first folklore source (1946)."),
    "A29": ("validated", "same", "compatible", "Same people; DRH period 1930-1960 lies inside the source window. DRH tags Ethiopian Orthodox (branch level), the only branch label in this sample."),
    "A30": ("validated", "same", "compatible", "Same people; DRH period 1700-2000 covers the source window (1896-). DRH tags Shoshoni (indigenous) religions, not an affiliation with a world religion."),
}
ev = pd.read_csv("crosswalk/review_sample_evidence.csv")
dec = pd.DataFrame([dict(review_id=k, identity_status=v[0], scope=v[1], time_status=v[2], rationale=v[3]) for k, v in D.items()])
out = ev.merge(dec, on="review_id", how="left")
assert out.identity_status.notna().all() and len(out) == 30
out["final_status"] = out.apply(lambda r: "validated" if r.identity_status == "validated" and r.time_status == "compatible"
                                else ("rejected" if r.identity_status == "rejected" or r.time_status == "incompatible" else "unresolved"), axis=1)
out["reviewer"] = "coding agent (Claude), 2026-11-04; human check pending"
cols = ["review_id", "stratum", "stratum_size", "target", "berezkin_name", "idn", "oid", "target_id", "target_name", "target_alt", "routes", "evidence",
        "distance_km", "b_family", "b_branch", "t_family", "t_region", "t_focal_year", "year_firstpub", "year_avgpub", "n_motifs",
        "nmbr_title", "religion_code", "identity_status", "scope", "time_status", "final_status", "rationale", "reviewer"]
out[cols].to_csv("crosswalk/crosswalk_reviewed.csv", index=False)
print(out.groupby("stratum").final_status.value_counts().unstack(fill_value=0).to_string())
print("\nidentity:", out.identity_status.value_counts().to_dict(), "| time:", out.time_status.value_counts().to_dict(), "| final:", out.final_status.value_counts().to_dict())
print("scope among unresolved/rejected:", out[out.final_status != "validated"].scope.value_counts().to_dict())
