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


def test_common_window_starts_at_the_youngest_series():
    """Real series are daily, so both assets have a point at the shared start;
    the older one must be cut back to it rather than measured from its own."""
    end = date.today()
    old = [(end - timedelta(days=365 * 20), 100.0),
           (end - timedelta(days=365 * 10), 150.0), (end, 200.0)]
    young = [(end - timedelta(days=365 * 10), 50.0), (end, 100.0)]
    start, res = fetch_history.common_window({"old": old, "young": young})
    assert start == young[0][0]
    # both measured from the same date, so both must report the same span
    assert res["old"]["span_years"] == res["young"]["span_years"] == 10.0
    assert res["old"]["from_value"] == 150.0  # not 100.0 from its own start


def test_cagr_from_measures_from_the_given_date():
    end = date.today()
    s = [(end - timedelta(days=365 * 10), 1.0),
         (end - timedelta(days=365 * 5), 2.0), (end, 4.0)]
    r = fetch_history.cagr_from(s, end - timedelta(days=365 * 5))
    assert abs(r["cagr_pct"] - 14.87) < 0.1  # doubling over 5 years


def test_denominate_rescales_only_pre_1998():
    from datetime import date as _d
    assert fetch_history.denominate((_d(1997, 12, 30), 5960.0)) == (_d(1997, 12, 30), 5.96)
    assert fetch_history.denominate((_d(1998, 1, 1), 5.96)) == (_d(1998, 1, 1), 5.96)
    assert fetch_history.denominate((_d(2026, 7, 24), 78.03)) == (_d(2026, 7, 24), 78.03)


def test_peak_ignores_pre_denomination_scale():
    """Without the 1000:1 fix a 1997 price looks like an unbeatable all-time
    high and every asset shows a ~99% drawdown."""
    from datetime import date as _d
    raw = [(_d(1997, 3, 25), 65082.0), (_d(2026, 3, 19), 13407.69), (_d(2026, 7, 24), 10147.63)]
    p = fetch_history.peak([fetch_history.denominate(x) for x in raw])
    assert p["ath_date"] == "2026-03-19"
    assert abs(p["drawdown_pct"] + 24.3) < 0.1


def test_moving_average_smooths_and_keeps_length():
    end = date.today()
    s = [(end - timedelta(days=n), float(10 + (n % 2) * 10)) for n in range(9, -1, -1)]
    ma = fetch_history.moving_average(s, window=4)
    assert len(ma) == len(s)
    assert ma[0][1] == s[0][1]                      # first point averages itself
    assert abs(ma[-1][1] - 15.0) < 1e-9             # 10/20 alternating -> 15


def test_ma_position_reports_distance_from_its_average():
    end = date.today()
    s = [(end - timedelta(days=3), 100.0), (end - timedelta(days=2), 100.0),
         (end - timedelta(days=1), 100.0), (end, 120.0)]
    pos = fetch_history.ma_position(s, window=4)
    assert pos["window"] == 4
    assert pos["price"] == 120.0
    assert pos["ma_value"] == 105.0
    assert abs(pos["above_ma_pct"] - 14.29) < 0.01


def test_ma_position_needs_two_points():
    assert fetch_history.ma_position([(date.today(), 1.0)]) is None


def test_smoothing_barely_moves_a_long_run_average():
    """The reason a moving average cannot fix window sensitivity: over a long
    span both endpoints get smoothed and the effect nearly cancels."""
    end = date.today()
    s = [(end - timedelta(days=n), 100.0 * (1.0003 ** (3000 - n)) * (1 + 0.05 * ((n % 7) - 3)))
         for n in range(3000, -1, -1)]
    start = s[0][0] + timedelta(days=100)
    raw = fetch_history.cagr_from(s, start)["cagr_pct"]
    smoothed = fetch_history.cagr_from(fetch_history.moving_average(s), start)["cagr_pct"]
    assert abs(smoothed - raw) < 1.5
