import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")
import valuation

CFG = valuation.load_factors()
BENCH = {"flat": {"price_per_m2": 160000, "estimated": False},
         "year-round house": {"price_per_m2": 100000, "estimated": True}}


def flat(**over):
    base = {"id": "T1", "segment": "flat", "price_rub": 12_000_000, "flat_m2": 60,
            "floor": "5/9", "year_built": 2000, "wall_material": "brick",
            "renovation": "euro"}
    base.update(over)
    return base


def house(**over):
    base = {"id": "H1", "segment": "year-round house", "price_rub": 20_000_000,
            "house_m2": 200, "land_sotki": 10, "land_category": "IZhS",
            "year_built": 2015, "wall_material": "timber (brus)", "mkad_km": 30,
            "renovation": "euro",
            "utilities": {"heating": "gas", "water": "central", "sewage": "central"}}
    base.update(over)
    return base


def test_floor_kind_reads_the_slash_notation():
    assert valuation._floor_kind("1/9") == "first"
    assert valuation._floor_kind("9/9") == "last"
    assert valuation._floor_kind("4/18") == "middle"
    assert valuation._floor_kind(None) is None
    assert valuation._floor_kind("партер") is None


def test_renovation_read_from_extras_when_not_explicit():
    assert valuation.renovation_of({"extras": ["designer renovation"]}) == "designer"
    assert valuation.renovation_of({"extras": ["quality renovation"]}) == "euro"
    assert valuation.renovation_of({"extras": ["two loggias"]}) is None
    assert valuation.renovation_of({"renovation": "none", "extras": ["designer"]}) == "none"


def test_first_floor_is_penalised_relative_to_middle():
    mid = valuation.estimate(flat(floor="5/9"), BENCH, CFG)["fair"]
    first = valuation.estimate(flat(floor="1/9"), BENCH, CFG)["fair"]
    assert first < mid


def test_gas_dominates_a_house_valuation():
    with_gas = valuation.estimate(house(), BENCH, CFG)["fair"]
    without = valuation.estimate(
        house(utilities={"heating": "electric", "water": "central", "sewage": "central"}),
        BENCH, CFG)["fair"]
    assert with_gas > without * 1.25   # +15% vs -15% is a ~35% spread


def test_comparables_damp_the_adjustments():
    """Nearby comparables already embed typical quality, so corrections on top
    must be halved — otherwise renovation gets counted twice."""
    no_comps = valuation.estimate(flat(), BENCH, CFG)
    with_comps = valuation.estimate(flat(comparables_per_m2=[160000, 160000]), BENCH, CFG)
    assert no_comps["adjustment_weight"] == 1.0
    assert with_comps["adjustment_weight"] == 0.5
    # same base, so the damped estimate sits closer to the raw base
    assert abs(with_comps["per_m2"] - 160000) < abs(no_comps["per_m2"] - 160000)


def test_estimated_base_widens_the_band_a_lot():
    """A verdict must not look confident when it rests on a guessed benchmark."""
    h = valuation.estimate(house(), BENCH, CFG)          # house base is estimated
    f = valuation.estimate(flat(comparables_per_m2=[160000]), BENCH, CFG)
    assert h["band_pct"] > f["band_pct"] + 0.1


def test_missing_fields_widen_the_band():
    full = valuation.estimate(flat(comparables_per_m2=[160000]), BENCH, CFG)
    thin = valuation.estimate(
        {"id": "T2", "segment": "flat", "price_rub": 12_000_000, "flat_m2": 60,
         "comparables_per_m2": [160000]}, BENCH, CFG)
    assert thin["missing_fields"] == 4
    assert thin["band_pct"] > full["band_pct"]


def test_band_never_exceeds_its_cap():
    thin_house = {"id": "H2", "segment": "year-round house",
                  "price_rub": 20_000_000, "house_m2": 200}
    assert valuation.estimate(thin_house, BENCH, CFG)["band_pct"] == CFG["band"]["max_pct"]


def test_verdict_follows_the_range():
    l = flat(comparables_per_m2=[160000])
    fair = valuation.estimate(l, BENCH, CFG)
    assert valuation.estimate({**l, "price_rub": fair["fair"]}, BENCH, CFG)["verdict"] == "inside"
    assert valuation.estimate({**l, "price_rub": round(fair["high"] * 1.2)},
                              BENCH, CFG)["verdict"] == "above"
    assert valuation.estimate({**l, "price_rub": round(fair["low"] * 0.8)},
                              BENCH, CFG)["verdict"] == "below"


def test_adjustments_carry_their_reasoning():
    out = valuation.estimate(house(), BENCH, CFG)
    names = [a["name_ru"] for a in out["adjustments"]]
    assert "Газ" in names and "Удалённость" in names
    for a in out["adjustments"]:
        assert a["why_ru"] and isinstance(a["pct"], float)


def test_area_missing_is_an_error_not_a_guess():
    with pytest.raises(ValueError):
        valuation.estimate({"id": "X", "segment": "flat", "price_rub": 1}, BENCH, CFG)


def test_real_journal_listings_all_value_cleanly():
    journal = json.loads(Path("data/listings.json").read_text())
    bench = valuation.latest_benchmarks()
    for l in journal["listings"]:
        out = valuation.estimate(l, bench, CFG)
        assert out["low"] < out["fair"] < out["high"]
        assert out["verdict"] in ("below", "inside", "above")


def test_factor_reasons_are_in_russian_not_source_values():
    """The family reads these rows; 'timber (brus)' is not an explanation."""
    out = valuation.estimate(house(wall_material="timber (brus)",
                                   extras=["banya/sauna", "terrace"]), BENCH, CFG)
    by_name = {a["name_ru"]: a for a in out["adjustments"]}
    assert by_name["Материал стен"]["why_ru"] == "из бруса"
    assert "Баня" in by_name and "Терраса" in by_name
    for a in out["adjustments"]:
        assert not any(ch.isascii() and ch.isalpha() for ch in a["name_ru"])


def test_variation_measures_relative_spread():
    assert valuation.variation([100, 100, 100]) == 0.0
    assert valuation.variation([100]) is None          # needs at least two
    assert valuation.variation([]) is None
    v = valuation.variation([90, 100, 110])
    assert abs(v - 0.1) < 0.001                        # sd 10 on mean 100


def test_heterogeneous_comparables_are_refused_not_averaged():
    """Past the 33% threshold the appraiser refuses the comparative approach;
    so do we, instead of silently averaging unlike things."""
    out = valuation.estimate(flat(comparables_per_m2=[80000, 160000, 320000]), BENCH, CFG)
    assert out["variation_pct"] > CFG["homogeneity"]["refuse_above"]
    assert out["verdict"] == "unreliable"
    assert "нельзя" in out["homogeneity_ru"]


def test_comparable_spread_widens_the_band_beyond_the_floor():
    tight = valuation.estimate(flat(comparables_per_m2=[160000, 161000, 159000]), BENCH, CFG)
    loose = valuation.estimate(flat(comparables_per_m2=[130000, 160000, 190000]), BENCH, CFG)
    assert tight["band_pct"] == CFG["band"]["base_pct"]          # floored at the base
    assert loose["band_pct"] > tight["band_pct"]                 # measured spread dominates
    assert abs(loose["band_pct"] - loose["variation_pct"]) < 0.001


def test_bargaining_discount_gives_a_negotiation_target():
    """Asking prices close below the ad, so the likely deal sits under the
    asking-based estimate — that gap is how far it is worth negotiating."""
    out = valuation.estimate(flat(comparables_per_m2=[160000]), BENCH, CFG)
    assert out["bargaining_coef"] == 0.94                        # flat under 100 m2
    assert out["likely_deal"] == round(out["fair"] * 0.94)
    assert out["likely_deal"] < out["fair"]


def test_bargaining_widens_for_large_flats_and_houses():
    big = valuation.estimate(flat(flat_m2=200, price_rub=40_000_000,
                                  comparables_per_m2=[200000]), BENCH, CFG)
    assert big["bargaining_coef"] == 0.90
    assert valuation.estimate(house(), BENCH, CFG)["bargaining_coef"] == 0.92


def test_area_correction_follows_the_power_law():
    """Not a step function: unit price decelerates as area grows, exponent
    -0.11 from a matched-pair regression."""
    small = valuation.estimate(flat(flat_m2=60), BENCH, CFG)
    big = valuation.estimate(flat(flat_m2=120), BENCH, CFG)
    area_adj = {a["name_ru"]: a["pct"] for a in big["adjustments"]}["Площадь"]
    expected = ((120 / 60) ** -0.11 - 1)
    assert abs(area_adj - expected) < 0.001
    assert small["per_m2"] > big["per_m2"]                       # bigger flat, cheaper metre
