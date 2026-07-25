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


def test_nominal_not_inflation_adjusted():
    """Every asset with a positive rate must grow in the numbers we display."""
    out = model.run(A)
    for name in ("deposit", "ofz", "tmos", "gold", "usd"):
        s = out["assets"][name]["series"]
        assert s[10] > s[0], name


def test_property_pays_entry_cost_then_grows_net_of_upkeep():
    out = model.run(A)
    s = out["assets"]["buy_now_house"]["series"]
    assert s[0] == round(10_000_000 * (1 - A["transaction_cost_rate"]))
    net = A["assets"]["buy_now_house"]["rate"] - (
        A["house_maintenance_rate"] + A["property_tax_rate"])
    assert abs(s[1] - s[0] * (1 + net)) <= 1


def test_compound_asset_matches_its_rate():
    out = model.run(A)
    rate = A["assets"]["gold"]["rate"]
    assert abs(out["assets"]["gold"]["series"][5] - 10_000_000 * (1 + rate) ** 5) <= 1


def test_avg_rate_reports_delivered_growth():
    out = model.run(A)
    gold = out["assets"]["gold"]
    assert abs(gold["avg_rate"] - A["assets"]["gold"]["rate"]) < 0.001
    # the deposit rate glides down, so its average must sit below today's rate
    assert out["assets"]["deposit"]["avg_rate"] < A["deposit"]["rate_start"]


def test_inflation_line_tracks_inflation():
    out = model.run(A)
    assert out["inflation_line"][0] == 10_000_000
    assert abs(out["inflation_line"][10] - 10_000_000 * (1 + A["inflation"]) ** 10) <= 1


def test_verdict_present_and_consistent():
    out = model.run(A)
    v = out["verdict"]
    assert v["light"] in ("green", "yellow", "red")
    assert v["reason_ru"]
    assert abs(v["numbers"]["ratio"]
               - v["numbers"]["deposit_y3"] / v["numbers"]["buy_house_y3"]) < 0.01


def test_zero_rates_leave_capital_flat():
    a = json.loads(json.dumps(A))
    a["assets"]["gold"]["rate"] = 0.0
    assert model.run(a)["assets"]["gold"]["series"] == [10_000_000] * 11


def test_rate_label_passthrough_and_default():
    out = model.run(A)
    assert out["assets"]["ofz"]["rate_label_ru"] == A["assets"]["ofz"]["rate_label_ru"]
    # assets whose rate is flat and gross need no override
    assert out["assets"]["gold"]["rate_label_ru"] is None


def test_ofz_beats_deposit_at_every_horizon():
    """A locked 13% must not be shown trailing a deposit that starts at 12.9%
    and decays — that inversion was a real reader-reported defect."""
    out = model.run(A)
    ofz, dep = out["assets"]["ofz"]["series"], out["assets"]["deposit"]["series"]
    assert all(o >= d for o, d in zip(ofz[1:], dep[1:]))
