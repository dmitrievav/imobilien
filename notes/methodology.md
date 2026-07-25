# Methodology

Working notes on where every number in the model comes from, so future
refinement has a paper trail. Anything marked **[refine]** is an initial
estimate standing in until real data replaces it.

## `data/assumptions.json` — value by value

As-of date for the whole file: `2026-07-25`.

- `inflation.pess = 0.10`, `inflation.base = 0.07`, `inflation.opt = 0.05` —
  rough band around Bank of Russia's own inflation targeting corridor and
  recent CBR press-release forecasts (see key-rate finding below, which
  quotes a 2026 CBR inflation forecast of 6.0–7.0%). **[refine]** — replace
  with the CBR's actual published forecast range from the same press
  release/MPR once we pull it into `data/cbr.json`.
- `deposit.rate_start = 0.13` — assumed starting top-10-bank deposit rate.
  **[refine]** — not yet cross-checked against `cbr.ru` "top-10 banks
  deposit rate" publication (`data/deposits.json` fetcher is deferred by
  design; see key-rate finding for why even the key rate itself needs a
  same-day check). Given the key rate is 14.00–14.25% as of 2026-07-25,
  13% start looks plausible but slightly low for a fresh deposit; needs a
  real top-10 read.
- `deposit.rate_floor = 0.08` — assumed long-run real-terms floor once
  rate-cutting cycle ends. **[refine]** — initial estimate, no source yet.
- `deposit.decay_years = 3` — assumed glide path length from
  `rate_start` to `rate_floor`. **[refine]** — initial estimate, matches
  the model's own 3-year "wait" horizon used in the verdict light, not an
  independently sourced number.
- `deposit.interest_tax = 0.13` — Russian personal income tax (NDFL) rate
  on deposit interest above the tax-free threshold. Source: RF Tax Code,
  standard 13% NDFL rate. Not flagged for refinement — this is a
  statutory rate, not an estimate.
- `ofz_ytm = 0.13` — assumed OFZ (federal bond) yield-to-maturity.
  **[refine]** — initial estimate; should be replaced with an actual
  MOEX/`rusbonds` OFZ curve read for a representative maturity matching
  the model horizon.
- `growth.house = {pess: -0.03, base: 0.04, opt: 0.10}` — assumed nominal
  annual price growth for year-round houses in the district.
  **[refine]** — initial estimate; not yet anchored to Rosstat IZhS
  statistics or IRN.RU's Podmoskovye index (irn.ru/analitika).
- `growth.flat = {pess: -0.02, base: 0.05, opt: 0.10}` — same, for flats.
  **[refine]** — initial estimate; same refinement path as above.
- `returns.tmos = {pess: -0.05, base: 0.12, opt: 0.20}` — expected return
  band for the TMOS (MOEX index) ETF. **[refine]** — wide, honestly
  uncertain band based on general historical MOEX equity behavior, not a
  specific backtest.
- `returns.tpay = {pess: 0.06, base: 0.11, opt: 0.15}` — expected return
  band for TPAY (money-market/bond ETF). **[refine]** — same caveat.
- `returns.gold = {pess: -0.02, base: 0.06, opt: 0.15}` — expected RUB
  gold return band. **[refine]** — same caveat; could be anchored to
  `data/cbr.json` accounting gold price history once we have enough
  points.
- `returns.usd = {pess: 0.00, base: 0.05, opt: 0.12}` — expected RUB/USD
  appreciation band. **[refine]** — same caveat.
- `returns.btc = {pess: -0.40, base: 0.15, opt: 0.60}` — expected BTC
  return band, deliberately the widest of all bands given volatility.
  **[refine]** — illustrative only, labeled high-risk by design; not
  meant to be tightened the same way as the others.
- `house_maintenance_rate = 0.015` — assumed annual house maintenance
  cost as a fraction of value ("~1.5%/yr" per the design doc).
  **[refine]** — initial estimate, no district-specific source yet.
- `property_tax_rate = 0.001` — assumed effective property tax rate.
  **[refine]** — initial estimate; the model applies the same rate to
  houses and flats (a known simplification, see design doc "Deferred"
  list — flat vs. house property-tax nuance is out of scope for now).
- `transaction_cost_rate = 0.03` — assumed one-off transaction cost
  (agent fee + registration + incidental costs) as a fraction of price.
  **[refine]** — initial estimate, typical Moscow-region ballpark, not
  itemized.

## Fair-price method (`scripts/fairprice.py`)

- Price per m² = `price_rub / area` (house or flat area, whichever the
  listing has).
- Fair per m² = median of the listing's own `comparables_per_m2` array
  when present (same-building or adjacent comparables recorded at
  ingestion time), otherwise the segment benchmark from `data/realty.json`.
- Verdict band: `ratio = price_per_m2 / fair_per_m2`.
  - `ratio < 0.90` → "below market"
  - `0.90 ≤ ratio ≤ 1.10` → "fair"
  - `ratio > 1.10` → "overpriced"
  (`FAIR_BAND = 0.10` in code — a ±10% band around fair.)
- Reprice flag: for consecutive `price_history` entries, if
  `abs(b - a) / a > 0.20` (`REPRICE_THRESHOLD = 0.20`), the listing is
  flagged — a large repricing in either direction is treated as a
  bait-listing / distress signal, surfaced on the card rather than acted
  on silently.

## Realty benchmark seeds (`data/realty.json`)

- `flat = 160000 RUB/m²`, dated 2026-07-25 — median of the on-page Cian
  comparables gathered while ingesting the first flat listings in Pushkino
  on that date. Treated as a live, defensible number because it is a
  direct median of comparables, not a guess — but still narrow (only the
  comparables seen so far) and will move as more listings are ingested.
- `year-round house = 100000 RUB/m²`, dated 2026-07-25 — **[refine]**
  initial estimate of Pushkinsky-district asking prices for year-round
  houses, not yet backed by a comparable set the way the flat benchmark
  is. It is also the benchmark against which the only house observation so
  far came out overpriced, which is reason to firm it up before any house
  verdict is relied on.
- `dacha = 70000 RUB/m²`, dated 2026-07-25 — **[refine]** initial
  estimate, no comparables ingested yet for this segment.

## Key-rate finding (2026-07-25 cross-check)

`data/cbr.json` records `key_rate: 14.25` as of 2026-07-25, scraped from
the first row of the official historical table at
`https://www.cbr.ru/hd_base/KeyRate/`. The IRN.ru news feed
(`https://www.irn.ru/analitika/`, headline "Банк России снизил ключевую
ставку до 14% годовых", seen 2026-07-25) reports a cut to 14.00%.

Cross-checked directly against CBR sources on 2026-07-25:

- `https://www.cbr.ru/eng/dkp/mp_dec/` (decision history) confirms: on
  **24 July 2026** (a Friday), the Bank of Russia Board of Directors cut
  the key rate by 25 bp to **14.00%** — the previous cut, to 14.25%, was
  on 19 June 2026.
- `https://www.cbr.ru/eng/press/keypr/` confirms the same 24 July 2026
  press release text ("Bank of Russia cuts the key rate by 25 bp to
  14.00% p.a.").
- `https://www.cbr.ru/hd_base/KeyRate/` — the official day-by-day table —
  still shows **14.25%** for 24.07.2026 itself ("Данные доступны с
  17.09.2013 по 24.07.2026", last row `24.07.2026 → 14,25`).

**Conclusion: our fetcher is not stale or wrong.** The rate change
announced Friday 24 July 2026 had not yet taken effect in the official
day-by-day series as of 2026-07-25 (a Saturday); it takes effect the
following business day, **Monday 27 July 2026**. So `key_rate: 14.25` in
`data/cbr.json` correctly reflects the rate in force on the as-of date,
and the 14.00% figure the IRN-style headline reports is the
already-announced-but-not-yet-effective new rate. No fetcher change is
needed for this task; `data/cbr.json` should simply be refreshed after
2026-07-27 to pick up 14.00% once it becomes the current row in the CBR
table. Downstream effect: any scenario numbers computed before that date
are one step behind the freshest announced cut, understating how far
into the cutting cycle the CBR already is — a minor conservative bias in
the "wait for a better deposit rate" direction.

## Tax treatment asymmetry (known bias in the comparison table)

The model does **not** tax all scenarios equally, and the comparison table
on `site/scenarios.html` inherits that asymmetry:

- `deposit` and `ofz` have 13% NDFL applied to their yield
  (`deposit.interest_tax = 0.13`), so their curves are after-tax.
- `tmos`, `tpay`, `gold`, `usd` and `btc` compound **untaxed** — their
  curves are pre-tax.

Effect: the untaxed scenarios are flattered relative to deposit and OFZ by
roughly 13% of their accumulated gain. Read every fund/gold/currency/crypto
figure as an upper bound, and treat a small gap in their favour over
deposit as no gap at all.

How defensible is it per asset?

- `tmos`/`tpay` — partially defensible. Russian ЛДВ (долгосрочное
  владение) exempts gains on securities held 3+ years up to an annual
  limit, and the model's horizon is 3–10 years, so a long-held position
  can legitimately land near zero tax. Not exact: the exemption is capped,
  and TPAY-style distributions are taxed as they arrive rather than at
  exit.
- `gold`, `usd` — **not** defensible. Physical gold and currency gains are
  taxable on disposal with no ЛДВ analogue (the 3-year rule for property
  does not cover them the way it covers securities), so these curves are
  optimistic by close to the full 13%.
- `btc` — **not** defensible, and the tax question is the smaller of its
  problems given the deliberately wide return band.

Not fixed in code on purpose: taxing each scenario properly needs
per-asset holding-period and limit logic, which would add more model
complexity than the decision warrants. Recorded here so the bias is
visible rather than silent. **[refine]** — revisit if the fund scenarios
ever come close enough to the deposit line for 13% to change the verdict.

## Deposit modeling caveat

`assumptions.json.deposit` (`rate_start: 0.13` decaying to `rate_floor:
0.08` over `decay_years: 3`, `interest_tax: 0.13`) is an **[refine]**
initial estimate of the whole deposit glide path, not a read of actual
top-10 bank deposit offers. It needs to be checked against real published
top-10 average deposit rates (CBR publishes these; see design doc note
that a `data/deposits.json` fetcher is deferred by design — manual entry
is the intended path) before the "deposit vs. buy" verdict is treated as
more than directional. Given the key rate itself sits at 14.00–14.25% as
of 2026-07-25 per the finding above, a 13% starting deposit assumption is
in the right neighborhood but not verified against a specific bank
product.
