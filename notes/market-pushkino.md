# Market observations — Pushkinsky district

Snapshot as of 2026-07-25.

> **Scope note.** Per-listing data — IDs, settlements, micro-districts,
> asking prices, price histories, listing URLs and per-object verdicts —
> lives only in the encrypted journal (`data/listings.enc`) and is
> deliberately not reproduced here. This repository is public, and we are
> actively negotiating; publishing our read on a specific object would
> hand the other side our position. This file therefore keeps only
> non-identifying market analysis. See `notes/methodology.md` for how the
> fair-price verdicts are computed.

## Price-per-m² levels observed

Flats in this district currently show asking prices in the
**130000–177000 RUB/m²** range across the comparable sets gathered so far.
The bottom of that range is a single low outlier at **130434 RUB/m²** — a
2nd-floor unit in a 17-floor building, and low floors typically price
below higher floors in the same building. Excluding it, the observed band
tightens to roughly **148000–177000 RUB/m²**, which is the range the
fair-price verdicts actually key off. Treat the 130434 figure as a floor
effect, not as evidence that the market has softened.

Year-round houses in the district are asked at levels loosely around
**100000 RUB/m²** for the benchmark, but the house segment has too few
observations to call that an observed median. It remains an **[refine]**
initial estimate rather than a comparables-derived number — unlike the
flat benchmark (160000 RUB/m², itself a median of on-page comparables from
the same date). Individual house asking prices seen so far sit well above
that benchmark, which is exactly why the segment benchmark needs real
comparables before any house verdict is treated as more than directional.

## Pattern: the doubling "urgent sale" listing

One pattern is worth recording generically because it will recur and
because it is the reason `fairprice.py` carries a reprice flag at all:

- A listing advertises an *urgent sale* in its text.
- Within about two weeks, the asking price roughly **doubles** — no
  change to the object, the photos, or the description.
- The listing stays online at the new price.

Read this as demand probing or bait-listing behaviour rather than a
genuine repricing: an urgent seller does not double their price. Practical
handling: treat the *lower* historical figure as the anchor for what the
seller once considered acceptable, ask the seller directly to explain the
jump before investing any viewing effort, and do not let the higher number
reset your sense of the market. Mechanically, any consecutive pair of
price-history entries differing by more than 20% raises
`reprice_flag: true` (`REPRICE_THRESHOLD` in `scripts/fairprice.py`), and
the site surfaces it on the card rather than acting on it silently.

## Macro context

- **CBR key rate**: 14.25% in force as of 2026-07-25 per the official
  day-by-day table. A 25 bp cut to 14.00% was announced Friday
  24 July 2026 but had not yet entered the official series at the time of
  this snapshot; it takes effect the following business day, Monday
  27 July 2026. Full cross-check in `notes/methodology.md` under
  "Key-rate finding". Either way the rate is high, so deposits remain an
  attractive competing use of capital right now.
- **Deposit rates**: assumed to start near 13% (**[refine]** — not yet
  checked against actual top-10 bank offers) and decay toward an 8% floor
  over 3 years.
- **Model verdict**: **RED**. In the base case a deposit beats "buy now"
  by about **27% in real terms over a 3-year horizon** (mid capital
  level, `site/data/scenarios.json`). Reading: in the current rate
  environment, parking the capital and waiting is financially favourable
  to buying immediately. This is a quantitative signal, not a veto — the
  "dream dividend" of an actual house is deliberately kept out of the
  number (see the design doc).

## Methodology pointers

- Verdict bands, the fair-per-m² rule (comparables median when available,
  segment benchmark otherwise) and the reprice threshold:
  `notes/methodology.md` → "Fair-price method".
- Every model assumption with its as-of date and **[refine]** status:
  `notes/methodology.md` → "`data/assumptions.json` — value by value".
- Benchmark provenance and why the flat benchmark is defensible while the
  house and dacha ones are not yet: `notes/methodology.md` → "Realty
  benchmark seeds".
- Tax treatment asymmetry between deposit/OFZ and the fund/gold/currency
  scenarios: `notes/methodology.md` → "Tax treatment asymmetry".

## Sources

Public sources only — per-listing sources stay in the encrypted journal.

- CBR key rate history (day-by-day, official):
  `https://www.cbr.ru/hd_base/KeyRate/` (checked 2026-07-25).
- CBR key-rate decisions and press releases:
  `https://www.cbr.ru/eng/dkp/mp_dec/`,
  `https://www.cbr.ru/eng/press/keypr/` (checked 2026-07-25).
- IRN.RU analytics (Podmoskovye price index, housing-yield index):
  `https://www.irn.ru/analitika/` — planned inputs per the design doc, not
  yet pulled into any data file. No IRN-sourced figure is relied on above;
  closing this gap is a future update.
- Realty benchmark seeds as committed: `data/realty.json` (see
  methodology for provenance and refinement status).
