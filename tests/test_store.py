import json, sys
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")
import store


def test_append_and_load(tmp_path):
    p = tmp_path / "x.json"
    assert store.append_point(p, {"date": "2026-07-25", "usd": 78.5}, ["date", "usd"]) is True
    assert store.load(p)["points"] == [{"date": "2026-07-25", "usd": 78.5}]


def test_dedupe_by_date(tmp_path):
    p = tmp_path / "x.json"
    store.append_point(p, {"date": "2026-07-25", "usd": 78.5}, ["date"])
    assert store.append_point(p, {"date": "2026-07-25", "usd": 99.0}, ["date"]) is False
    assert len(store.load(p)["points"]) == 1


def test_dedupe_respects_segment(tmp_path):
    p = tmp_path / "x.json"
    store.append_point(p, {"date": "2026-07-25", "segment": "flat", "v": 1}, ["date"])
    assert store.append_point(p, {"date": "2026-07-25", "segment": "house", "v": 2}, ["date"]) is True


def test_missing_required_key_raises(tmp_path):
    with pytest.raises(ValueError):
        store.append_point(tmp_path / "x.json", {"date": "2026-07-25"}, ["date", "usd"])


def test_malformed_never_written(tmp_path):
    p = tmp_path / "x.json"
    store.append_point(p, {"date": "2026-07-25", "usd": 1.0}, ["date", "usd"])
    before = p.read_text()
    with pytest.raises(ValueError):
        store.append_point(p, {"date": "2026-07-26", "usd": None}, ["date", "usd"])
    assert p.read_text() == before
