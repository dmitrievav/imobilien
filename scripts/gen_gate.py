"""Generate site/data/gate.json (verifier + salt + iterations) from IMOBILIEN_KEY."""
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
    salt = base64.b64decode(salt_b64)
    gate = {"verifier": crypto_util.verifier_b64(passphrase, salt),
            "salt": salt_b64, "iterations": crypto_util.ITERATIONS}
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(json.dumps(gate, indent=1))
    return gate


if __name__ == "__main__":
    write_gate(crypto_util.load_passphrase())
    print(f"wrote {GATE_PATH}")
