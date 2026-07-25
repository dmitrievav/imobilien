import json, sys
from pathlib import Path

sys.path.insert(0, "scripts")
import model

A = json.loads(Path("data/assumptions.json").read_text())


def test_shapes():
    out = model.run(A)
    assert out["capital_levels"] == [10_000_000, 17_500_000, 25_000_000]
    s = out["scenarios"]["deposit"]["17500000"]
    assert set(s) == {"pess", "base", "opt"} and all(len(v) == 11 for v in s.values())


def test_year_zero_costs():
    out = model.run(A)
    # buy_now starts capital minus transaction costs; deposit starts at full capital
    assert out["scenarios"]["buy_now_house"]["10000000"]["base"][0] == 10_000_000 * 0.97
    assert out["scenarios"]["deposit"]["10000000"]["base"][0] == 10_000_000


def test_real_adjustment():
    # zero growth, zero costs => real value must shrink by exactly inflation
    a = json.loads(json.dumps(A))
    a["growth"]["house"] = {"pess": 0.0, "base": 0.0, "opt": 0.0}
    a["house_maintenance_rate"] = a["property_tax_rate"] = a["transaction_cost_rate"] = 0.0
    out = model.run(a)
    v = out["scenarios"]["buy_now_house"]["10000000"]["base"]
    assert abs(v[1] - 10_000_000 / 1.07) < 1


def test_paths_ordered():
    out = model.run(A)
    for name, caps in out["scenarios"].items():
        for series in caps.values():
            assert series["pess"][5] <= series["base"][5] <= series["opt"][5], name


def test_verdict_present():
    out = model.run(A)
    assert out["verdict"]["light"] in ("green", "yellow", "red")
    assert out["verdict"]["reason_ru"]
