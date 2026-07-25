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


def test_verifier_is_sha256_of_derived_key():
    """The public verifier must cost a full PBKDF2 derivation per guess."""
    import hashlib
    salt = b"0123456789abcdef"
    key = crypto_util.derive_key("abc", salt, iterations=1000)
    exp = base64.b64encode(hashlib.sha256(key).digest()).decode()
    assert crypto_util.verifier_b64("abc", salt, iterations=1000) == exp


def test_verifier_is_salted():
    v1 = crypto_util.verifier_b64("abc", b"0123456789abcdef", iterations=1000)
    v2 = crypto_util.verifier_b64("abc", b"fedcba9876543210", iterations=1000)
    assert v1 != v2


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
    assert crypto_util.decrypt(
        base64.b64decode(vec["blob"]), vec["passphrase"],
        base64.b64decode(vec["salt"])) == vec["plaintext"].encode()


def test_golden_vector_verifier():
    """The gate verifier gate.js compares against must never drift either."""
    vec = json.loads(Path("tests/vectors/gate_vector.json").read_text())
    assert crypto_util.verifier_b64(
        vec["passphrase"], base64.b64decode(vec["salt"]),
        vec["iterations"]) == vec["verifier"]
