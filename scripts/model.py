"""Capital scenarios in nominal RUB. Pure math in run(); IO in main().

Deliberately simple, because the audience is a 70+ reader: one capital, one
average return per asset, no pessimistic/optimistic fan. Uncertainty is
carried by a risk rank instead of a band, and the inflation line shows what
merely keeping up with prices would require.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import store

OUT_PATH = Path("site/data/scenarios.json")
ASSUMPTIONS_PATH = Path("data/assumptions.json")
HISTORY_PATH = Path("data/history.json")
PROPERTY_ASSETS = ("buy_now_house", "buy_now_flat")


def _property_series(capital, rate, horizon, a):
    """Bought outright: entry costs once, then growth minus yearly upkeep."""
    v = capital * (1 - a["transaction_cost_rate"])
    out = [v]
    upkeep = a["house_maintenance_rate"] + a["property_tax_rate"]
    for _ in range(horizon):
        v = v * (1 + rate) - v * upkeep
        out.append(v)
    return out


def _deposit_series(capital, horizon, a):
    """Rate glides from today's level down to the floor; interest is taxed."""
    d = a["deposit"]
    v, out = capital, [capital]
    for t in range(horizon):
        rate = max(d["rate_floor"],
                   d["rate_start"] - (d["rate_start"] - d["rate_floor"]) * t / d["decay_years"])
        v += v * rate * (1 - d["interest_tax"])
        out.append(v)
    return out


def _compound_series(capital, rate, horizon):
    return [capital * (1 + rate) ** t for t in range(horizon + 1)]


def _avg_rate(series):
    """Annualised growth actually delivered by a series — the number we show."""
    years = len(series) - 1
    return (series[-1] / series[0]) ** (1 / years) - 1


def run(a):
    capital, horizon = a["capital"], a["horizon_years"]
    assets = {}
    for name, cfg in a["assets"].items():
        if name in PROPERTY_ASSETS:
            series = _property_series(capital, cfg["rate"], horizon, a)
        elif name == "deposit":
            series = _deposit_series(capital, horizon, a)
        else:
            series = _compound_series(capital, cfg["rate"], horizon)
        assets[name] = {"series": [round(v) for v in series],
                        "avg_rate": round(_avg_rate(series), 4),
                        "risk": cfg["risk"], "basis_ru": cfg["basis_ru"],
                        # A flat percentage misleads where the rate is not flat
                        # (deposit glides down) or not gross (property pays upkeep).
                        "rate_label_ru": cfg.get("rate_label_ru")}

    inflation_line = [round(v) for v in _compound_series(capital, a["inflation"], horizon)]

    house3 = assets["buy_now_house"]["series"][3]
    depo3 = assets["deposit"]["series"][3]
    ratio = depo3 / house3
    if ratio > 1.20:
        light, reason = "red", ("Вклад за 3 года прибавляет заметно больше, чем дорожает дом. "
                                "Спешить с покупкой незачем — можно спокойно искать свой вариант.")
    elif ratio > 1.05:
        light, reason = "yellow", ("Вклад за 3 года немного обгоняет дом. Торопиться некуда, "
                                   "но и ждать бесконечно смысла нет.")
    else:
        light, reason = "green", ("Покупка не проигрывает вкладу. Если дом нашёлся — "
                                  "откладывать нет финансового смысла.")

    return {"as_of": date.today().isoformat(),
            "capital": capital, "horizon_years": horizon,
            "inflation": a["inflation"], "inflation_line": inflation_line,
            "assets": assets,
            "verdict": {"light": light, "reason_ru": reason,
                        "numbers": {"deposit_y3": depo3, "buy_house_y3": house3,
                                    "ratio": round(ratio, 3)}},
            "assumptions_echo": a}


def main():
    a = json.loads(ASSUMPTIONS_PATH.read_text())
    out = run(a)
    # Measured history travels with the forecast so the site can show readers
    # what these assets actually did, not only what we assume they will do.
    history = store.load(HISTORY_PATH)["points"]
    if history:
        out["history_echo"] = history[-1]
    store.atomic_write(OUT_PATH, out)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
