"""Measured long-run behaviour of the assets we compare.

Answers three questions the model cannot answer by itself:
  * what did each asset actually return, over IDENTICAL windows (comparing a
    20-year gold number against a 23-year stock number is meaningless);
  * how far is each asset from its own all-time high right now (a cheap
    read on "overbought / oversold");
  * therefore, which of our forward assumptions are defensible.

Sources: CBR (USD, gold) and MOEX ISS (MCFTR = MOEX total return incl.
dividends, RGBITR = OFZ total return). Both public, no auth.
"""
import sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import store

DATA_PATH = Path("data/history.json")
TIMEOUT = 60
WINDOWS = [5, 10, 15, 20]
PAGE = 100
USD_URL = ("https://www.cbr.ru/scripts/XML_dynamic.asp"
           "?date_req1={start}&date_req2={end}&VAL_NM_RQ=R01235")
GOLD_URL = "https://www.cbr.ru/scripts/xml_metall.asp?date_req1={start}&date_req2={end}"
MOEX_URL = ("https://iss.moex.com/iss/history/engines/stock/markets/index"
            "/securities/{secid}.json?from={start}&till={end}&iss.meta=off"
            "&iss.only=history&history.columns=TRADEDATE,CLOSE&start={offset}")


# On 1998-01-01 the ruble was redenominated 1000:1 (USD 30.12.1997 = 5960 old
# rubles, 01.01.1998 = 5.96 new). CBR serves both eras raw, so an unadjusted
# series makes 1997 look like an all-time high a thousand times over.
DENOMINATION_DATE = date(1998, 1, 1)
DENOMINATION_FACTOR = 1000


def _num(s):
    return float(s.replace(",", "."))


def denominate(point):
    """Restate a pre-1998 CBR value in today's rubles."""
    d, v = point
    return (d, v / DENOMINATION_FACTOR) if d < DENOMINATION_DATE else (d, v)


def _date(s):
    dd, mm, yy = s.split(".")
    return date(int(yy), int(mm), int(dd))


def _get(url):
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def usd_series(start, end):
    root = ET.fromstring(_get(USD_URL.format(start=f"{start:%d/%m/%Y}",
                                             end=f"{end:%d/%m/%Y}")).content)
    return sorted(denominate((_date(r.get("Date")),
                              _num(r.findtext("VunitRate") or r.findtext("Value"))))
                  for r in root.iter("Record"))


def gold_series(start, end):
    root = ET.fromstring(_get(GOLD_URL.format(start=f"{start:%d/%m/%Y}",
                                              end=f"{end:%d/%m/%Y}")).content)
    return sorted(denominate((_date(r.get("Date")), _num(r.findtext("Sell"))))
                  for r in root.iter("Record") if r.get("Code") == "1")


def moex_series(secid, start, end):
    """ISS pages 100 rows at a time; walk until a page comes back short."""
    out, offset = [], 0
    while True:
        rows = _get(MOEX_URL.format(secid=secid, start=start, end=end,
                                    offset=offset)).json()["history"]["data"]
        out += [(date.fromisoformat(d), float(c)) for d, c in rows if c]
        if len(rows) < PAGE:
            return sorted(out)
        offset += PAGE


def cagr(series, years):
    """Annualised growth over the window ending at the last point."""
    end_d, end_v = series[-1]
    target = date(end_d.year - years, end_d.month, min(end_d.day, 28))
    start_d, start_v = min(series, key=lambda p: abs((p[0] - target).days))
    span = (end_d - start_d).days / 365.25
    if span <= 0 or start_v <= 0:
        raise ValueError(f"cannot annualise over {span:.2f} years from {start_v}")
    return {"years": years, "from": start_d.isoformat(), "from_value": round(start_v, 2),
            "to_value": round(end_v, 2),
            "cagr_pct": round(((end_v / start_v) ** (1 / span) - 1) * 100, 2)}


def peak(series):
    """All-time high in the series and how far below it we are now."""
    ath_d, ath_v = max(series, key=lambda p: p[1])
    _, now_v = series[-1]
    return {"ath_date": ath_d.isoformat(), "ath_value": round(ath_v, 2),
            "now_value": round(now_v, 2),
            "drawdown_pct": round((now_v / ath_v - 1) * 100, 2)}


def summarise(series, windows=WINDOWS):
    span = (series[-1][0] - series[0][0]).days / 365.25
    return {"first": series[0][0].isoformat(), "span_years": round(span, 1),
            "cagr": [cagr(series, y) for y in windows if span >= y],
            "peak": peak(series)}


def cagr_from(series, start):
    """Growth from a fixed calendar date — used for the longest window that
    ALL assets share. Fixed-length windows are only comparable if every asset
    has data for them; this is how we find the longest one that qualifies."""
    end_d, end_v = series[-1]
    # First point AT OR AFTER the date, never before it: measuring an asset
    # from earlier than the shared start is exactly the window mismatch this
    # function exists to prevent.
    later = [p for p in series if p[0] >= start]
    start_d, start_v = later[0] if later else series[-1]
    span = (end_d - start_d).days / 365.25
    if span <= 0 or start_v <= 0:
        raise ValueError(f"cannot annualise over {span:.2f} years from {start_v}")
    return {"from": start_d.isoformat(), "span_years": round(span, 1),
            "from_value": round(start_v, 2), "to_value": round(end_v, 2),
            "cagr_pct": round(((end_v / start_v) ** (1 / span) - 1) * 100, 2)}


def common_window(series_by_name):
    """Longest window every asset covers: starts where the youngest series does."""
    start = max(s[0][0] for s in series_by_name.values())
    return start, {name: cagr_from(s, start) for name, s in series_by_name.items()}


def main():
    end = date.today()
    # Reach for everything the sources hold; the MOEX indices (2003) end up
    # setting the comparable window, and the pre-1998 ruble redenomination
    # plus 1990s hyperinflation make deeper history uncomparable anyway.
    start = date(1997, 1, 1)
    iso = (f"{start:%Y-%m-%d}", f"{end:%Y-%m-%d}")
    series = {"usd": usd_series(start, end),
              "gold_rub_g": gold_series(start, end),
              "stocks_mcftr": moex_series("MCFTR", *iso),
              "bonds_rgbitr": moex_series("RGBITR", *iso)}
    common_start, common = common_window(series)
    point = {"date": end.isoformat(),
             "source": "cbr.ru (USD R01235, gold Code=1) and iss.moex.com history "
                       "(MCFTR = MOEX total return incl. dividends, RGBITR = OFZ total return)",
             "note": "nominal RUB; identical windows across assets so the numbers compare",
             "common_window": {"from": common_start.isoformat(),
                               "span_years": common[next(iter(common))]["span_years"],
                               "limited_by": "MOEX indices start in 2003",
                               "assets": common},
             **{name: summarise(s) for name, s in series.items()}}
    return store.append_point(DATA_PATH, point, ["date", "usd", "gold_rub_g"])


if __name__ == "__main__":
    print("history:", "appended" if main() else "already have today")
