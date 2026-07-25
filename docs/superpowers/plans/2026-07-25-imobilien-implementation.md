# Imobilien Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the data pipeline, scenario model, fair-price engine, and gated static site defined in `docs/superpowers/specs/2026-07-25-imobilien-design.md`, and publish it to GitHub Pages.

**Architecture:** Python scripts append dated points to `data/*.json`, a scenario model and fair-price engine write outputs to `site/data/`, and a plain HTML+Chart.js site (magic-URL gated, listings encrypted) is deployed by GitHub Actions to Pages. No backend, no site build step.

**Tech Stack:** Python 3.11+, `requests`, `cryptography`, `Pillow`, `pytest`; vanilla JS + WebCrypto + vendored Chart.js 4.

> **SUPERSEDED — gate verifier.** This plan is kept as a historical record of
> what was executed. The gate scheme it specifies (tasks 2 and 12) published a
> plain unsalted `digest = SHA256(passphrase)` in `gate.json` and compared it in
> `gate.js` via `sha256b64` — one hash per brute-force guess, which made the
> published value roughly 600000× cheaper to attack than the PBKDF2 cost the
> design claimed. It was replaced before the first public push by a salted,
> PBKDF2-based `verifier` field (`SHA256(PBKDF2(passphrase, salt, iterations))`,
> derived bits reused as the AES-GCM key). Do not copy the `digest_b64` /
> `sha256b64` snippets below. The authoritative description is section 8 of
> `docs/superpowers/specs/2026-07-25-imobilien-design.md`; the implementation is
> `scripts/crypto_util.py` (`verifier_b64`) and `site/assets/gate.js`.

## Global Constraints

- Crypto (MUST match Python↔JS, guarded by golden-vector test): PBKDF2-HMAC-SHA256, 600000 iterations, 32-byte key; AES-GCM; encrypted blob layout = `12-byte IV || ciphertext+tag`; digests/salts stored base64.
- Passphrase env var: `IMOBILIEN_KEY`, read from gitignored `.env` (format: `IMOBILIEN_KEY=<phrase>`).
- Data files are append-only history `{"points": [...]}`; writes are atomic (temp file + `os.replace`); one point per date (per date+segment for realty).
- Privacy (repo is public): plaintext `data/listings.json` and `data/photos/` are gitignored; no family names/full addresses/cadastral numbers anywhere; git author = personal identity.
- Site copy is Russian, base font ≥ 20px; code/comments/docs English.
- Model levels: capitals 10 / 17.5 / 25 mln RUB; horizon 10 years; paths `pess/base/opt`; all outputs in real (inflation-adjusted) RUB.
- Local site testing: `python3 -m http.server -d site` (WebCrypto needs a secure context — `localhost` qualifies, `file://` does not).
- Run all commands from the repo root; `pytest` discovers `tests/`.

---

### Task 1: Scaffolding, Pages workflow, vendored Chart.js

**Files:**
- Create: `requirements.txt`, `.github/workflows/pages.yml`, `pytest.ini`, `site/assets/chart.umd.js` (vendored), `data/.gitkeep`, `site/data/.gitkeep`, `notes/.gitkeep`
- Test: none (infrastructure; verified by `pytest` running and later by the Pages deploy in Task 16)

**Interfaces:**
- Produces: directory layout and CI used by every later task.

- [ ] **Step 1: Create files**

```text
# requirements.txt
requests
cryptography
Pillow
pytest
```

```ini
# pytest.ini
[pytest]
testpaths = tests
```

```yaml
# .github/workflows/pages.yml
name: pages
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
concurrency:
  group: pages
  cancel-in-progress: true
jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: site
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Vendor Chart.js and create dirs**

```bash
mkdir -p data site/data site/assets notes tests scripts
touch data/.gitkeep site/data/.gitkeep notes/.gitkeep
curl -fsSL https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.js -o site/assets/chart.umd.js
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo ".venv/" >> .gitignore
```

- [ ] **Step 3: Verify pytest runs (0 tests, exit 0 with `--collect-only` clean)**

Run: `.venv/bin/pytest --collect-only`
Expected: "no tests ran" / collected 0 items, no errors.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "chore: scaffolding, Pages workflow, vendored Chart.js"
```

---

### Task 2: crypto_util.py

**Files:**
- Create: `scripts/crypto_util.py`, `tests/test_crypto_util.py`, `tests/make_vector.py`, `tests/vectors/gate_vector.json` (generated)

**Interfaces:**
- Produces: `load_passphrase(env_path=".env") -> str`, `digest_b64(passphrase: str) -> str`, `derive_key(passphrase: str, salt: bytes, iterations: int = ITERATIONS) -> bytes`, `encrypt(data: bytes, passphrase: str, salt: bytes, iv: bytes | None = None) -> bytes`, `decrypt(blob: bytes, passphrase: str, salt: bytes) -> bytes`, constants `ITERATIONS = 600_000`, `IV_LEN = 12`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_crypto_util.py
import base64, json, sys
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")
import crypto_util


def test_roundtrip():
    salt = b"0123456789abcdef"
    blob = crypto_util.encrypt(b"secret data", "pass phrase", salt)
    assert crypto_util.decrypt(blob, "pass phrase", salt) == b"secret data"


def test_wrong_passphrase_fails():
    salt = b"0123456789abcdef"
    blob = crypto_util.encrypt(b"secret data", "pass phrase", salt)
    with pytest.raises(Exception):
        crypto_util.decrypt(blob, "wrong", salt)


def test_digest_is_sha256_b64():
    import hashlib
    exp = base64.b64encode(hashlib.sha256(b"abc").digest()).decode()
    assert crypto_util.digest_b64("abc") == exp


def test_load_passphrase_from_file(tmp_path):
    env = tmp_path / ".env"
    env.write_text("OTHER=1\nIMOBILIEN_KEY=my secret phrase\n")
    assert crypto_util.load_passphrase(env) == "my secret phrase"


def test_golden_vector():
    """Params (PBKDF2 600k, AES-GCM, iv||ct) must never drift — gate.js mirrors them."""
    vec = json.loads(Path("tests/vectors/gate_vector.json").read_text())
    blob = crypto_util.encrypt(
        vec["plaintext"].encode(), vec["passphrase"],
        base64.b64decode(vec["salt"]), iv=base64.b64decode(vec["iv"]))
    assert base64.b64encode(blob).decode() == vec["blob"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_crypto_util.py -v`
Expected: FAIL/ERROR with "No module named 'crypto_util'".

- [ ] **Step 3: Implement**

```python
# scripts/crypto_util.py
"""AES-GCM + PBKDF2 helpers. Parameters MUST stay in sync with site/assets/gate.js."""
import base64
import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITERATIONS = 600_000
IV_LEN = 12
KEY_LEN = 32


def load_passphrase(env_path=".env"):
    if os.environ.get("IMOBILIEN_KEY"):
        return os.environ["IMOBILIEN_KEY"]
    p = Path(env_path)
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith("IMOBILIEN_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("IMOBILIEN_KEY not set (env var or .env)")


def digest_b64(passphrase: str) -> str:
    return base64.b64encode(hashlib.sha256(passphrase.encode()).digest()).decode()


def derive_key(passphrase: str, salt: bytes, iterations: int = ITERATIONS) -> bytes:
    kdf = PBKDF2HMAC(hashes.SHA256(), KEY_LEN, salt, iterations)
    return kdf.derive(passphrase.encode())


def encrypt(data: bytes, passphrase: str, salt: bytes, iv: bytes | None = None) -> bytes:
    iv = iv if iv is not None else os.urandom(IV_LEN)
    ct = AESGCM(derive_key(passphrase, salt)).encrypt(iv, data, None)
    return iv + ct


def decrypt(blob: bytes, passphrase: str, salt: bytes) -> bytes:
    return AESGCM(derive_key(passphrase, salt)).decrypt(blob[:IV_LEN], blob[IV_LEN:], None)
```

- [ ] **Step 4: Generate the golden vector (one-time)**

```python
# tests/make_vector.py
"""Run once: freezes crypto params into tests/vectors/gate_vector.json. Commit the output."""
import base64, json, sys
from pathlib import Path

sys.path.insert(0, "scripts")
import crypto_util

passphrase, salt, iv, plaintext = "test-vector", b"0123456789abcdef", b"\x00" * 12, "imobilien"
blob = crypto_util.encrypt(plaintext.encode(), passphrase, salt, iv=iv)
out = {"passphrase": passphrase, "salt": base64.b64encode(salt).decode(),
       "iv": base64.b64encode(iv).decode(), "plaintext": plaintext,
       "blob": base64.b64encode(blob).decode(), "iterations": crypto_util.ITERATIONS}
Path("tests/vectors").mkdir(parents=True, exist_ok=True)
Path("tests/vectors/gate_vector.json").write_text(json.dumps(out, indent=1))
print("vector written")
```

Run: `.venv/bin/python tests/make_vector.py`

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_crypto_util.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add scripts/crypto_util.py tests/ && git commit -m "feat: crypto_util with golden-vector param guard"
```

---

### Task 3: gen_gate.py

**Files:**
- Create: `scripts/gen_gate.py`, `tests/test_gen_gate.py`

**Interfaces:**
- Consumes: `crypto_util.load_passphrase`, `crypto_util.digest_b64`, `crypto_util.ITERATIONS`.
- Produces: `write_gate(passphrase: str, gate_path: Path) -> dict` and CLI `python scripts/gen_gate.py`; output file `site/data/gate.json` = `{"digest": b64, "salt": b64, "iterations": int}`. The salt in `gate.json` is THE salt used for all encryption (journal, photos); `fairprice.py` and `add_listing.py` read it from here.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_gen_gate.py
import base64, json, sys
from pathlib import Path

sys.path.insert(0, "scripts")
import crypto_util
import gen_gate


def test_creates_gate(tmp_path):
    gate = gen_gate.write_gate("phrase", tmp_path / "gate.json")
    saved = json.loads((tmp_path / "gate.json").read_text())
    assert saved == gate
    assert saved["digest"] == crypto_util.digest_b64("phrase")
    assert saved["iterations"] == crypto_util.ITERATIONS
    assert len(base64.b64decode(saved["salt"])) == 16


def test_preserves_existing_salt(tmp_path):
    g1 = gen_gate.write_gate("phrase", tmp_path / "gate.json")
    g2 = gen_gate.write_gate("new phrase", tmp_path / "gate.json")
    assert g1["salt"] == g2["salt"]
    assert g1["digest"] != g2["digest"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_gen_gate.py -v` — Expected: import error.

- [ ] **Step 3: Implement**

```python
# scripts/gen_gate.py
"""Generate site/data/gate.json (digest + salt + iterations) from IMOBILIEN_KEY."""
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import crypto_util

GATE_PATH = Path("site/data/gate.json")


def write_gate(passphrase: str, gate_path: Path = GATE_PATH) -> dict:
    if gate_path.exists():
        salt_b64 = json.loads(gate_path.read_text())["salt"]
    else:
        salt_b64 = base64.b64encode(os.urandom(16)).decode()
    gate = {"digest": crypto_util.digest_b64(passphrase),
            "salt": salt_b64, "iterations": crypto_util.ITERATIONS}
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps(gate, indent=1))
    return gate


if __name__ == "__main__":
    write_gate(crypto_util.load_passphrase())
    print(f"wrote {GATE_PATH}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_gen_gate.py -v` — Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/gen_gate.py tests/test_gen_gate.py && git commit -m "feat: gate.json generator"
```

---

### Task 4: store.py (append-only history)

**Files:**
- Create: `scripts/store.py`, `tests/test_store.py`

**Interfaces:**
- Produces: `load(path) -> dict` (returns `{"points": []}` if missing), `atomic_write(path, obj) -> None`, `append_point(path, point: dict, required_keys: list[str]) -> bool` (False = duplicate date[+segment] skipped; raises `ValueError` on missing required keys). Every fetcher and fairprice benchmark write goes through this.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_store.py
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
```

- [ ] **Step 2: Run tests to verify they fail** — `.venv/bin/pytest tests/test_store.py -v`

- [ ] **Step 3: Implement**

```python
# scripts/store.py
"""Append-only dated history files with atomic writes."""
import json
import os
import tempfile
from pathlib import Path


def load(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else {"points": []}


def atomic_write(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def append_point(path, point, required_keys):
    missing = [k for k in required_keys if point.get(k) is None]
    if missing:
        raise ValueError(f"missing required keys: {missing}")
    data = load(path)
    dup = any(pt["date"] == point["date"] and pt.get("segment") == point.get("segment")
              for pt in data["points"])
    if dup:
        return False
    data["points"].append(point)
    atomic_write(path, data)
    return True
```

- [ ] **Step 4: Run tests to verify they pass** — `.venv/bin/pytest tests/test_store.py -v` — Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/store.py tests/test_store.py && git commit -m "feat: append-only history store"
```

---

### Task 5: fetch_cbr.py

**Files:**
- Create: `scripts/fetch_cbr.py`, `tests/test_fetch_cbr.py`

**Interfaces:**
- Consumes: `store.append_point`.
- Produces: `fetch_fx() -> dict` (`{"usd": float, "eur": float}`), `fetch_gold() -> float | None` (RUB/gram), `fetch_key_rate() -> float | None` (percent), `main() -> bool` appending to `data/cbr.json` point `{"date", "usd", "eur", "gold_rub_g", "key_rate"}` (required: date/usd/eur; others may be None).

- [ ] **Step 1: Write the failing tests (mock HTTP)**

```python
# tests/test_fetch_cbr.py
import sys
from unittest import mock

sys.path.insert(0, "scripts")
import fetch_cbr

FX_XML = b"""<?xml version="1.0" encoding="UTF-8"?><ValCurs Date="25.07.2026">
<Valute ID="R01235"><CharCode>USD</CharCode><VunitRate>78,50</VunitRate></Valute>
<Valute ID="R01239"><CharCode>EUR</CharCode><VunitRate>91,20</VunitRate></Valute></ValCurs>"""

METALL_XML = b"""<?xml version="1.0" encoding="UTF-8"?><Metall>
<Record Date="24.07.2026" Code="1"><Buy>10100,5</Buy><Sell>10100,5</Sell></Record>
<Record Date="25.07.2026" Code="1"><Buy>10200,0</Buy><Sell>10200,0</Sell></Record>
<Record Date="25.07.2026" Code="2"><Buy>110,0</Buy><Sell>110,0</Sell></Record></Metall>"""

KEYRATE_HTML = b'<table><tr><td>25.07.2026</td><td>14,00</td></tr></table>'


def _resp(content):
    r = mock.Mock()
    r.content = content
    r.raise_for_status = mock.Mock()
    return r


def test_fetch_fx():
    with mock.patch("fetch_cbr.requests.get", return_value=_resp(FX_XML)):
        assert fetch_cbr.fetch_fx() == {"usd": 78.5, "eur": 91.2}


def test_fetch_gold_takes_last_code1():
    with mock.patch("fetch_cbr.requests.get", return_value=_resp(METALL_XML)):
        assert fetch_cbr.fetch_gold() == 10200.0


def test_fetch_key_rate():
    with mock.patch("fetch_cbr.requests.get", return_value=_resp(KEYRATE_HTML)):
        assert fetch_cbr.fetch_key_rate() == 14.0


def test_main_appends(tmp_path):
    with mock.patch("fetch_cbr.requests.get", return_value=_resp(FX_XML)), \
         mock.patch("fetch_cbr.fetch_gold", return_value=None), \
         mock.patch("fetch_cbr.fetch_key_rate", return_value=14.0), \
         mock.patch("fetch_cbr.DATA_PATH", tmp_path / "cbr.json"):
        assert fetch_cbr.main() is True
```

- [ ] **Step 2: Run tests to verify they fail** — `.venv/bin/pytest tests/test_fetch_cbr.py -v`

- [ ] **Step 3: Implement**

```python
# scripts/fetch_cbr.py
"""CBR: USD/EUR official rates, gold accounting price, key rate."""
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import store

DATA_PATH = Path("data/cbr.json")
TIMEOUT = 30


def _num(s):
    return float(s.replace(",", "."))


def fetch_fx():
    r = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=TIMEOUT)
    r.raise_for_status()
    out = {}
    for v in ET.fromstring(r.content).iter("Valute"):
        code = v.findtext("CharCode")
        if code in ("USD", "EUR"):
            out[code.lower()] = _num(v.findtext("VunitRate"))
    if set(out) != {"usd", "eur"}:
        raise ValueError(f"unexpected FX payload: {out}")
    return out


def fetch_gold():
    d2, d1 = date.today(), date.today() - timedelta(days=14)
    url = ("https://www.cbr.ru/scripts/xml_metall.asp"
           f"?date_req1={d1:%d/%m/%Y}&date_req2={d2:%d/%m/%Y}")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    gold = [rec for rec in ET.fromstring(r.content).iter("Record")
            if rec.get("Code") == "1"]
    return _num(gold[-1].findtext("Sell")) if gold else None


def fetch_key_rate():
    r = requests.get("https://www.cbr.ru/hd_base/KeyRate/", timeout=TIMEOUT)
    r.raise_for_status()
    m = re.search(r"<td>\d{2}\.\d{2}\.\d{4}</td>\s*<td>([\d,\.]+)</td>",
                  r.content.decode("utf-8", "ignore"))
    return _num(m.group(1)) if m else None


def main():
    fx = fetch_fx()
    point = {"date": date.today().isoformat(), **fx}
    try:
        point["gold_rub_g"] = fetch_gold()
    except Exception:
        point["gold_rub_g"] = None
    try:
        point["key_rate"] = fetch_key_rate()
    except Exception:
        point["key_rate"] = None
    return store.append_point(DATA_PATH, point, ["date", "usd", "eur"])


if __name__ == "__main__":
    print("cbr:", "appended" if main() else "already have today")
```

- [ ] **Step 4: Run tests to verify they pass** — Expected: 4 passed.

- [ ] **Step 5: Live smoke test** — `.venv/bin/python scripts/fetch_cbr.py` — Expected: "cbr: appended", `data/cbr.json` has one point with today's values. Commit the data file too.

- [ ] **Step 6: Commit**

```bash
git add scripts/fetch_cbr.py tests/test_fetch_cbr.py data/cbr.json && git commit -m "feat: CBR fetcher (fx, gold, key rate)"
```

---

### Task 6: fetch_moex.py

**Files:**
- Create: `scripts/fetch_moex.py`, `tests/test_fetch_moex.py`

**Interfaces:**
- Consumes: `store.append_point`.
- Produces: `last_price(secid, market="shares", board="TQTF") -> float`, `main() -> bool` appending to `data/moex.json` point `{"date", "tmos", "tpay", "rgbitr"}` (rgbitr may be None).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_fetch_moex.py
import sys
from unittest import mock

import pytest

sys.path.insert(0, "scripts")
import fetch_moex

PAYLOAD = {
    "securities": {"columns": ["SECID", "PREVPRICE"], "data": [["TMOS", 7.10]]},
    "marketdata": {"columns": ["SECID", "LAST", "MARKETPRICE"], "data": [["TMOS", 7.25, 7.20]]},
}
PAYLOAD_NO_LAST = {
    "securities": {"columns": ["SECID", "PREVPRICE"], "data": [["TMOS", 7.10]]},
    "marketdata": {"columns": ["SECID", "LAST", "MARKETPRICE"], "data": [["TMOS", None, None]]},
}


def _resp(payload):
    r = mock.Mock()
    r.json = mock.Mock(return_value=payload)
    r.raise_for_status = mock.Mock()
    return r


def test_last_price_prefers_last():
    with mock.patch("fetch_moex.requests.get", return_value=_resp(PAYLOAD)):
        assert fetch_moex.last_price("TMOS") == 7.25


def test_last_price_falls_back_to_prevprice():
    with mock.patch("fetch_moex.requests.get", return_value=_resp(PAYLOAD_NO_LAST)):
        assert fetch_moex.last_price("TMOS") == 7.10


def test_main_appends(tmp_path):
    with mock.patch("fetch_moex.last_price", side_effect=[7.25, 102.0, 620.0]), \
         mock.patch("fetch_moex.DATA_PATH", tmp_path / "moex.json"):
        assert fetch_moex.main() is True
```

- [ ] **Step 2: Run tests to verify they fail** — `.venv/bin/pytest tests/test_fetch_moex.py -v`

- [ ] **Step 3: Implement**

```python
# scripts/fetch_moex.py
"""MOEX ISS: TMOS, TPAY closes and RGBITR index."""
import sys
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import store

DATA_PATH = Path("data/moex.json")
TIMEOUT = 30
PRICE_FIELDS = ["LAST", "MARKETPRICE", "CURRENTVALUE", "LASTVALUE"]


def _cell(block, field):
    cols = block["columns"]
    return block["data"][0][cols.index(field)] if field in cols and block["data"] else None


def last_price(secid, market="shares", board="TQTF"):
    url = (f"https://iss.moex.com/iss/engines/stock/markets/{market}/boards/{board}"
           f"/securities/{secid}.json?iss.only=securities,marketdata&iss.meta=off")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    j = r.json()
    for f in PRICE_FIELDS:
        v = _cell(j["marketdata"], f)
        if v:
            return float(v)
    v = _cell(j["securities"], "PREVPRICE")
    if v:
        return float(v)
    raise ValueError(f"no price for {secid}")


def main():
    point = {"date": date.today().isoformat(),
             "tmos": last_price("TMOS"),
             "tpay": last_price("TPAY")}
    try:
        point["rgbitr"] = last_price("RGBITR", market="index", board="SNDX")
    except Exception:
        point["rgbitr"] = None
    return store.append_point(DATA_PATH, point, ["date", "tmos", "tpay"])


if __name__ == "__main__":
    print("moex:", "appended" if main() else "already have today")
```

- [ ] **Step 4: Run tests to verify they pass** — Expected: 3 passed.

- [ ] **Step 5: Live smoke test + commit**

```bash
.venv/bin/python scripts/fetch_moex.py
git add scripts/fetch_moex.py tests/test_fetch_moex.py data/moex.json && git commit -m "feat: MOEX fetcher (TMOS, TPAY, RGBITR)"
```

---

### Task 7: fetch_crypto.py

**Files:**
- Create: `scripts/fetch_crypto.py`, `tests/test_fetch_crypto.py`

**Interfaces:**
- Consumes: `store.append_point`.
- Produces: `main() -> bool` appending to `data/crypto.json` point `{"date", "btc_rub", "btc_usd"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fetch_crypto.py
import sys
from unittest import mock

sys.path.insert(0, "scripts")
import fetch_crypto


def test_main_appends(tmp_path):
    payload = {"bitcoin": {"rub": 9500000, "usd": 121000}}
    r = mock.Mock()
    r.json = mock.Mock(return_value=payload)
    r.raise_for_status = mock.Mock()
    with mock.patch("fetch_crypto.requests.get", return_value=r), \
         mock.patch("fetch_crypto.DATA_PATH", tmp_path / "crypto.json"):
        assert fetch_crypto.main() is True
```

- [ ] **Step 2: Run test to verify it fails** — `.venv/bin/pytest tests/test_fetch_crypto.py -v`

- [ ] **Step 3: Implement**

```python
# scripts/fetch_crypto.py
"""CoinGecko: BTC in RUB and USD."""
import sys
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import store

DATA_PATH = Path("data/crypto.json")
URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=rub,usd"


def main():
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    btc = r.json()["bitcoin"]
    point = {"date": date.today().isoformat(),
             "btc_rub": float(btc["rub"]), "btc_usd": float(btc["usd"])}
    return store.append_point(DATA_PATH, point, ["date", "btc_rub", "btc_usd"])


if __name__ == "__main__":
    print("crypto:", "appended" if main() else "already have today")
```

- [ ] **Step 4: Run test to verify it passes**, live smoke test, commit

```bash
.venv/bin/pytest tests/test_fetch_crypto.py -v
.venv/bin/python scripts/fetch_crypto.py
git add scripts/fetch_crypto.py tests/test_fetch_crypto.py data/crypto.json && git commit -m "feat: CoinGecko BTC fetcher"
```

---

### Task 8: assumptions + model.py

**Files:**
- Create: `data/assumptions.json` (committed — not secret), `scripts/model.py`, `tests/test_model.py`

**Interfaces:**
- Consumes: `store.atomic_write`.
- Produces: `run(assumptions: dict) -> dict` (pure), `main() -> None` writing `site/data/scenarios.json`. Output shape:
  `{"as_of", "capital_levels": [10000000, 17500000, 25000000], "horizon_years": 10, "scenarios": {name: {"<capital>": {"pess": [11 floats], "base": [...], "opt": [...]}}}, "verdict": {"light": "green|yellow|red", "reason_ru": str, "numbers": {...}}, "assumptions_echo": dict}`.
  Scenario names: `buy_now_house`, `buy_now_flat`, `deposit`, `ofz`, `tmos`, `tpay`, `gold`, `usd`, `btc`. All series are real (inflation-adjusted) RUB. Path label semantics: `pess` = bad for the saver (high inflation, low returns/growth).

- [ ] **Step 1: Create assumptions (initial values; refined in Task 16 and documented in notes/methodology.md)**

```json
{
  "as_of": "2026-07-25",
  "inflation": {"pess": 0.10, "base": 0.07, "opt": 0.05},
  "deposit": {"rate_start": 0.13, "rate_floor": 0.08, "decay_years": 3, "interest_tax": 0.13},
  "ofz_ytm": 0.13,
  "growth": {
    "house": {"pess": -0.03, "base": 0.04, "opt": 0.10},
    "flat": {"pess": -0.02, "base": 0.05, "opt": 0.10}
  },
  "returns": {
    "tmos": {"pess": -0.05, "base": 0.12, "opt": 0.20},
    "tpay": {"pess": 0.06, "base": 0.11, "opt": 0.15},
    "gold": {"pess": -0.02, "base": 0.06, "opt": 0.15},
    "usd": {"pess": 0.00, "base": 0.05, "opt": 0.12},
    "btc": {"pess": -0.40, "base": 0.15, "opt": 0.60}
  },
  "house_maintenance_rate": 0.015,
  "property_tax_rate": 0.001,
  "transaction_cost_rate": 0.03
}
```

Save as `data/assumptions.json`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_model.py
import json, sys
from pathlib import Path

sys.path.insert(0, "scripts")
import model

A = json.loads(Path("data/assumptions.json").read_text())


def test_shapes():
    out = model.run(A)
    assert out["capital_levels"] == [10_000_000, 17_500_000, 25_000_000]
    s = out["scenarios"]["deposit"]["17500000"]
    assert set(s) == {"pess", "base", "opt"} and all(len(v) == 11 for v in s.values())


def test_year_zero_costs():
    out = model.run(A)
    # buy_now starts capital minus transaction costs; deposit starts at full capital
    assert out["scenarios"]["buy_now_house"]["10000000"]["base"][0] == 10_000_000 * 0.97
    assert out["scenarios"]["deposit"]["10000000"]["base"][0] == 10_000_000


def test_real_adjustment():
    # zero growth, zero costs => real value must shrink by exactly inflation
    a = json.loads(json.dumps(A))
    a["growth"]["house"] = {"pess": 0.0, "base": 0.0, "opt": 0.0}
    a["house_maintenance_rate"] = a["property_tax_rate"] = a["transaction_cost_rate"] = 0.0
    out = model.run(a)
    v = out["scenarios"]["buy_now_house"]["10000000"]["base"]
    assert abs(v[1] - 10_000_000 / 1.07) < 1


def test_paths_ordered():
    out = model.run(A)
    for name, caps in out["scenarios"].items():
        for series in caps.values():
            assert series["pess"][5] <= series["base"][5] <= series["opt"][5], name


def test_verdict_present():
    out = model.run(A)
    assert out["verdict"]["light"] in ("green", "yellow", "red")
    assert out["verdict"]["reason_ru"]
```

- [ ] **Step 3: Run tests to verify they fail** — `.venv/bin/pytest tests/test_model.py -v`

- [ ] **Step 4: Implement**

```python
# scripts/model.py
"""Capital scenarios in real RUB. Pure math in run(); IO in main()."""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import store

CAPITALS = [10_000_000, 17_500_000, 25_000_000]
HORIZON = 10
PATHS = ["pess", "base", "opt"]
OUT_PATH = Path("site/data/scenarios.json")
ASSUMPTIONS_PATH = Path("data/assumptions.json")


def _real(nominal, infl):
    return [v / (1 + infl) ** t for t, v in enumerate(nominal)]


def _buy_now(c, growth, infl, a):
    v = c * (1 - a["transaction_cost_rate"])
    out = [v]
    for _ in range(HORIZON):
        v = v * (1 + growth) - v * (a["house_maintenance_rate"] + a["property_tax_rate"])
        out.append(v)
    return _real(out, infl)


def _deposit(c, infl, a):
    d = a["deposit"]
    v, out = c, [c]
    for t in range(HORIZON):
        rate = max(d["rate_floor"],
                   d["rate_start"] - (d["rate_start"] - d["rate_floor"]) * t / d["decay_years"])
        v += v * rate * (1 - d["interest_tax"])
        out.append(v)
    return _real(out, infl)


def _compound(c, r, infl):
    return _real([c * (1 + r) ** t for t in range(HORIZON + 1)], infl)


def run(a):
    # pess = bad for the saver: pair pess returns/growth with pess (high) inflation
    scenarios = {}
    for cap in CAPITALS:
        key = str(cap)
        def put(name, series_by_path):
            scenarios.setdefault(name, {})[key] = series_by_path
        put("buy_now_house", {p: _buy_now(cap, a["growth"]["house"][p], a["inflation"][p], a) for p in PATHS})
        put("buy_now_flat", {p: _buy_now(cap, a["growth"]["flat"][p], a["inflation"][p], a) for p in PATHS})
        put("deposit", {p: _deposit(cap, a["inflation"][p], a) for p in PATHS})
        ofz_net = a["ofz_ytm"] * (1 - a["deposit"]["interest_tax"])
        put("ofz", {p: _compound(cap, ofz_net, a["inflation"][p]) for p in PATHS})
        for name in ("tmos", "tpay", "gold", "usd", "btc"):
            put(name, {p: _compound(cap, a["returns"][name][p], a["inflation"][p]) for p in PATHS})

    mid = str(CAPITALS[1])
    house3 = scenarios["buy_now_house"][mid]["base"][3]
    depo3 = scenarios["deposit"][mid]["base"][3]
    ratio = depo3 / house3
    if ratio > 1.20:
        light, reason = "red", ("Депозит за 3 года обгоняет покупку дома более чем на 20% "
                                "(базовый сценарий) — финансово выгоднее подождать.")
    elif ratio > 1.05:
        light, reason = "yellow", ("Депозит за 3 года несколько выгоднее покупки (базовый "
                                   "сценарий) — торопиться некуда, можно спокойно искать свой дом.")
    else:
        light, reason = "green", ("Покупка сопоставима с депозитом или лучше (базовый сценарий) "
                                  "— если дом нашёлся, откладывать нет финансового смысла.")
    return {"as_of": date.today().isoformat(),
            "capital_levels": CAPITALS, "horizon_years": HORIZON,
            "scenarios": scenarios,
            "verdict": {"light": light, "reason_ru": reason,
                        "numbers": {"deposit_y3_real": round(depo3),
                                    "buy_house_y3_real": round(house3),
                                    "ratio": round(ratio, 3)}},
            "assumptions_echo": a}


def main():
    a = json.loads(ASSUMPTIONS_PATH.read_text())
    store.atomic_write(OUT_PATH, run(a))
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass** — Expected: 5 passed.

- [ ] **Step 6: Generate output and commit**

```bash
.venv/bin/python scripts/model.py
git add data/assumptions.json scripts/model.py tests/test_model.py site/data/scenarios.json
git commit -m "feat: scenario model with verdict"
```

---

### Task 9: fairprice.py + realty benchmarks

**Files:**
- Create: `scripts/fairprice.py`, `tests/test_fairprice.py`, `data/realty.json` (seed)

**Interfaces:**
- Consumes: `store.load`, `store.atomic_write`, `crypto_util.encrypt/decrypt/load_passphrase`, salt from `site/data/gate.json`.
- Produces: `assess(listing: dict, benchmarks: dict) -> dict` (pure; returns assessment block `{"price_per_m2", "fair_per_m2", "verdict": "below market|fair|overpriced", "reprice_flag": bool, "note"}`), `load_journal() -> dict`, `save_journal(journal: dict) -> None` (writes local `data/listings.json` + encrypted `data/listings.enc` + `site/data/listings.enc`), `main() -> None` re-assessing every listing. Verdict thresholds: price vs fair ±10%. Reprice flag: any consecutive `price_history` change > 20% either way.

- [ ] **Step 1: Seed benchmarks** — `data/realty.json` (initial estimates from the first three ingested listings' surroundings; refined in Task 16):

```json
{"points": [
 {"date": "2026-07-25", "segment": "flat", "price_per_m2": 160000,
  "source": "median of on-page Cian comparables, Pushkino, 2026-07-25"},
 {"date": "2026-07-25", "segment": "year-round house", "price_per_m2": 100000,
  "source": "initial estimate, Pushkinsky district asking prices, to be refined"},
 {"date": "2026-07-25", "segment": "dacha", "price_per_m2": 70000,
  "source": "initial estimate, to be refined"}
]}
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_fairprice.py
import sys

sys.path.insert(0, "scripts")
import fairprice

BENCH = {"flat": 160000, "year-round house": 100000}


def _flat(price, m2=80, comps=None):
    l = {"id": "T1", "segment": "flat", "price_rub": price, "flat_m2": m2}
    if comps:
        l["comparables_per_m2"] = comps
    return l


def test_fair_within_10pct():
    a = fairprice.assess(_flat(12_800_000), BENCH)  # exactly 160k/m2
    assert a["verdict"] == "fair"


def test_overpriced_above_10pct():
    assert fairprice.assess(_flat(15_000_000), BENCH)["verdict"] == "overpriced"


def test_below_market():
    assert fairprice.assess(_flat(11_000_000), BENCH)["verdict"] == "below market"


def test_comparables_override_benchmark():
    a = fairprice.assess(_flat(12_000_000, comps=[150000, 152000, 148000]), BENCH)
    assert a["fair_per_m2"] == 150000  # median of comps, not segment benchmark


def test_house_uses_house_m2():
    h = {"id": "T2", "segment": "year-round house", "price_rub": 23_400_000, "house_m2": 234}
    assert fairprice.assess(h, BENCH)["price_per_m2"] == 100000


def test_reprice_flag():
    l = _flat(33_500_000)
    l["price_history"] = [{"date": "2026-07-11", "price_rub": 15_500_000},
                          {"date": "2026-07-25", "price_rub": 33_500_000}]
    assert fairprice.assess(l, BENCH)["reprice_flag"] is True


def test_no_reprice_flag_small_change():
    l = _flat(12_000_000)
    l["price_history"] = [{"date": "2026-07-01", "price_rub": 12_500_000},
                          {"date": "2026-07-25", "price_rub": 12_000_000}]
    assert fairprice.assess(l, BENCH)["reprice_flag"] is False
```

- [ ] **Step 3: Run tests to verify they fail** — `.venv/bin/pytest tests/test_fairprice.py -v`

- [ ] **Step 4: Implement**

```python
# scripts/fairprice.py
"""Segment-aware fair-price assessment; journal encryption round-trip."""
import base64
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import crypto_util
import store

JOURNAL_LOCAL = Path("data/listings.json")
JOURNAL_ENC = Path("data/listings.enc")
JOURNAL_SITE = Path("site/data/listings.enc")
GATE_PATH = Path("site/data/gate.json")
REALTY_PATH = Path("data/realty.json")
FAIR_BAND = 0.10
REPRICE_THRESHOLD = 0.20


def _salt():
    return base64.b64decode(json.loads(GATE_PATH.read_text())["salt"])


def latest_benchmarks():
    bench = {}
    for pt in store.load(REALTY_PATH)["points"]:
        bench[pt["segment"]] = pt["price_per_m2"]  # points are chronological; last wins
    return bench


def assess(listing, benchmarks):
    area = listing.get("house_m2") or listing.get("flat_m2")
    ppm2 = listing["price_rub"] / area
    comps = listing.get("comparables_per_m2")
    fair = statistics.median(comps) if comps else benchmarks[listing["segment"]]
    ratio = ppm2 / fair
    if ratio < 1 - FAIR_BAND:
        verdict = "below market"
    elif ratio > 1 + FAIR_BAND:
        verdict = "overpriced"
    else:
        verdict = "fair"
    flag = False
    hist = [h["price_rub"] for h in listing.get("price_history", [])]
    for a, b in zip(hist, hist[1:]):
        if abs(b - a) / a > REPRICE_THRESHOLD:
            flag = True
    return {"price_per_m2": round(ppm2), "fair_per_m2": round(fair),
            "verdict": verdict, "reprice_flag": flag,
            "note": f"{round(ppm2)} vs fair {round(fair)} RUB/m2 ({ratio:+.0%} vs fair)".replace("+-", "-")}


def load_journal():
    if JOURNAL_LOCAL.exists():
        return json.loads(JOURNAL_LOCAL.read_text())
    if JOURNAL_ENC.exists():
        raw = crypto_util.decrypt(JOURNAL_ENC.read_bytes(), crypto_util.load_passphrase(), _salt())
        return json.loads(raw)
    return {"listings": []}


def save_journal(journal):
    store.atomic_write(JOURNAL_LOCAL, journal)
    blob = crypto_util.encrypt(json.dumps(journal, ensure_ascii=False).encode(),
                               crypto_util.load_passphrase(), _salt())
    for p in (JOURNAL_ENC, JOURNAL_SITE):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(blob)


def main():
    journal = load_journal()
    bench = latest_benchmarks()
    for listing in journal["listings"]:
        manual_note = listing.get("assessment", {}).get("manual_note")
        listing["assessment"] = assess(listing, bench)
        if manual_note:
            listing["assessment"]["manual_note"] = manual_note
    save_journal(journal)
    print(f"assessed {len(journal['listings'])} listings")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass** — Expected: 7 passed.

- [ ] **Step 6: Commit** (only code, seed benchmarks and tests — journal artifacts appear in Task 16)

```bash
git add scripts/fairprice.py tests/test_fairprice.py data/realty.json
git commit -m "feat: fair-price engine with reprice flag"
```

---

### Task 10: add_listing.py

**Files:**
- Create: `scripts/add_listing.py`, `tests/test_add_listing.py`

**Interfaces:**
- Consumes: `fairprice.load_journal/save_journal/main`, `crypto_util.encrypt/load_passphrase`, salt via `fairprice._salt`.
- Produces: `next_id(journal: dict) -> str` ("L001", "L002", …), `process_photos(listing_id: str, photo_paths: list[str], passphrase: str, salt: bytes) -> int` (compress to JPEG ≤1600px wide quality 80 into `data/photos/<id>-<n>.jpg`, encrypt to `site/data/photos/<id>-<n>.enc`, return count), CLI `python scripts/add_listing.py entry.json --photos p1.jpg p2.jpg`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_add_listing.py
import base64, io, json, sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, "scripts")
import add_listing
import crypto_util


def test_next_id():
    assert add_listing.next_id({"listings": []}) == "L001"
    assert add_listing.next_id({"listings": [{"id": "L001"}, {"id": "L007"}]}) == "L008"


def test_process_photos(tmp_path, monkeypatch):
    monkeypatch.setattr(add_listing, "PHOTOS_LOCAL", tmp_path / "local")
    monkeypatch.setattr(add_listing, "PHOTOS_SITE", tmp_path / "site")
    src = tmp_path / "big.png"
    Image.new("RGB", (3200, 2400), "red").save(src)
    salt = b"0123456789abcdef"
    n = add_listing.process_photos("L001", [str(src)], "phrase", salt)
    assert n == 1
    jpg = tmp_path / "local" / "L001-1.jpg"
    assert Image.open(jpg).width <= 1600
    enc = (tmp_path / "site" / "L001-1.enc").read_bytes()
    assert crypto_util.decrypt(enc, "phrase", salt) == jpg.read_bytes()
```

- [ ] **Step 2: Run tests to verify they fail** — `.venv/bin/pytest tests/test_add_listing.py -v`

- [ ] **Step 3: Implement**

```python
# scripts/add_listing.py
"""Ingest one listing (agent-extracted JSON + photo files) into the journal."""
import argparse
import base64
import json
import sys
from datetime import date
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import crypto_util
import fairprice

PHOTOS_LOCAL = Path("data/photos")
PHOTOS_SITE = Path("site/data/photos")
MAX_WIDTH = 1600
JPEG_QUALITY = 80


def next_id(journal):
    nums = [int(l["id"][1:]) for l in journal["listings"] if l["id"].startswith("L")]
    return f"L{(max(nums) if nums else 0) + 1:03d}"


def process_photos(listing_id, photo_paths, passphrase, salt):
    PHOTOS_LOCAL.mkdir(parents=True, exist_ok=True)
    PHOTOS_SITE.mkdir(parents=True, exist_ok=True)
    for n, src in enumerate(photo_paths, 1):
        img = Image.open(src).convert("RGB")
        if img.width > MAX_WIDTH:
            img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)))
        jpg = PHOTOS_LOCAL / f"{listing_id}-{n}.jpg"
        img.save(jpg, "JPEG", quality=JPEG_QUALITY)
        blob = crypto_util.encrypt(jpg.read_bytes(), passphrase, salt)
        (PHOTOS_SITE / f"{listing_id}-{n}.enc").write_bytes(blob)
    return len(photo_paths)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("entry_json", help="path to agent-extracted listing JSON")
    ap.add_argument("--photos", nargs="*", default=[])
    args = ap.parse_args(argv)

    entry = json.loads(Path(args.entry_json).read_text())
    journal = fairprice.load_journal()
    entry["id"] = next_id(journal)
    entry.setdefault("added", date.today().isoformat())
    entry.setdefault("status", "considering")
    passphrase = crypto_util.load_passphrase()
    entry["photos"] = process_photos(entry["id"], args.photos, passphrase, fairprice._salt())
    journal["listings"].append(entry)
    fairprice.save_journal(journal)
    fairprice.main()  # re-assess everything, rewrites the .enc files
    print(f"added {entry['id']}: {entry.get('label', '')}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass** — Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/add_listing.py tests/test_add_listing.py && git commit -m "feat: listing ingestion with encrypted photos"
```

---

### Task 11: update_all.py

**Files:**
- Create: `scripts/update_all.py`, `tests/test_update_all.py`

**Interfaces:**
- Consumes: `fetch_cbr.main`, `fetch_moex.main`, `fetch_crypto.main`, `model.main`.
- Produces: `run_all(fetchers: dict[str, callable]) -> dict[str, str]` (statuses: "appended" / "skipped (dup)" / "FAILED: <err>"); CLI runs fetchers fail-soft, then model (model failure = non-zero exit: better no update than a wrong chart).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_update_all.py
import sys

sys.path.insert(0, "scripts")
import update_all


def test_fail_soft_continues():
    def boom():
        raise RuntimeError("network down")
    statuses = update_all.run_all({"ok": lambda: True, "boom": boom, "dup": lambda: False})
    assert statuses["ok"] == "appended"
    assert statuses["dup"] == "skipped (dup)"
    assert statuses["boom"].startswith("FAILED")
```

- [ ] **Step 2: Run test to verify it fails** — `.venv/bin/pytest tests/test_update_all.py -v`

- [ ] **Step 3: Implement**

```python
# scripts/update_all.py
"""Refresh all data sources (fail-soft) and rebuild model output."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def run_all(fetchers):
    statuses = {}
    for name, fn in fetchers.items():
        try:
            statuses[name] = "appended" if fn() else "skipped (dup)"
        except Exception as e:
            statuses[name] = f"FAILED: {e}"
    return statuses


if __name__ == "__main__":
    import fetch_cbr, fetch_crypto, fetch_moex, model
    statuses = run_all({"cbr": fetch_cbr.main, "moex": fetch_moex.main,
                        "crypto": fetch_crypto.main})
    for name, s in statuses.items():
        print(f"{name}: {s}")
    model.main()  # loud failure by design
```

- [ ] **Step 4: Run test to verify it passes**, then live run:

```bash
.venv/bin/pytest tests/test_update_all.py -v
.venv/bin/python scripts/update_all.py
```

Expected: three source statuses (dup skips are fine — Task 5–7 already pulled today) + "wrote site/data/scenarios.json".

- [ ] **Step 5: Commit**

```bash
git add scripts/update_all.py tests/test_update_all.py data/ site/data/scenarios.json
git commit -m "feat: update_all orchestrator"
```

---

### Task 12: site foundation — style.css, gate.js, index.html

**Files:**
- Create: `site/assets/style.css`, `site/assets/gate.js`, `site/index.html`, `site/robots.txt`

**Interfaces:**
- Consumes: `site/data/gate.json` (Task 3), `site/data/scenarios.json` (Task 8).
- Produces: `window.gateReady` — Promise resolving `{passphrase, cryptoKey}` (cryptoKey is an AES-GCM `CryptoKey`), rejecting if locked; `window.decryptBlob(cryptoKey, arrayBuffer) -> Promise<ArrayBuffer>`; CSS classes `body.locked`/`body.unlocked`; shared nav markup. All later pages include `gate.js` and hide `<main>` until unlocked.

- [ ] **Step 1: Write the files**

```css
/* site/assets/style.css */
:root { --fg: #1a1a1a; --bg: #fdfcf8; --accent: #2a6b4f; --muted: #777;
        --green: #2e8b57; --yellow: #d99a00; --red: #c0392b; }
* { box-sizing: border-box; }
body { font-family: Georgia, "Times New Roman", serif; font-size: 21px;
       line-height: 1.55; color: var(--fg); background: var(--bg);
       max-width: 60rem; margin: 0 auto; padding: 1rem; }
h1 { font-size: 1.7em; } h2 { font-size: 1.3em; }
nav { display: flex; flex-wrap: wrap; gap: 1rem; padding: .5rem 0;
      border-bottom: 2px solid var(--accent); margin-bottom: 1.5rem; }
nav a { color: var(--accent); text-decoration: none; font-weight: bold; }
nav a.current { border-bottom: 3px solid var(--accent); }
body.locked main, body.locked nav { display: none; }
#gate-msg { text-align: center; margin-top: 4rem; color: var(--muted); }
body.unlocked #gate-msg { display: none; }
.light { font-size: 1.2em; padding: 1rem 1.5rem; border-radius: .75rem;
         color: #fff; margin: 1rem 0; }
.light.green { background: var(--green); } .light.yellow { background: var(--yellow); }
.light.red { background: var(--red); }
.asof { color: var(--muted); font-size: .8em; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(20rem, 1fr));
         gap: 1.2rem; padding: 0; list-style: none; }
.card { border: 1px solid #ddd; border-radius: .75rem; background: #fff;
        padding: 1rem; cursor: pointer; }
.card img { max-width: 100%; border-radius: .5rem; }
.card.rejected { opacity: .45; }
.badge { display: inline-block; padding: .1rem .6rem; border-radius: 1rem;
         font-size: .75em; color: #fff; margin-right: .4rem; }
.badge.fair { background: var(--green); } .badge.overpriced { background: var(--red); }
.badge.below { background: #1f6fb2; } .badge.status { background: var(--muted); }
.badge.flag { background: var(--yellow); }
.numbers { display: flex; gap: 2rem; flex-wrap: wrap; }
.numbers div { text-align: center; }
.numbers strong { display: block; font-size: 1.5em; }
table { border-collapse: collapse; width: 100%; }
td, th { border: 1px solid #ddd; padding: .5rem; text-align: right; }
th:first-child, td:first-child { text-align: left; }
```

```javascript
// site/assets/gate.js
// Magic-URL gate. Crypto params MUST match scripts/crypto_util.py
// (PBKDF2-HMAC-SHA256, iterations from gate.json, AES-GCM, blob = 12-byte IV || ct).
(function () {
  const enc = new TextEncoder();
  const b64ToBytes = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));

  async function sha256b64(text) {
    const d = await crypto.subtle.digest("SHA-256", enc.encode(text));
    return btoa(String.fromCharCode(...new Uint8Array(d)));
  }

  async function deriveKey(passphrase, saltB64, iterations) {
    const material = await crypto.subtle.importKey(
      "raw", enc.encode(passphrase), "PBKDF2", false, ["deriveKey"]);
    return crypto.subtle.deriveKey(
      { name: "PBKDF2", salt: b64ToBytes(saltB64), iterations, hash: "SHA-256" },
      material, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
  }

  window.decryptBlob = async function (cryptoKey, buf) {
    const b = new Uint8Array(buf);
    return crypto.subtle.decrypt({ name: "AES-GCM", iv: b.slice(0, 12) }, cryptoKey, b.slice(12));
  };

  window.gateReady = (async function () {
    const params = await fetch("data/gate.json").then((r) => r.json());
    const candidate = decodeURIComponent(location.hash.slice(1)) ||
                      localStorage.getItem("imobilien-key") || "";
    document.body.classList.add("locked");
    if (candidate && (await sha256b64(candidate)) === params.digest) {
      localStorage.setItem("imobilien-key", candidate);
      history.replaceState(null, "", location.pathname);  // hide key from shoulder-surfers
      document.body.classList.replace("locked", "unlocked");
      const cryptoKey = await deriveKey(candidate, params.salt, params.iterations);
      return { passphrase: candidate, cryptoKey };
    }
    throw new Error("locked");
  })();
  window.gateReady.catch(() => {});  // page stays a neutral placeholder
})();
```

```html
<!-- site/index.html -->
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Семейный дом — вывод</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body class="locked">
<p id="gate-msg">Личная страница. Откройте её по ссылке из семейного чата.</p>
<nav>
  <a class="current" href="index.html">Вывод</a>
  <a href="scenarios.html">Сценарии</a>
  <a href="listings.html">Варианты</a>
  <a href="checklist.html">Как проверить дом</a>
</nav>
<main>
  <h1>Стоит ли покупать сейчас?</h1>
  <div id="verdict" class="light">Загрузка…</div>
  <div class="numbers" id="numbers"></div>
  <p>Дом — это не только деньги: это место, где собирается вся семья.
     Эти цифры нужны лишь для того, чтобы мечта не обошлась дороже, чем должна.</p>
  <p class="asof" id="asof"></p>
</main>
<script src="assets/gate.js"></script>
<script>
gateReady.then(async () => {
  const s = await fetch("data/scenarios.json").then(r => r.json());
  const v = s.verdict;
  const el = document.getElementById("verdict");
  el.classList.add(v.light);
  el.textContent = v.reason_ru;
  const fmt = (x) => (x / 1e6).toFixed(1).replace(".", ",") + " млн ₽";
  document.getElementById("numbers").innerHTML =
    `<div><strong>${fmt(v.numbers.buy_house_y3_real)}</strong>дом через 3 года<br>(в сегодняшних деньгах)</div>` +
    `<div><strong>${fmt(v.numbers.deposit_y3_real)}</strong>депозит через 3 года<br>(в сегодняшних деньгах)</div>`;
  document.getElementById("asof").textContent = "Данные от " + s.as_of + ". Расчёт для 17,5 млн ₽, базовый сценарий.";
}).catch(() => {});
</script>
</body>
</html>
```

```text
# site/robots.txt
User-agent: *
Disallow: /
```

- [ ] **Step 2: Verify locally**

```bash
python3 -m http.server 8321 -d site &
```

Open `http://localhost:8321/` — placeholder only. Open `http://localhost:8321/#<IMOBILIEN_KEY value>` — verdict renders, hash disappears from URL, reload keeps it unlocked. (Requires Task 3's real `gate.json` — run `.venv/bin/python scripts/gen_gate.py` with a `.env` in place first.)

- [ ] **Step 3: Commit**

```bash
git add site/ && git commit -m "feat: gated site foundation with verdict page"
```

---

### Task 13: scenarios.html

**Files:**
- Create: `site/scenarios.html`

**Interfaces:**
- Consumes: `gateReady`, `site/data/scenarios.json`, `site/assets/chart.umd.js`.

- [ ] **Step 1: Write the page**

```html
<!-- site/scenarios.html -->
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Сценарии для капитала</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body class="locked">
<p id="gate-msg">Личная страница. Откройте её по ссылке из семейного чата.</p>
<nav>
  <a href="index.html">Вывод</a>
  <a class="current" href="scenarios.html">Сценарии</a>
  <a href="listings.html">Варианты</a>
  <a href="checklist.html">Как проверить дом</a>
</nav>
<main>
  <h1>Что станет с деньгами за 10 лет</h1>
  <p>Все суммы — в сегодняшних деньгах (с учётом инфляции), базовый сценарий.</p>
  <p id="capitals"></p>
  <canvas id="chart" height="220"></canvas>
  <h2>Через 3 и 5 лет</h2>
  <table id="tbl"></table>
  <p class="asof" id="asof"></p>
</main>
<script src="assets/chart.umd.js"></script>
<script src="assets/gate.js"></script>
<script>
const NAMES = {buy_now_house: "Купить дом сейчас", buy_now_flat: "Купить квартиру сейчас",
  deposit: "Депозит", ofz: "ОФЗ", tmos: "Фонд акций (TMOS)", tpay: "Фонд облигаций (TPAY)",
  gold: "Золото", usd: "Доллар", btc: "Биткойн"};
const COLORS = {buy_now_house: "#2a6b4f", buy_now_flat: "#67a487", deposit: "#1f6fb2",
  ofz: "#7db3dd", tmos: "#c0392b", tpay: "#d98880", gold: "#d99a00", usd: "#888", btc: "#8e44ad"};
let chart, data, capital;

function render() {
  const fmt = (x) => (x / 1e6).toFixed(1).replace(".", ",");
  const ds = Object.keys(NAMES).map(k => ({
    label: NAMES[k], data: data.scenarios[k][capital].base,
    borderColor: COLORS[k], fill: false, tension: .2 }));
  if (chart) chart.destroy();
  chart = new Chart(document.getElementById("chart"), {
    type: "line",
    data: { labels: [...Array(11).keys()].map(y => y + " лет"), datasets: ds },
    options: { scales: { y: { ticks: { callback: v => fmt(v) + " млн" } } },
               plugins: { legend: { labels: { font: { size: 16 } } } } }
  });
  let html = "<tr><th>Вариант</th><th>3 года</th><th>5 лет</th><th>плохой / хороший (5 лет)</th></tr>";
  for (const k of Object.keys(NAMES)) {
    const s = data.scenarios[k][capital];
    html += `<tr><td>${NAMES[k]}</td><td>${fmt(s.base[3])} млн</td><td>${fmt(s.base[5])} млн</td>` +
            `<td>${fmt(s.pess[5])} — ${fmt(s.opt[5])} млн</td></tr>`;
  }
  document.getElementById("tbl").innerHTML = html;
}

gateReady.then(async () => {
  data = await fetch("data/scenarios.json").then(r => r.json());
  capital = String(data.capital_levels[1]);
  const fmtC = (c) => (c / 1e6).toFixed(1).replace(".0", "").replace(".", ",") + " млн";
  document.getElementById("capitals").innerHTML = "Капитал: " + data.capital_levels.map(c =>
    `<button data-c="${c}" style="font-size:1em;margin-right:.5rem">${fmtC(c)} ₽</button>`).join("");
  document.querySelectorAll("#capitals button").forEach(b =>
    b.addEventListener("click", () => { capital = b.dataset.c; render(); }));
  document.getElementById("asof").textContent = "Данные от " + data.as_of + ".";
  render();
}).catch(() => {});
</script>
</body>
</html>
```

- [ ] **Step 2: Verify locally** — with the server from Task 12 and the key in the URL hash, chart renders 9 lines; capital buttons switch; table shows pess—opt band.

- [ ] **Step 3: Commit** — `git add site/scenarios.html && git commit -m "feat: scenarios page"`

---

### Task 14: listings.html (gallery)

**Files:**
- Create: `site/listings.html`

**Interfaces:**
- Consumes: `gateReady`, `decryptBlob`, `site/data/listings.enc`, `site/data/photos/<id>-<n>.enc`. Journal JSON shape per spec section 4 (fields incl. `label`, `settlement`, `price_rub`, `segment`, `status`, `photos` count, `assessment` from `fairprice.assess`, optional `family_notes`, `price_history`, `url`).

- [ ] **Step 1: Write the page**

```html
<!-- site/listings.html -->
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Варианты</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body class="locked">
<p id="gate-msg">Личная страница. Откройте её по ссылке из семейного чата.</p>
<nav>
  <a href="index.html">Вывод</a>
  <a href="scenarios.html">Сценарии</a>
  <a class="current" href="listings.html">Варианты</a>
  <a href="checklist.html">Как проверить дом</a>
</nav>
<main>
  <h1>Что мы смотрим</h1>
  <p id="filter">
    <button data-seg="all" style="font-size:1em">Все</button>
    <button data-seg="house" style="font-size:1em">Дома</button>
    <button data-seg="flat" style="font-size:1em">Квартиры</button>
  </p>
  <ul class="cards" id="cards"></ul>
</main>
<script src="assets/gate.js"></script>
<script>
const VERDICT_RU = {"fair": ["fair", "Справедливая цена"],
  "overpriced": ["overpriced", "Переоценён"], "below market": ["below", "Ниже рынка"]};
const STATUS_RU = {considering: "Рассматриваем", viewed: "Смотрели",
  favorite: "Фаворит ★", rejected: "Отклонён"};
const ORDER = {favorite: 0, considering: 1, viewed: 2, rejected: 3};
const fmtM = (x) => (x / 1e6).toFixed(1).replace(".", ",") + " млн ₽";
let key, journal, seg = "all";

async function photoUrl(id, n) {
  const buf = await fetch(`data/photos/${id}-${n}.enc`).then(r => {
    if (!r.ok) throw new Error("no photo");
    return r.arrayBuffer();
  });
  const plain = await decryptBlob(key, buf);
  return URL.createObjectURL(new Blob([plain], { type: "image/jpeg" }));
}

function isHouse(l) { return l.segment !== "flat"; }

async function render() {
  const cards = document.getElementById("cards");
  cards.innerHTML = "";
  const items = journal.listings
    .filter(l => seg === "all" || (seg === "house" ? isHouse(l) : !isHouse(l)))
    .sort((a, b) => (ORDER[a.status] ?? 9) - (ORDER[b.status] ?? 9));
  for (const l of items) {
    const a = l.assessment || {};
    const [vc, vt] = VERDICT_RU[a.verdict] || ["status", a.verdict || "—"];
    const area = l.house_m2 || l.flat_m2 || "?";
    const li = document.createElement("li");
    li.className = "card" + (l.status === "rejected" ? " rejected" : "");
    li.innerHTML =
      `<div class="ph"></div><h2>${l.label}</h2>` +
      `<p>${l.settlement} · ${area} м² · <strong>${fmtM(l.price_rub)}</strong></p>` +
      `<p><span class="badge ${vc}">${vt}</span>` +
      `<span class="badge status">${STATUS_RU[l.status] || l.status}</span>` +
      (a.reprice_flag ? `<span class="badge flag">Цена скакала!</span>` : "") + `</p>` +
      `<div class="details" hidden>` +
      `<p>${Math.round(a.price_per_m2 / 1000)} тыс ₽/м² при рынке ~${Math.round(a.fair_per_m2 / 1000)} тыс ₽/м²</p>` +
      (l.family_notes ? `<p>${l.family_notes}</p>` : "") +
      (l.price_history ? `<p>История цены: ${l.price_history.map(h => h.date + " — " + fmtM(h.price_rub)).join("; ")}</p>` : "") +
      (l.url ? `<p><a href="${l.url}" target="_blank" rel="noreferrer">Объявление</a></p>` : "") +
      `<div class="more-photos"></div></div>`;
    if (l.photos > 0) {
      photoUrl(l.id, 1).then(u => { li.querySelector(".ph").innerHTML = `<img src="${u}" alt="">`; })
        .catch(() => {});
    }
    li.addEventListener("click", async (ev) => {
      if (ev.target.tagName === "A") return;
      const d = li.querySelector(".details");
      d.hidden = !d.hidden;
      const box = li.querySelector(".more-photos");
      if (!d.hidden && !box.childElementCount && l.photos > 1) {
        for (let n = 2; n <= l.photos; n++) {
          photoUrl(l.id, n).then(u => { box.innerHTML += `<img src="${u}" alt="">`; }).catch(() => {});
        }
      }
    });
    cards.appendChild(li);
  }
}

gateReady.then(async (g) => {
  key = g.cryptoKey;
  const buf = await fetch("data/listings.enc").then(r => r.arrayBuffer());
  journal = JSON.parse(new TextDecoder().decode(await decryptBlob(key, buf)));
  document.querySelectorAll("#filter button").forEach(b =>
    b.addEventListener("click", () => { seg = b.dataset.seg; render(); }));
  render();
}).catch(() => {});
</script>
</body>
</html>
```

- [ ] **Step 2: Verify locally** — needs Task 16's encrypted journal, OR create a temporary one: run `.venv/bin/python scripts/fairprice.py` (encrypts the existing local `data/listings.json`). Gallery shows 3 cards; the Mogiltsy house card shows the yellow "Цена скакала!" badge; rejected filter/order logic can be eyeballed by temporarily setting a status.

- [ ] **Step 3: Commit** — `git add site/listings.html && git commit -m "feat: encrypted listings gallery"`

---

### Task 15: checklist.html

**Files:**
- Create: `site/checklist.html`

**Interfaces:**
- Consumes: `gateReady` only (static content).

- [ ] **Step 1: Write the page**

```html
<!-- site/checklist.html -->
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Как проверить дом</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body class="locked">
<p id="gate-msg">Личная страница. Откройте её по ссылке из семейного чата.</p>
<nav>
  <a href="index.html">Вывод</a>
  <a href="scenarios.html">Сценарии</a>
  <a href="listings.html">Варианты</a>
  <a class="current" href="checklist.html">Как проверить дом</a>
</nav>
<main>
  <h1>Как проверить дом перед покупкой</h1>
  <h2>До просмотра — по телефону</h2>
  <ul>
    <li>Кто продаёт: собственник или агент? Сколько собственников?</li>
    <li>Почему продают и как давно продаётся?</li>
    <li>Менялась ли цена? Резкие скачки цены — плохой знак (мы уже видели такое).</li>
    <li>Есть ли документы на дом И на землю (два разных документа)?</li>
  </ul>
  <h2>Документы — не подписывать ничего без этого</h2>
  <ul>
    <li>Свежая выписка ЕГРН на дом и на участок: собственник совпадает с продавцом,
        нет арестов, залогов, обременений.</li>
    <li>Категория земли и вид использования: ИЖС — хорошо; СНТ — осторожно.</li>
    <li>Границы участка отмежёваны (стоят на кадастровом учёте).</li>
    <li>Нет долгов по коммуналке и налогам; продавец не банкрот.</li>
    <li>Если продавец в браке — согласие супруга. Если по наследству — сколько лет прошло.</li>
    <li>Задаток — только по письменному соглашению, никаких «на слово».</li>
  </ul>
  <h2>На просмотре — сам дом</h2>
  <ul>
    <li>Фундамент: трещины, сырость в подвале, перекосы дверей и окон.</li>
    <li>Крыша и чердак: подтёки, состояние утепления.</li>
    <li>Газ: заведён ли В ДОМ официально (договор с облгазом), а не «газ по границе».</li>
    <li>Вода и канализация: центральные или скважина/септик, зимний режим.</li>
    <li>Электричество: сколько киловатт выделено (для дома нужно 10–15).</li>
    <li>Отопление: включить, проверить все батареи; спросить счета за зиму.</li>
    <li>Дороги зимой: чистят ли, кто и за чей счёт.</li>
  </ul>
  <h2>Главное правило</h2>
  <p>Понравившийся дом никуда не убежит за неделю проверки документов.
     А спешка — самый дорогой способ купить чужие проблемы.
     Любой документ перед подписанием показываем всей семье.</p>
</main>
<script src="assets/gate.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify locally** (gate works, text renders), **commit** — `git add site/checklist.html && git commit -m "feat: house inspection checklist page"`

---

### Task 16: First real deployment

**Files:**
- Create: `.env` (LOCAL ONLY — never committed), `data/listings.enc`, `site/data/listings.enc`, `site/data/gate.json`, `notes/methodology.md`, `notes/market-pushkino.md`, `notes/legal-checklist.md`
- Modify: `data/listings.json` (local): move `comparables_per_m2` arrays from inside `assessment` to the listing top level (the format `fairprice.assess` consumes).

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Generate passphrase and gate**

```bash
python3 - <<'EOF'
import secrets
words = [secrets.choice("рябина сосна ольха клён липа вяз дуб пихта кедр ясень".split()) for _ in range(2)]
print("IMOBILIEN_KEY=" + "-".join(words) + "-" + secrets.token_hex(4))
EOF
```

Write the output line into `.env`. Verify `git status` does NOT show `.env`. Run `.venv/bin/python scripts/gen_gate.py`.

- [ ] **Step 2: Fix journal format and run the full pipeline**

In local `data/listings.json` (gitignored — values stay out of this tracked
plan): for each flat listing move its `comparables_per_m2` array from inside
`assessment` to the listing top level, and delete the old hand-written
`assessment` blocks. Then:

```bash
.venv/bin/python scripts/update_all.py
.venv/bin/python scripts/fairprice.py
.venv/bin/pytest
```

Expected: all tests pass; `data/listings.enc` + `site/data/listings.enc` exist; L001 gets `reprice_flag: true`.

- [ ] **Step 3: Write notes**

`notes/methodology.md`: document every value in `data/assumptions.json` (one line each: value, source, as-of date, "initial estimate — refine with IRN/CBR data" where applicable), the fair-price thresholds (±10% band, 20% reprice flag), and the realty benchmark sources. `notes/market-pushkino.md`: current district observations — the three ingested listings, per-m² levels seen (flats ~148–177k, house asking anomaly L001), IRN Podmoskovye index and CBR key rate (14% as of 2026-07-25) with source URLs. `notes/legal-checklist.md`: the document checks from `checklist.html` in working form with links to ЕГРН/Росреестр services. No family names anywhere.

- [ ] **Step 4: Create GitHub repo, push, enable Pages**

```bash
git add -A && git status   # verify: no .env, no data/listings.json, no data/photos/
git commit -m "feat: first data pull, encrypted journal, methodology notes"
gh repo create imobilien --public --source . --push
gh api -X POST repos/{owner}/imobilien/pages -f build_type=workflow || true
gh run watch
```

- [ ] **Step 5: Verify the live site**

Open `https://<username>.github.io/imobilien/` — placeholder only. Open with `#<passphrase>` — verdict, scenarios chart, gallery with 3 cards and decrypted photos (photos appear after the first `add_listing.py` run with real photo files; cards without photos degrade gracefully), checklist. Verify `https://<username>.github.io/imobilien/data/listings.enc` downloads as opaque binary.

- [ ] **Step 6: Hand the family link to the user** (in chat, never in the repo): `https://<username>.github.io/imobilien/#<passphrase>`.

---

## Self-review notes

- Spec coverage: data pipeline (T4–7, 11), model+verdict (T8), fair price+reprice flag (T9), ingestion+photos (T10), gate+encryption (T2–3, 12), four pages (T12–15), privacy (T16 step 4 check, .gitignore already committed), deploy (T1, T16). IRN/deposits/realty benchmarks are semi-manual by design — recorded via `store.append_point` into `data/realty.json`/`data/deposits.json`; first entries in T9/T16.
- Photos for L001–L003 were not downloaded during ad-hoc ingestion; gallery degrades gracefully (`photos: 0` → no image). Re-ingest photos later via a Claude session + `add_listing.py`.
- Deferred (YAGNI, revisit when needed): `data/deposits.json` fetcher (manual entry is fine), IRN chart digitization, flat property-tax nuance vs house in the model (uses the same rate).
