"""Refresh all data sources (fail-soft), rebuild the model and re-assess listings."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def run_all(fetchers):
    statuses = {}
    for name, fn in fetchers.items():
        try:
            statuses[name] = "appended" if fn() else "skipped (dup)"
        except Exception as e:
            statuses[name] = f"FAILED: {e}"
    return statuses


def reassess(fairprice_main):
    """Re-run fair-price so edited benchmarks reach the site's verdicts.

    Needs the passphrase to read/write the encrypted journal, which a plain
    data refresh legitimately may not have — so this step reports and skips
    instead of failing the whole run.
    """
    try:
        fairprice_main()
        return "reassessed"
    except Exception as e:
        print(f"fair price: SKIPPED ({e}) — verdicts on the site are unchanged; "
              f"set IMOBILIEN_KEY and rerun scripts/fairprice.py")
        return f"skipped: {e}"


if __name__ == "__main__":
    import fairprice, fetch_cbr, fetch_crypto, fetch_moex, model
    statuses = run_all({"cbr": fetch_cbr.main, "moex": fetch_moex.main,
                        "crypto": fetch_crypto.main})
    for name, s in statuses.items():
        print(f"{name}: {s}")
    model.main()  # loud failure by design
    reassess(fairprice.main)
