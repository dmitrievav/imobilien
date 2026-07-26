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


def test_drawdowns_attach_only_where_history_exists():
    out = model.run(A)
    history_point = {"stocks_mcftr": {"peak": {"drawdown_pct": -25.1}}}
    model.attach_drawdowns(out, A, history_point)
    assert out["assets"]["tmos"]["drawdown_pct"] == -25.1
    assert out["assets"]["deposit"]["drawdown_pct"] is None   # no series by nature
    assert out["assets"]["gold"]["drawdown_pct"] is None      # key absent from this point


def test_rate_label_passthrough_and_default():
    out = model.run(A)
    assert out["assets"]["ofz"]["rate_label_ru"] == A["assets"]["ofz"]["rate_label_ru"]
    assert out["assets"]["gold"]["rate_label_ru"] is None
