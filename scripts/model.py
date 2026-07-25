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
