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
            "note": f"{round(ppm2)} vs fair {round(fair)} RUB/m2 ({ratio - 1:+.0%} vs fair)"}


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
