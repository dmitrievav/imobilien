import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
import crypto_util
import gen_gate


def test_creates_gate(tmp_path):
    gate = gen_gate.write_gate("phrase", tmp_path / "gate.json")
    saved = json.loads((tmp_path / "gate.json").read_text())
    assert saved == gate
    assert saved["iterations"] == crypto_util.ITERATIONS
    assert len(base64.b64decode(saved["salt"])) == 16
    assert saved["verifier"] == crypto_util.verifier_b64(
        "phrase", base64.b64decode(saved["salt"]))
    assert "digest" not in saved  # legacy unsalted SHA-256 field must be gone


def test_preserves_existing_salt(tmp_path):
    g1 = gen_gate.write_gate("phrase", tmp_path / "gate.json")
    g2 = gen_gate.write_gate("new phrase", tmp_path / "gate.json")
    assert g1["salt"] == g2["salt"]
    assert g1["verifier"] != g2["verifier"]
