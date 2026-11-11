"""A transparent rule for "does this passage tell a story?".

Two sources mix stories with sayings and commentary under one heading: Rapaport's Midrash
anthology and Legge's Zhuangzi. A passage counts as a story when it has enough past-tense
action, some speech or a story opener, and little exegesis. The rule never looks at folktales,
so the selection cannot favour passages that resemble them. It is deliberately simple;
labeling/segmentation_check.csv is there to check it by hand.
"""
from __future__ import annotations

import re

ACTION = re.compile(
    r"\b(?:said|replied|answered|asked|went|came|took|gave|saw|found|told|brought|sent|returned|cried|met|called|heard|"
    r"ran|fell|died|killed|married|arrived|departed|entered|seized|ordered|begged|exclaimed|rejoined|inquired|"
    r"demanded|led|carried|rose|sat|walked|fled|opened|threw|caught|bought|sold|paid|ate|drank|slept|awoke|"
    r"laughed|wept|looked|turned|left|reached|began|put|made|appeared|happened|visited|invited|dreamt|dreamed)\b", re.I)
OPENER = re.compile(r"\b(?:once|one day|a certain|there (?:was|lived|were)|on (?:one|a certain) occasion|it happened|"
                    r"formerly|in the time of|when he (?:was|came|had)|a man (?:of|who|was|had)|a king)\b", re.I)
SPEECH = re.compile(r"\b(?:said|replied|answered|asked|exclaimed|rejoined|inquired|demanded|told|spoke)\b", re.I)
COMPARISON = re.compile(r"\b(?:it is as though|is like unto|may be (?:compared|likened)|like (?:unto )?a king|parable|"
                        r"as if a (?:king|man|prince))\b", re.I)
SCRIPTURE = re.compile(r"\((?:[1-3] )?[A-Z][a-z]+\.? ?\d+[.,]? ?\d*\.?\)")          # (Deut. 4. 32)
EXEGESIS = re.compile(r"\b(?:verses?|words?|passages?|expressions?|interpret\w*|refers?|referring|means|meaning|signif\w+|"
                      r"allu\w+|mentioned|Psalms?|Scriptures?|written|texts?|letters?|phrases?|terms?|explained|"
                      r"explanation|points? to|teaches|deduc\w+|inferr?\w*)\b", re.I)
ENUMERATION = re.compile(r"\(\d\)")


def features(text: str) -> dict:
    n = max(len(text.split()), 1)
    return dict(tokens=n, action=100.0 * len(ACTION.findall(text)) / n, openers=len(OPENER.findall(text)),
                speech=len(SPEECH.findall(text)), comparison=bool(COMPARISON.search(text)),
                exegesis=100.0 * (len(SCRIPTURE.findall(text)) + len(EXEGESIS.findall(text))) / n,
                enumeration=len(ENUMERATION.findall(text)))


def is_story(text: str, min_tokens: int, min_action: float = 2.5, max_exegesis: float = 2.0) -> bool:
    f = features(text)
    return (f["tokens"] >= min_tokens and f["action"] >= min_action
            and (f["openers"] >= 1 or f["speech"] >= 2 or f["comparison"])
            and f["exegesis"] <= max_exegesis and f["enumeration"] < 2)


def is_saying(text: str, max_tokens: int = 60) -> bool:
    """A short passage without action, speech or story opener (a maxim)."""
    f = features(text)
    return f["tokens"] <= max_tokens and f["action"] < 1.5 and f["speech"] == 0 and f["openers"] == 0
