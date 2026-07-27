import json
import sys
from pathlib import Path

sys.path.insert(0, "scripts")
import model

A = json.loads(Path("data/assumptions.json").read_text())


def test_shape():
    out = model.run(A)
    assert out["capital"] == 10_000_000
    assert len(out["inflation_line"]) == 11
    assert set(out["assets"]) == set(A["assets"])
    for name, block in out["assets"].items():
        assert len(block["series"]) == 11, name
        assert block["risk"] in ("низкий", "средний", "высокий"), name
        assert block["basis_ru"], name


def test_world_asset_rate_is_real_plus_inflation():
    """The point of the world basis: a +5.2% real asset must end up 5.2%
    above the inflation line, whatever inflation happens to be."""
    rate = model.nominal_rate(A["assets"]["tmos"], A["inflation"])
    assert abs(rate - ((1.052 * 1.06) - 1)) < 1e-9
    out = model.run(A)
    ratio = out["assets"]["tmos"]["series"][10] / out["inflation_line"][10]
    assert abs(ratio - 1.052 ** 10) < 0.01


def test_local_instrument_keeps_its_stated_rate():
    assert model.nominal_rate(A["assets"]["ofz"], A["inflation"]) == 0.13
    out = model.run(A)
    assert abs(out["assets"]["ofz"]["series"][5] - 10_000_000 * 1.13 ** 5) <= 1


def test_negative_real_rate_falls_behind_prices():
    """Cash dollars lose purchasing power even while the ruble number grows."""
    out = model.run(A)
    usd = out["assets"]["usd"]["series"]
    assert usd[10] > usd[0]
    assert usd[10] < out["inflation_line"][10]


def test_no_property_costs_are_deducted():
    """Realty compounds gross, like every other asset — no upkeep haircut."""
    out = model.run(A)
    rate = model.nominal_rate(A["assets"]["realty"], A["inflation"])
    assert out["assets"]["realty"]["series"][0] == 10_000_000
    assert abs(out["assets"]["realty"]["series"][10] - 10_000_000 * (1 + rate) ** 10) <= 1


def test_deposit_average_sits_below_todays_rate():
    out = model.run(A)
    assert out["assets"]["deposit"]["avg_rate"] < A["deposit"]["rate_start"]


def test_inflation_line_tracks_inflation():
    out = model.run(A)
    assert out["inflation_line"][0] == 10_000_000
    assert abs(out["inflation_line"][10] - 10_000_000 * (1 + A["inflation"]) ** 10) <= 1


def test_measured_position_attaches_only_where_history_exists():
    out = model.run(A)
    history_point = {"stocks_mcftr": {"peak": {"drawdown_pct": -25.1},
                                      "ma": {"window": 200, "above_ma_pct": -12.8}}}
    model.attach_measured_position(out, A, history_point)
    tmos = out["assets"]["tmos"]
    assert tmos["drawdown_pct"] == -25.1
    assert tmos["above_ma_pct"] == -12.8
    assert tmos["ma_window"] == 200
    assert out["assets"]["deposit"]["drawdown_pct"] is None   # no series by nature
    assert out["assets"]["gold"]["above_ma_pct"] is None      # key absent from this point


def test_measured_position_tolerates_a_point_without_ma():
    """Older history points predate the moving average and must not crash."""
    out = model.run(A)
    model.attach_measured_position(out, A, {"stocks_mcftr": {"peak": {"drawdown_pct": -9.0}}})
    assert out["assets"]["tmos"]["drawdown_pct"] == -9.0
    assert out["assets"]["tmos"]["above_ma_pct"] is None


def test_rate_label_passthrough_and_default():
    out = model.run(A)
    assert out["assets"]["ofz"]["rate_label_ru"] == A["assets"]["ofz"]["rate_label_ru"]
    assert out["assets"]["gold"]["rate_label_ru"] is None


def test_world_asset_in_dollars_is_real_plus_us_inflation():
    """The whole point of the dollar view: a world asset must clear US
    inflation abroad exactly as it clears ours at home."""
    out = model.run(A)
    expected = (1 + A["assets"]["tmos"]["real_rate"]) * (1 + A["us_inflation"]) - 1
    assert abs(out["assets"]["tmos"]["avg_rate_usd"] - expected) < 0.001


def test_dollar_view_starts_at_converted_capital():
    out = model.run(A)
    assert out["capital_usd"] == round(A["capital"] / A["usd_rub"])
    for block in out["assets"].values():
        assert abs(block["series_usd"][0] - out["capital_usd"]) <= 1


def test_local_rate_loses_the_inflation_gap_in_dollars():
    """13% in rubles is not 13% for someone counting in dollars."""
    out = model.run(A)
    ofz = out["assets"]["ofz"]
    assert ofz["avg_rate"] == 0.13
    assert ofz["avg_rate_usd"] < ofz["avg_rate"]
    expected = 1.13 / (1 + model.depreciation(A)) - 1
    assert abs(ofz["avg_rate_usd"] - expected) < 0.001


def test_cash_dollars_are_flat_in_dollars():
    """Holding dollars must neither gain nor lose when measured in dollars."""
    out = model.run(A)
    usd = out["assets"]["usd"]["series_usd"]
    assert abs(usd[10] / usd[0] - 1) < 0.01


def test_dollar_inflation_line_uses_us_inflation():
    out = model.run(A)
    line = out["inflation_line_usd"]
    assert abs(line[10] - out["capital_usd"] * (1 + A["us_inflation"]) ** 10) <= 2
