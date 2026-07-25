"""Add/replace photos for an existing listing already in the journal."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import add_listing
import crypto_util
import fairprice


def find_entry(journal, listing_id):
    for entry in journal["listings"]:
        if entry["id"] == listing_id:
            return entry
    raise SystemExit(f"no listing with id {listing_id!r} in the journal")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("listing_id")
    ap.add_argument("photos", nargs="+", help="paths to photo files")
    args = ap.parse_args(argv)

    journal = fairprice.load_journal()
    entry = find_entry(journal, args.listing_id)
    passphrase = crypto_util.load_passphrase()
    entry["photos"] = add_listing.process_photos(
        args.listing_id, args.photos, passphrase, fairprice._salt())
    fairprice.save_journal(journal)
    print(f"added {entry['photos']} photo(s) to {args.listing_id}: {entry.get('label', '')}")


if __name__ == "__main__":
    main()
