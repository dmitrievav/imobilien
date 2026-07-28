"""Journal assessment and encryption round-trip.

The valuation itself lives in valuation.py — comparison with adjustments,
producing a range. This module wires it to the journal and adds the one
signal that has nothing to do with value: a suspicious price history.
"""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import crypto_util
import store
import valuation

JOURNAL_LOCAL = Path("data/listings.json")
JOURNAL_ENC = Path("data/listings.enc")
JOURNAL_SITE = Path("site/data/listings.enc")
GATE_PATH = Path("site/data/gate.json")
REPRICE_THRESHOLD = 0.20


def _salt():
    return base64.b64decode(json.loads(GATE_PATH.read_text())["salt"])


def reprice_flag(listing):
    """A large jump in either direction is a bait-listing / distress signal,
    independent of whether the current price is fair."""
    hist = [h["price_rub"] for h in listing.get("price_history", [])]
    return any(abs(b - a) / a > REPRICE_THRESHOLD for a, b in zip(hist, hist[1:]))


def assess(listing, benchmarks, factors=None):
    return {**valuation.estimate(listing, benchmarks, factors),
            "reprice_flag": reprice_flag(listing)}


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
    bench = valuation.latest_benchmarks()
    factors = valuation.load_factors()
    for listing in journal["listings"]:
        manual_note = listing.get("assessment", {}).get("manual_note")
        listing["assessment"] = assess(listing, bench, factors)
        if manual_note:
            listing["assessment"]["manual_note"] = manual_note
    save_journal(journal)
    print(f"assessed {len(journal['listings'])} listings")


if __name__ == "__main__":
    main()
