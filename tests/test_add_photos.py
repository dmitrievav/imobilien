import base64
import json
import sys

import pytest
from PIL import Image

sys.path.insert(0, "scripts")
import add_listing
import add_photos
import crypto_util
import fairprice


@pytest.fixture
def journal_env(tmp_path, monkeypatch):
    monkeypatch.setattr(fairprice, "JOURNAL_LOCAL", tmp_path / "listings.json")
    monkeypatch.setattr(fairprice, "JOURNAL_ENC", tmp_path / "listings.enc")
    monkeypatch.setattr(fairprice, "JOURNAL_SITE", tmp_path / "site-listings.enc")
    monkeypatch.setattr(fairprice, "GATE_PATH", tmp_path / "gate.json")
    monkeypatch.setattr(add_listing, "PHOTOS_LOCAL", tmp_path / "photos-local")
    monkeypatch.setattr(add_listing, "PHOTOS_SITE", tmp_path / "photos-site")
    monkeypatch.setenv("IMOBILIEN_KEY", "phrase")
    salt = b"0123456789abcdef"
    (tmp_path / "gate.json").write_text(json.dumps({"salt": base64.b64encode(salt).decode()}))
    journal = {"listings": [{"id": "L001", "label": "тест", "photos": 0}]}
    fairprice.save_journal(journal)
    return tmp_path, salt


def test_unknown_id_exits_with_clear_error(journal_env, tmp_path):
    src = tmp_path / "a.png"
    Image.new("RGB", (10, 10), "red").save(src)
    with pytest.raises(SystemExit, match="L999"):
        add_photos.main(["L999", str(src)])


def test_happy_path_updates_journal_and_encrypts(journal_env, tmp_path):
    _, salt = journal_env
    src = tmp_path / "photo.png"
    Image.new("RGB", (3200, 2400), "blue").save(src)

    add_photos.main(["L001", str(src)])

    journal = json.loads(fairprice.JOURNAL_LOCAL.read_text())
    entry = next(l for l in journal["listings"] if l["id"] == "L001")
    assert entry["photos"] == 1

    jpg = add_listing.PHOTOS_LOCAL / "L001-1.jpg"
    assert jpg.exists()
    enc = add_listing.PHOTOS_SITE / "L001-1.enc"
    assert enc.exists()
    plain = crypto_util.decrypt(enc.read_bytes(), "phrase", salt)
    assert plain == jpg.read_bytes()
