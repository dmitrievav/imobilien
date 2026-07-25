"""MOEX ISS: TMOS, TPAY closes and RGBITR index."""
import sys
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import store

DATA_PATH = Path("data/moex.json")
TIMEOUT = 30
PRICE_FIELDS = ["LAST", "MARKETPRICE", "CURRENTVALUE", "LASTVALUE"]


def _cell(block, field):
    cols = block["columns"]
    return block["data"][0][cols.index(field)] if field in cols and block["data"] else None


def last_price(secid, market="shares", board="TQBR"):
    url = (f"https://iss.moex.com/iss/engines/stock/markets/{market}/boards/{board}"
           f"/securities/{secid}.json?iss.only=securities,marketdata&iss.meta=off")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    j = r.json()
    for f in PRICE_FIELDS:
        v = _cell(j["marketdata"], f)
        if v:
            return float(v)
    v = _cell(j["securities"], "PREVPRICE")
    if v:
        return float(v)
    raise ValueError(f"no price for {secid}")


def main():
    point = {"date": date.today().isoformat(),
             "tmos": last_price("TMOS"),
             "tpay": last_price("TPAY")}
    try:
        point["rgbitr"] = last_price("RGBITR", market="index", board="SNDX")
    except Exception:
        point["rgbitr"] = None
    return store.append_point(DATA_PATH, point, ["date", "tmos", "tpay"])


if __name__ == "__main__":
    print("moex:", "appended" if main() else "already have today")
