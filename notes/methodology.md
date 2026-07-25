# Methodology

Working notes on where every number in the model comes from, so future
refinement has a paper trail. Anything marked **[refine]** is an initial
estimate standing in until real data replaces it.

## Model shape (rewritten 2026-07-25, round 4)

The first version showed inflation-adjusted ("real") rubles with a
pessimistic/optimistic fan across three capital levels. A reader — the
project's actual audience — reported it as counter-intuitive: lines went
*down* while everyone knows prices go *up*, and the fan added noise without
adding information ("и так понятно, что гарантии нет"). Rebuilt to:

- **Nominal rubles.** Every line rises, which matches intuition. Honesty is
  preserved by a dashed grey `inflation_line` — what you need just to keep
  up with prices. Above it is real gain, below it is a real loss. Same
  information, no counter-intuitive descent.
- **One capital: 10 mln RUB.** The three-level switcher is gone.
- **One average return per asset instead of a band**, taken from the
  longest measured window available, on the explicit assumption that the
  future resembles the past.
- **A risk rank** (`низкий` / `средний` / `высокий`) carries the
  uncertainty the band used to carry, in words a 70+ reader can act on.

## `data/assumptions.json` — value by value

As-of date for the whole file: `2026-07-25`. Rates are nominal, annual.

- `capital = 10000000`, `horizon_years = 10` — set by the reader.
- `inflation = 0.06` — measured IRN.RU July 2026 reading (`data/irn.json`,
  `https://www.irn.ru/analitika/`). Drives only the reference line.
- `deposit` — glides from today's measured 12.9% (IRN) down to an assumed
  8% floor over 3 years, interest taxed at the statutory 13% NDFL. The
  displayed `avg_rate` (7.8%) is the growth this path actually delivers, so
  the table never advertises today's peak rate as a ten-year expectation.
  **[refine]** — the 8% floor and 3-year glide are judgement, not data.
- `assets.tmos.rate = 0.1325` — **measured**: MOEX total-return index
  MCFTR, 2003-02-26 (335.67) to 2026-07-24 (6172.49), 23.4 years. Includes
  dividends. TMOS tracks this index, so the index history is the honest
  proxy for a fund with a shorter life.
- `assets.tpay.rate = 0.0903` — **measured**: RGBITR (OFZ total return),
  2003-01-04 (100.34) to 2026-07-24 (768.97), 23.6 years.
- `assets.ofz.rate = 0.13` — current yield to maturity, not history. For a
  bond held to maturity this is contractual, which beats a historical
  average. Deliberately a different basis from `tpay`, and the site shows
  the basis per row so the difference is visible.
- `assets.gold.rate = 0.1588` — **measured**: CBR accounting gold price,
  20 years (see "Measured history").
- `assets.usd.rate = 0.0546` — **measured**: CBR USD rate, 20 years. Cash
  dollars: no interest is credited.
- `assets.buy_now_flat.rate = 0.06` and `buy_now_house.rate = 0.05` —
  **[refine]**, and the weakest numbers in the project. Derived from IRN's
  July 2026 Podmoskovye housing yield (11.9%) minus an assumed ~5.5% gross
  rental yield, with houses set 1pp below flats for illiquidity. No long
  measured series exists for us here: IRN blocks scripted access to its
  index history, and no Rosstat series covers Pushkinsky-district IZhS.
  Everything the site says about houses rests on this estimate.
- `house_maintenance_rate = 0.015`, `property_tax_rate = 0.001`,
  `transaction_cost_rate = 0.03` — **[refine]** initial estimates; applied
  to both property scenarios. Note the property lines are the only ones
  carrying yearly costs, which is why they trail their headline rate (a
  5.0% house grows at 3.4% after upkeep).
- **Bitcoin was dropped** from the projection. The free CoinGecko tier
  serves only 365 days, and over that year BTC fell ~47% in RUB — one year
  is not a long-run average, and projecting −47% for a decade would be
  theatre. Mentioned on the page as a risk illustration instead.

### Known bias

Only the deposit and OFZ are taxed in the model (13% NDFL). Gold, currency
and the funds compound untaxed, which flatters them; long-held securities
get partial relief in reality (ЛДВ), gold and currency do not. The house
lines carry upkeep costs that no other asset carries — that asymmetry is
real, not a modelling error, but it means the property rows are compared
net while the rest are compared gross.

### What the house numbers leave out

The house is the only asset that is *used*. Rent forgone on a comparable
property is roughly 5.5% of its value per year — about 550k RUB/yr on a
10 mln house — and none of it appears in the chart. That is why a house
trailing the inflation line is not an argument against buying one; it is an
argument that a house has to earn its keep through use, not appreciation.

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

## IRN.RU readings (`data/irn.json`, 2026-07-25)

Source: `https://www.irn.ru/analitika/` — chart images with no open API, so
values are read off the page and recorded with their date.

| Reading | Value |
| --- | --- |
| Podmoskovye flats, price index | 161 832 RUB/m² (+0.6%) |
| Housing yield, Moscow | 14.2%/yr |
| Housing yield, New Moscow | 14.0%/yr |
| Housing yield, Podmoskovye | 11.9%/yr |
| Bank deposits | 12.9%/yr |
| Inflation | 6.0%/yr |

Two things this buys us:

1. **A validation of our own flat benchmark.** IRN's regional 161 832
   RUB/m² sits within 1.2% of the 160 000 RUB/m² we derived independently
   from district comparables — the two methods agree, which is reassuring
   for the flat verdicts.
2. **A measured anchor for inflation and deposit rates**, replacing two
   guesses (see the value-by-value list above).

The yield index bundles rent with appreciation; see "Why the house line
falls in real terms" for why that does not transfer to an owner-occupied
family house.

## Measured history: USD and gold (`data/history.json`, `scripts/fetch_history.py`)

Two assumption bands used to be pure guesses, and a reader challenged them
on the obvious grounds that "the dollar and gold always go up". Measured
nominal CAGR in RUB, straight from CBR series (USD `R01235` via
`XML_dynamic`, gold accounting price via `xml_metall`, Code=1), as of
2026-07-25:

| Window | USD/RUB | Gold RUB/g |
| --- | --- | --- |
| 5 years | +1.13%/yr | +18.86%/yr |
| 10 years | +1.86%/yr | +13.98%/yr |
| 15 years | +7.14%/yr | +13.89%/yr |
| 20 years | +5.46%/yr | +15.88%/yr |

What this settles:

- **Gold**: the intuition is right and our old `base: 0.06` was far too low.
  Gold beat Russian inflation over every window measured. Raised to
  `{pess: 0.02, base: 0.09, opt: 0.16}` — deliberately *below* the measured
  14–19%, because extrapolating an exceptional two-decade run forward is
  not the same as measuring it. **[refine]** — the gap between measured
  (14%) and assumed (9%) is a judgement call, not a calculation.
- **USD cash**: the intuition is wrong for the recent past. Over 5 and 10
  years the dollar grew 1–2%/yr against 6–8%/yr inflation, so cash dollars
  *lost* real purchasing power badly. Even the 20-year figure (5.5%/yr)
  roughly matches, not beats, Russian inflation over the same span. Base
  lowered from 0.05 to **0.035**, which is also what relative purchasing
  power parity predicts (Russian inflation ≈6% minus US inflation ≈2.5%).
  The pattern is jumps (1998, 2014, 2022) separated by long stretches of
  lagging — insurance against a devaluation event, not a growth asset.
- The model's `usd` scenario is **cash** dollars: no interest. A
  dollar-denominated interest-bearing instrument would add its coupon and
  is not modelled.

Consequence for the chart: gold's line now rises (+2.8%/yr real) and the
dollar's still falls (−2.4%/yr real). Both are now defensible from data
rather than from a guess. `site/scenarios.html` shows this table to the
reader for exactly the question that prompted it.
