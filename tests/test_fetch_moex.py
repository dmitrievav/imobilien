import sys
from unittest import mock

sys.path.insert(0, "scripts")
import fetch_moex

PAYLOAD = {
    "securities": {"columns": ["SECID", "PREVPRICE"], "data": [["TMOS", 7.10]]},
    "marketdata": {"columns": ["SECID", "LAST", "MARKETPRICE"], "data": [["TMOS", 7.25, 7.20]]},
}
PAYLOAD_NO_LAST = {
    "securities": {"columns": ["SECID", "PREVPRICE"], "data": [["TMOS", 7.10]]},
    "marketdata": {"columns": ["SECID", "LAST", "MARKETPRICE"], "data": [["TMOS", None, None]]},
}


def _resp(payload):
    r = mock.Mock()
    r.json = mock.Mock(return_value=payload)
    r.raise_for_status = mock.Mock()
    return r


def test_last_price_prefers_last():
    with mock.patch("fetch_moex.requests.get", return_value=_resp(PAYLOAD)):
        assert fetch_moex.last_price("TMOS") == 7.25


def test_default_board_is_tqbr():
    """TQBR is where TMOS/TPAY actually trade; the plan guessed wrong and only a
    live check caught it. Pin the default so a refactor cannot re-break it."""
    with mock.patch("fetch_moex.requests.get", return_value=_resp(PAYLOAD)) as get:
        fetch_moex.last_price("TMOS")
    url = get.call_args.args[0]
    assert "/markets/shares/boards/TQBR/" in url
    assert "/securities/TMOS.json" in url


def test_index_board_is_overridable():
    with mock.patch("fetch_moex.requests.get", return_value=_resp(PAYLOAD)) as get:
        fetch_moex.last_price("RGBITR", market="index", board="SNDX")
    assert "/markets/index/boards/SNDX/" in get.call_args.args[0]


def test_last_price_falls_back_to_prevprice():
    with mock.patch("fetch_moex.requests.get", return_value=_resp(PAYLOAD_NO_LAST)):
        assert fetch_moex.last_price("TMOS") == 7.10


def test_main_appends(tmp_path):
    with mock.patch("fetch_moex.last_price", side_effect=[7.25, 102.0, 620.0]), \
         mock.patch("fetch_moex.DATA_PATH", tmp_path / "moex.json"):
        assert fetch_moex.main() is True
