import sys
from unittest import mock

sys.path.insert(0, "scripts")
import fetch_crypto


def test_main_appends(tmp_path):
    payload = {"bitcoin": {"rub": 9500000, "usd": 121000}}
    r = mock.Mock()
    r.json = mock.Mock(return_value=payload)
    r.raise_for_status = mock.Mock()
    with mock.patch("fetch_crypto.requests.get", return_value=r), \
         mock.patch("fetch_crypto.DATA_PATH", tmp_path / "crypto.json"):
        assert fetch_crypto.main() is True
