"""CoinGecko: BTC in RUB and USD."""
import sys
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import store

DATA_PATH = Path("data/crypto.json")
URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=rub,usd"


def main():
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    btc = r.json()["bitcoin"]
    point = {"date": date.today().isoformat(),
             "btc_rub": float(btc["rub"]), "btc_usd": float(btc["usd"])}
    return store.append_point(DATA_PATH, point, ["date", "btc_rub", "btc_usd"])


if __name__ == "__main__":
    print("crypto:", "appended" if main() else "already have today")
