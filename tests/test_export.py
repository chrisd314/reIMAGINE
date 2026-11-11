"""A public build must never ship full texts, and excerpts must keep passage offsets valid."""
import json
from pathlib import Path

import pytest

from analysis.export import EXCERPT_WORDS, excerpt_of, public_build

WEB = Path(__file__).resolve().parent.parent / "web/public/data"


def test_excerpt_is_a_verbatim_prefix():
    text = "Once  upon a time,\nthere was a king. " * 40
    out = excerpt_of(text, 10)
    assert text.startswith(out) and len(out) < len(text)
    assert len(out.split()) == 10
    assert not out[-1].isspace()


def test_short_text_is_returned_whole():
    text = "A fox saw some grapes.\n"
    assert excerpt_of(text, 10) == text


@pytest.mark.parametrize("value,expected", [("1", True), ("true", True), ("", False), ("0", False)])
def test_public_build_flag(monkeypatch, value, expected):
    monkeypatch.setenv("OUAW_PUBLIC_BUILD", value)
    assert public_build() is expected


def test_public_export_contains_no_full_texts():
    manifest = WEB / "manifest.json"
    if not manifest.exists() or not json.loads(manifest.read_text(encoding="utf-8")).get("public_build"):
        pytest.skip("no public export present (run the export with OUAW_PUBLIC_BUILD=1)")
    assert json.loads(manifest.read_text(encoding="utf-8"))["full_texts_included"] is False
    tales = sorted((WEB / "tales").glob("*.json"))
    assert tales
    for p in tales:
        t = json.loads(p.read_text(encoding="utf-8"))
        assert len(t["text"].split()) <= EXCERPT_WORDS, p.name
        if t["text_is_excerpt"]:
            assert len(t["text"].split()) == EXCERPT_WORDS, p.name
        assert len(t["passages"]) <= 1, p.name
        for c, passage in t["passages"].items():
            s, e, _ = t["chunks"][int(c)]
            assert len(passage) == e - s, p.name
