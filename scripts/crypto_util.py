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


def derive_key(passphrase: str, salt: bytes, iterations: int = ITERATIONS) -> bytes:
    kdf = PBKDF2HMAC(hashes.SHA256(), KEY_LEN, salt, iterations)
    return kdf.derive(passphrase.encode())


def verifier_b64(passphrase: str, salt: bytes, iterations: int = ITERATIONS) -> str:
    """Public gate verifier: SHA-256 of the derived key bytes.

    Salted and PBKDF2-expensive, so a guess costs the same as a real key
    derivation; the browser reuses the same bits as the AES-GCM key, so
    verification adds no work beyond one hash.
    """
    key = derive_key(passphrase, salt, iterations)
    return base64.b64encode(hashlib.sha256(key).digest()).decode()


def encrypt(data: bytes, passphrase: str, salt: bytes, iv: bytes | None = None) -> bytes:
    iv = iv if iv is not None else os.urandom(IV_LEN)
    ct = AESGCM(derive_key(passphrase, salt)).encrypt(iv, data, None)
    return iv + ct


def decrypt(blob: bytes, passphrase: str, salt: bytes) -> bytes:
    return AESGCM(derive_key(passphrase, salt)).decrypt(blob[:IV_LEN], blob[IV_LEN:], None)
