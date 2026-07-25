# tests/test_fairprice.py
import sys

sys.path.insert(0, "scripts")
import fairprice

BENCH = {"flat": 160000, "year-round house": 100000}


def _flat(price, m2=80, comps=None):
    l = {"id": "T1", "segment": "flat", "price_rub": price, "flat_m2": m2}
    if comps:
        l["comparables_per_m2"] = comps
    return l


def test_fair_within_10pct():
    a = fairprice.assess(_flat(12_800_000), BENCH)  # exactly 160k/m2
    assert a["verdict"] == "fair"


def test_overpriced_above_10pct():
    assert fairprice.assess(_flat(15_000_000), BENCH)["verdict"] == "overpriced"


def test_below_market():
    assert fairprice.assess(_flat(11_000_000), BENCH)["verdict"] == "below market"


def test_comparables_override_benchmark():
    a = fairprice.assess(_flat(12_000_000, comps=[150000, 152000, 148000]), BENCH)
    assert a["fair_per_m2"] == 150000  # median of comps, not segment benchmark


def test_house_uses_house_m2():
    h = {"id": "T2", "segment": "year-round house", "price_rub": 23_400_000, "house_m2": 234}
    assert fairprice.assess(h, BENCH)["price_per_m2"] == 100000


def test_reprice_flag():
    l = _flat(33_500_000)
    l["price_history"] = [{"date": "2026-07-11", "price_rub": 15_500_000},
                          {"date": "2026-07-25", "price_rub": 33_500_000}]
    assert fairprice.assess(l, BENCH)["reprice_flag"] is True


def test_no_reprice_flag_small_change():
    l = _flat(12_000_000)
    l["price_history"] = [{"date": "2026-07-01", "price_rub": 12_500_000},
                          {"date": "2026-07-25", "price_rub": 12_000_000}]
    assert fairprice.assess(l, BENCH)["reprice_flag"] is False


def test_note_fair_price():
    a = fairprice.assess(_flat(12_800_000), BENCH)  # exactly 160k/m2, ratio = 1.0
    assert "+0% vs fair" in a["note"]


def test_note_overpriced():
    a = fairprice.assess(_flat(15_000_000), BENCH)  # 187.5k/m2, ratio ≈ 1.172
    assert "+17% vs fair" in a["note"]
