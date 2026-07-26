"""Capital scenarios in nominal RUB. Pure math in run(); IO in main().

Deliberately simple, because the audience is a 70+ reader: one capital, one
average return per asset, no pessimistic/optimistic fan. Uncertainty is
carried by a risk rank and by each asset's current distance from its own
all-time high, not by a band of scenarios.

Two bases sit side by side on purpose. Globally traded asset classes use
125-year world evidence for their return above inflation, because any
Russian window is too short and too idiosyncratic to extrapolate. The
deposit and OFZ use today's actual Russian terms, because those are
contractual and knowable in advance rather than estimated from history.
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


def nominal_rate(cfg, inflation):
    """A world-evidence asset states its return above inflation; a local
    instrument states the rate itself."""
    if cfg.get("real_rate") is not None:
        return (1 + cfg["real_rate"]) * (1 + inflation) - 1
    return cfg.get("rate")


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


def depreciation(a):
    """Long-run ruble slide against the dollar: the inflation differential.

    Over a decade this is the only defensible path — anything else would be a
    currency forecast. It is an assumption, not a measurement, and the site
    says so: short-term the rate swings far more violently.
    """
    return (1 + a["inflation"]) / (1 + a["us_inflation"]) - 1


def to_usd(series, a):
    """Same money, seen from outside the ruble."""
    fx0, d = a["usd_rub"], depreciation(a)
    return [v / (fx0 * (1 + d) ** t) for t, v in enumerate(series)]


def run(a):
    capital, horizon, infl = a["capital"], a["horizon_years"], a["inflation"]
    assets = {}
    for name, cfg in a["assets"].items():
        if name == "deposit":
            series = _deposit_series(capital, horizon, a)
        else:
            series = _compound_series(capital, nominal_rate(cfg, infl), horizon)
        usd = to_usd(series, a)
        assets[name] = {"series": [round(v) for v in series],
                        "series_usd": [round(v) for v in usd],
                        "avg_rate": round(_avg_rate(series), 4),
                        "avg_rate_usd": round(_avg_rate(usd), 4),
                        "risk": cfg["risk"], "basis_ru": cfg["basis_ru"],
                        # A flat percentage misleads where the rate is not flat.
                        "rate_label_ru": cfg.get("rate_label_ru")}

    infl_line = _compound_series(capital, infl, horizon)
    return {"as_of": date.today().isoformat(),
            "capital": capital, "capital_usd": round(capital / a["usd_rub"]),
            "horizon_years": horizon,
            "inflation": infl, "us_inflation": a["us_inflation"],
            "usd_rub": a["usd_rub"], "depreciation": round(depreciation(a), 4),
            "inflation_line": [round(v) for v in infl_line],
            # In dollars the bar to clear is US inflation, not ours.
            "inflation_line_usd": [round(v) for v in
                                   _compound_series(capital / a["usd_rub"],
                                                    a["us_inflation"], horizon)],
            "assets": assets,
            "basis_note_ru": a.get("basis_note_ru"),
            "currency_note_ru": a.get("currency_note_ru"),
            "assumptions_echo": a}


def attach_drawdowns(out, a, history_point):
    """How far each asset sits below its own all-time high, straight from the
    measured series — the one place the site still shows Russian history."""
    for name, cfg in a["assets"].items():
        key = cfg.get("history_key")
        measured = history_point.get(key) if key and history_point else None
        out["assets"][name]["drawdown_pct"] = measured["peak"]["drawdown_pct"] if measured else None
    return out


def main():
    a = json.loads(ASSUMPTIONS_PATH.read_text())
    out = run(a)
    history = store.load(HISTORY_PATH)["points"]
    if history:
        attach_drawdowns(out, a, history[-1])
    store.atomic_write(OUT_PATH, out)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
