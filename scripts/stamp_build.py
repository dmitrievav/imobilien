"""Stamp a fresh build id into site HTML/version.js and write site/data/version.json.

Run after any deploy so browsers holding a cached copy of the site self-heal
(see site/assets/version.js) and versioned assets (?v=<build>) bust their cache.
Safe to run twice in a row with the same build id (idempotent).
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

SITE_DIR = Path("site")

# Matches an *existing* assets/<name>?v=<anything> query and replaces the
# value. Deliberately does NOT match a bare href/src with no ?v= at all —
# that would insert a query the page markup doesn't already declare, which
# should be an explicit authoring choice, not something this script does.
ASSET_RE = re.compile(
    r'(assets/(?:style\.css|gate\.js|chart\.umd\.js|version\.js)\?v=)[^"\']*'
)
# The single embedded build id, declared in site/assets/version.js.
BUILD_CONST_RE = re.compile(r'const BUILD = "[^"]*";')


def compute_build_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y%m%d%H%M")


def _rewrite_text(text: str, build_id: str) -> str:
    text = ASSET_RE.sub(lambda m: f"{m.group(1)}{build_id}", text)
    text = BUILD_CONST_RE.sub(f'const BUILD = "{build_id}";', text)
    return text


def rewrite_versions(site_dir: Path, build_id: str) -> None:
    """Rewrite ?v= asset queries and the BUILD constant, and write data/version.json.

    Only touches files whose content actually changes, and only touches the
    known asset-reference / BUILD-constant patterns — anything else in a file
    is left byte-for-byte untouched.
    """
    for path in sorted(site_dir.glob("*.html")):
        original = path.read_text(encoding="utf-8")
        updated = _rewrite_text(original, build_id)
        if updated != original:
            path.write_text(updated, encoding="utf-8")

    version_js = site_dir / "assets" / "version.js"
    if version_js.exists():
        original = version_js.read_text(encoding="utf-8")
        updated = _rewrite_text(original, build_id)
        if updated != original:
            version_js.write_text(updated, encoding="utf-8")

    data_dir = site_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "version.json").write_text(
        json.dumps({"build": build_id}) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_id = compute_build_id()
    rewrite_versions(SITE_DIR, build_id)
    print(f"stamped build {build_id}")
