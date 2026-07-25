import sys

from PIL import Image

sys.path.insert(0, "scripts")
import add_listing
import crypto_util


def test_next_id():
    assert add_listing.next_id({"listings": []}) == "L001"
    assert add_listing.next_id({"listings": [{"id": "L001"}, {"id": "L007"}]}) == "L008"


def test_process_photos(tmp_path, monkeypatch):
    monkeypatch.setattr(add_listing, "PHOTOS_LOCAL", tmp_path / "local")
    monkeypatch.setattr(add_listing, "PHOTOS_SITE", tmp_path / "site")
    src = tmp_path / "big.png"
    Image.new("RGB", (3200, 2400), "red").save(src)
    salt = b"0123456789abcdef"
    n = add_listing.process_photos("L001", [str(src)], "phrase", salt)
    assert n == 1
    jpg = tmp_path / "local" / "L001-1.jpg"
    assert Image.open(jpg).width <= 1600
    enc = (tmp_path / "site" / "L001-1.enc").read_bytes()
    assert crypto_util.decrypt(enc, "phrase", salt) == jpg.read_bytes()
