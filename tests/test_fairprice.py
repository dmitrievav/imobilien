# tests/test_fairprice.py
import sys

sys.path.insert(0, "scripts")
import fairprice

BENCH = {"flat": {"price_per_m2": 160000, "estimated": False},
         "year-round house": {"price_per_m2": 100000, "estimated": True}}


def _flat(price, m2=80, **over):
    l = {"id": "T1", "segment": "flat", "price_rub": price, "flat_m2": m2,
         "floor": "5/9", "year_built": 2000, "wall_material": "brick",
         "renovation": "euro", "comparables_per_m2": [160000, 160000, 160000]}
    l.update(over)
    return l


def test_reprice_flag_on_a_large_jump():
    l = _flat(33_500_000, price_history=[{"date": "2026-07-11", "price_rub": 15_500_000},
                                         {"date": "2026-07-25", "price_rub": 33_500_000}])
    assert fairprice.reprice_flag(l) is True


def test_no_reprice_flag_on_a_small_move():
    l = _flat(12_000_000, price_history=[{"date": "2026-07-01", "price_rub": 12_500_000},
                                         {"date": "2026-07-25", "price_rub": 12_000_000}])
    assert fairprice.reprice_flag(l) is False


def test_no_history_means_no_flag():
    assert fairprice.reprice_flag(_flat(12_000_000)) is False


def test_reprice_flag_is_independent_of_value():
    """A fairly priced listing can still have a suspicious history, and the
    assessment must report both facts separately."""
    l = _flat(13_000_000, price_history=[{"date": "2026-01-01", "price_rub": 6_000_000},
                                         {"date": "2026-07-01", "price_rub": 13_000_000}])
    out = fairprice.assess(l, BENCH)
    assert out["verdict"] == "inside"
    assert out["reprice_flag"] is True


def test_assess_carries_the_valuation_range_and_reasoning():
    out = fairprice.assess(_flat(12_800_000), BENCH)
    assert out["low"] < out["fair"] < out["high"]
    assert out["adjustments"] and out["base_why_ru"]
    assert out["verdict"] in ("below", "inside", "above")
