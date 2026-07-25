import sys
from unittest import mock

sys.path.insert(0, "scripts")
import fetch_cbr

FX_XML = b"""<?xml version="1.0" encoding="UTF-8"?><ValCurs Date="25.07.2026">
<Valute ID="R01235"><CharCode>USD</CharCode><VunitRate>78,50</VunitRate></Valute>
<Valute ID="R01239"><CharCode>EUR</CharCode><VunitRate>91,20</VunitRate></Valute></ValCurs>"""

METALL_XML = b"""<?xml version="1.0" encoding="UTF-8"?><Metall>
<Record Date="24.07.2026" Code="1"><Buy>10100,5</Buy><Sell>10100,5</Sell></Record>
<Record Date="25.07.2026" Code="1"><Buy>10200,0</Buy><Sell>10200,0</Sell></Record>
<Record Date="25.07.2026" Code="2"><Buy>110,0</Buy><Sell>110,0</Sell></Record></Metall>"""

KEYRATE_HTML = b'<table><tr><td>25.07.2026</td><td>14,00</td></tr></table>'


def _resp(content):
    r = mock.Mock()
    r.content = content
    r.raise_for_status = mock.Mock()
    return r


def test_fetch_fx():
    with mock.patch("fetch_cbr.requests.get", return_value=_resp(FX_XML)):
        assert fetch_cbr.fetch_fx() == {"usd": 78.5, "eur": 91.2}


def test_fetch_gold_takes_last_code1():
    with mock.patch("fetch_cbr.requests.get", return_value=_resp(METALL_XML)):
        assert fetch_cbr.fetch_gold() == 10200.0


def test_fetch_key_rate():
    with mock.patch("fetch_cbr.requests.get", return_value=_resp(KEYRATE_HTML)):
        assert fetch_cbr.fetch_key_rate() == 14.0


def test_main_appends(tmp_path):
    with mock.patch("fetch_cbr.requests.get", return_value=_resp(FX_XML)), \
         mock.patch("fetch_cbr.fetch_gold", return_value=None), \
         mock.patch("fetch_cbr.fetch_key_rate", return_value=14.0), \
         mock.patch("fetch_cbr.DATA_PATH", tmp_path / "cbr.json"):
        assert fetch_cbr.main() is True
