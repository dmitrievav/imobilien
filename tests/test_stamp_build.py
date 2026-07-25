import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "scripts")
import stamp_build


def make_site(tmp_path):
    site = tmp_path / "site"
    (site / "assets").mkdir(parents=True)
    (site / "index.html").write_text(
        '<link rel="stylesheet" href="assets/style.css?v=old">\n'
        '<script src="assets/gate.js?v=old"></script>\n',
        encoding="utf-8")
    (site / "checklist.html").write_text(
        '<link rel="stylesheet" href="assets/style.css">\n'
        '<p>Плоский текст без версий.</p>\n',
        encoding="utf-8")
    (site / "assets" / "version.js").write_text(
        'const BUILD = "old";\nwindow.BUILD = BUILD;\n', encoding="utf-8")
    return site


def test_compute_build_id_uses_utc_minute_precision():
    now = datetime(2026, 7, 25, 20, 30, 5, tzinfo=timezone.utc)
    assert stamp_build.compute_build_id(now) == "202607252030"


def test_writes_version_json(tmp_path):
    site = make_site(tmp_path)
    stamp_build.rewrite_versions(site, "202601010000")
    saved = json.loads((site / "data" / "version.json").read_text())
    assert saved == {"build": "202601010000"}


def test_rewrites_existing_v_query(tmp_path):
    site = make_site(tmp_path)
    stamp_build.rewrite_versions(site, "202601010000")
    html = (site / "index.html").read_text()
    assert 'assets/style.css?v=202601010000' in html
    assert 'assets/gate.js?v=202601010000' in html
    assert "?v=old" not in html


def test_rewrites_build_constant(tmp_path):
    site = make_site(tmp_path)
    stamp_build.rewrite_versions(site, "202601010000")
    js = (site / "assets" / "version.js").read_text()
    assert 'const BUILD = "202601010000";' in js
    assert "old" not in js


def test_running_twice_is_idempotent(tmp_path):
    site = make_site(tmp_path)
    stamp_build.rewrite_versions(site, "202601010000")
    first_html = (site / "index.html").read_text()
    first_js = (site / "assets" / "version.js").read_text()
    first_version_json = (site / "data" / "version.json").read_text()

    stamp_build.rewrite_versions(site, "202601010000")
    assert (site / "index.html").read_text() == first_html
    assert (site / "assets" / "version.js").read_text() == first_js
    assert (site / "data" / "version.json").read_text() == first_version_json


def test_file_with_no_v_query_is_left_untouched(tmp_path):
    site = make_site(tmp_path)
    original = (site / "checklist.html").read_text()
    stamp_build.rewrite_versions(site, "202601010000")
    updated = (site / "checklist.html").read_text()
    # No assets/style.css?v= pattern present initially (no query at all) —
    # the bare href without ?v= is not touched, everything else is untouched too.
    assert updated == original
