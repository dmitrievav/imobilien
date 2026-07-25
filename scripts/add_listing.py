"""Ingest one listing (agent-extracted JSON + photo files) into the journal."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import crypto_util
import fairprice

PHOTOS_LOCAL = Path("data/photos")
PHOTOS_SITE = Path("site/data/photos")
MAX_WIDTH = 1600
JPEG_QUALITY = 80


def next_id(journal):
    nums = [int(l["id"][1:]) for l in journal["listings"] if l["id"].startswith("L")]
    return f"L{(max(nums) if nums else 0) + 1:03d}"


def process_photos(listing_id, photo_paths, passphrase, salt):
    PHOTOS_LOCAL.mkdir(parents=True, exist_ok=True)
    PHOTOS_SITE.mkdir(parents=True, exist_ok=True)
    for n, src in enumerate(photo_paths, 1):
        img = Image.open(src).convert("RGB")
        if img.width > MAX_WIDTH:
            img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)))
        jpg = PHOTOS_LOCAL / f"{listing_id}-{n}.jpg"
        img.save(jpg, "JPEG", quality=JPEG_QUALITY)
        blob = crypto_util.encrypt(jpg.read_bytes(), passphrase, salt)
        (PHOTOS_SITE / f"{listing_id}-{n}.enc").write_bytes(blob)
    return len(photo_paths)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("entry_json", help="path to agent-extracted listing JSON")
    ap.add_argument("--photos", nargs="*", default=[])
    args = ap.parse_args(argv)

    entry = json.loads(Path(args.entry_json).read_text())
    journal = fairprice.load_journal()
    entry["id"] = next_id(journal)
    entry.setdefault("added", date.today().isoformat())
    entry.setdefault("status", "considering")
    passphrase = crypto_util.load_passphrase()
    entry["photos"] = process_photos(entry["id"], args.photos, passphrase, fairprice._salt())
    journal["listings"].append(entry)
    fairprice.save_journal(journal)
    fairprice.main()  # re-assess everything, rewrites the .enc files
    print(f"added {entry['id']}: {entry.get('label', '')}")


if __name__ == "__main__":
    main()
