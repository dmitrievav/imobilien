import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, "scripts")
import fetch_history


def _series(years, start_value, end_value):
    """Two-point series spanning exactly `years` back from today."""
    end = date.today()
    start = end - timedelta(days=round(years * 365.25))
    return [(start, start_value), (end, end_value)]


def test_cagr_doubling_over_ten_years():
    r = fetch_history.cagr(_series(10, 100.0, 200.0), 10)
    assert r["years"] == 10
    assert abs(r["cagr_pct"] - 7.18) < 0.05  # 2**(1/10) - 1


def test_cagr_flat_is_zero():
    assert fetch_history.cagr(_series(5, 50.0, 50.0), 5)["cagr_pct"] == 0.0


def test_cagr_decline_is_negative():
    assert fetch_history.cagr(_series(5, 100.0, 50.0), 5)["cagr_pct"] < 0


def test_cagr_rejects_zero_start_value():
    with pytest.raises(ValueError):
        fetch_history.cagr(_series(5, 0.0, 100.0), 5)


def test_peak_reports_ath_and_drawdown():
    end = date.today()
    series = [(end - timedelta(days=800), 100.0),
              (end - timedelta(days=400), 200.0),
              (end, 150.0)]
    p = fetch_history.peak(series)
    assert p["ath_value"] == 200.0
    assert p["ath_date"] == (end - timedelta(days=400)).isoformat()
    assert p["drawdown_pct"] == -25.0


def test_peak_at_ath_has_zero_drawdown():
    end = date.today()
    assert fetch_history.peak([(end - timedelta(days=100), 5.0), (end, 9.0)])["drawdown_pct"] == 0.0


def test_summarise_reports_span_and_peak():
    out = fetch_history.summarise(_series(6, 100.0, 150.0))
    assert out["span_years"] == 6.0
    assert [w["years"] for w in out["cagr"]] == [5]
    assert out["peak"]["ath_value"] == 150.0
