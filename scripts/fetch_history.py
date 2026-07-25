"""Long-run nominal CAGR for USD/RUB and gold from CBR history.

The forward-looking bands in data/assumptions.json used to be guesses. This
script measures what these assets actually did over 5/10/15/20 years, so the
assumptions can be argued with instead of invented.
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
USD_URL = ("https://www.cbr.ru/scripts/XML_dynamic.asp"
           "?date_req1={start}&date_req2={end}&VAL_NM_RQ=R01235")
GOLD_URL = ("https://www.cbr.ru/scripts/xml_metall.asp"
            "?date_req1={start}&date_req2={end}")


def _num(s):
    return float(s.replace(",", "."))


def _date(s):
    dd, mm, yy = s.split(".")
    return date(int(yy), int(mm), int(dd))


def _fetch(url):
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return ET.fromstring(r.content)


def usd_series(start, end):
    root = _fetch(USD_URL.format(start=f"{start:%d/%m/%Y}", end=f"{end:%d/%m/%Y}"))
    return sorted((_date(r.get("Date")), _num(r.findtext("VunitRate") or r.findtext("Value")))
                  for r in root.iter("Record"))


def gold_series(start, end):
    root = _fetch(GOLD_URL.format(start=f"{start:%d/%m/%Y}", end=f"{end:%d/%m/%Y}"))
    return sorted((_date(r.get("Date")), _num(r.findtext("Sell")))
                  for r in root.iter("Record") if r.get("Code") == "1")


def cagr(series, years):
    """Annualised growth over the window ending at the last point."""
    end_d, end_v = series[-1]
    target = date(end_d.year - years, end_d.month, min(end_d.day, 28))
    start_d, start_v = min(series, key=lambda p: abs((p[0] - target).days))
    span = (end_d - start_d).days / 365.25
    if span <= 0 or start_v <= 0:
        raise ValueError(f"cannot annualise over {span:.2f} years from {start_v}")
    return {"years": years, "from": start_d.isoformat(), "from_value": start_v,
            "to_value": end_v, "cagr_pct": round(((end_v / start_v) ** (1 / span) - 1) * 100, 2)}


def summarise(series, windows=WINDOWS):
    return [cagr(series, y) for y in windows if (series[-1][0] - series[0][0]).days / 365.25 >= y]


def main():
    end = date.today()
    start = date(end.year - max(WINDOWS) - 1, 1, 1)
    point = {"date": end.isoformat(),
             "source": "cbr.ru XML_dynamic (USD R01235) and xml_metall (gold, Code=1)",
             "note": "nominal CAGR in RUB; compare against inflation to judge real return",
             "usd": summarise(usd_series(start, end)),
             "gold_rub_g": summarise(gold_series(start, end))}
    return store.append_point(DATA_PATH, point, ["date", "usd", "gold_rub_g"])


if __name__ == "__main__":
    print("history:", "appended" if main() else "already have today")
