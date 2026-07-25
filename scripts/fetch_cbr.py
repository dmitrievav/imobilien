"""CBR: USD/EUR official rates, gold accounting price, key rate."""
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import store

DATA_PATH = Path("data/cbr.json")
TIMEOUT = 30


def _num(s):
    return float(s.replace(",", "."))


def fetch_fx():
    r = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=TIMEOUT)
    r.raise_for_status()
    out = {}
    for v in ET.fromstring(r.content).iter("Valute"):
        code = v.findtext("CharCode")
        if code in ("USD", "EUR"):
            out[code.lower()] = _num(v.findtext("VunitRate"))
    if set(out) != {"usd", "eur"}:
        raise ValueError(f"unexpected FX payload: {out}")
    return out


def fetch_gold():
    d2, d1 = date.today(), date.today() - timedelta(days=14)
    url = ("https://www.cbr.ru/scripts/xml_metall.asp"
           f"?date_req1={d1:%d/%m/%Y}&date_req2={d2:%d/%m/%Y}")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    gold = [rec for rec in ET.fromstring(r.content).iter("Record")
            if rec.get("Code") == "1"]
    return _num(gold[-1].findtext("Sell")) if gold else None


def fetch_key_rate():
    r = requests.get("https://www.cbr.ru/hd_base/KeyRate/", timeout=TIMEOUT)
    r.raise_for_status()
    m = re.search(r"<td>\d{2}\.\d{2}\.\d{4}</td>\s*<td>([\d,\.]+)</td>",
                  r.content.decode("utf-8", "ignore"))
    return _num(m.group(1)) if m else None


def main():
    fx = fetch_fx()
    point = {"date": date.today().isoformat(), **fx}
    try:
        point["gold_rub_g"] = fetch_gold()
    except Exception:
        point["gold_rub_g"] = None
    try:
        point["key_rate"] = fetch_key_rate()
    except Exception:
        point["key_rate"] = None
    return store.append_point(DATA_PATH, point, ["date", "usd", "eur"])


if __name__ == "__main__":
    print("cbr:", "appended" if main() else "already have today")
