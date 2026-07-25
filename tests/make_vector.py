"""Run once: freezes crypto params into tests/vectors/gate_vector.json. Commit the output."""
import base64, json, sys
from pathlib import Path

sys.path.insert(0, "scripts")
import crypto_util

passphrase, salt, iv, plaintext = "test-vector", b"0123456789abcdef", b"\x00" * 12, "imobilien"
blob = crypto_util.encrypt(plaintext.encode(), passphrase, salt, iv=iv)
out = {"passphrase": passphrase, "salt": base64.b64encode(salt).decode(),
       "iv": base64.b64encode(iv).decode(), "plaintext": plaintext,
       "blob": base64.b64encode(blob).decode(), "iterations": crypto_util.ITERATIONS,
       "verifier": crypto_util.verifier_b64(passphrase, salt)}
Path("tests/vectors").mkdir(parents=True, exist_ok=True)
Path("tests/vectors/gate_vector.json").write_text(json.dumps(out, indent=1))
print("vector written")
