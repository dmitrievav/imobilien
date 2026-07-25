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

As-of date: `2026-07-25`. Rates are nominal, annual, and — this matters —
measured over **identical 20-year windows** wherever a series exists.

- `capital = 10000000`, `horizon_years = 10` — set by the reader.
- `inflation = 0.06` — measured IRN.RU July 2026 reading (`data/irn.json`).
  Drives only the reference line.
- `deposit` — glides from today's measured 12.9% (IRN) to an assumed 8%
  floor over 3 years, interest taxed at 13% NDFL; the displayed `avg_rate`
  (7.8%) is what the path actually delivers. **[refine]** — floor and glide
  are judgement.
- `assets.tmos.rate = 0.078` — **measured**: MCFTR (MOEX total return incl.
  dividends), 20 years.
- `assets.ofz.rate = 0.081` — **measured**: RGBITR (OFZ total return),
  20 years. Note the live alternative: OFZ bought today yield ≈13% to
  maturity, far above their own 20-year average — surfaced on the site as a
  standing note rather than folded into the projection, which stays
  consistently historical.
- `assets.gold.rate = 0.159` — **measured**: CBR gold, 20 years. Flagged on
  the site as the least reliable projection despite being measured (see
  "Window sensitivity").
- `assets.usd.rate = 0.055` — **measured**: CBR USD, 20 years. Cash: no
  interest.
- `assets.buy_now_flat.rate = 0.06`, `buy_now_house.rate = 0.05` —
  **[refine]**, unmeasured. IRN blocks scripted access to its index history
  and no Rosstat series covers Pushkinsky-district IZhS, so these remain
  estimates derived from IRN's current yield reading net of assumed rent.
  The site now says outright that "housing lags inflation" is a hypothesis,
  not a finding: the 5–6% estimate sits inside its own error bar against
  6% inflation.
- `house_maintenance_rate = 0.015`, `property_tax_rate = 0.001`,
  `transaction_cost_rate = 0.03` — **[refine]** estimates. Property is the
  only asset carrying yearly costs, which is why a 5.0% house compounds at
  3.4%.
- `long_run_world` — 125-year global real returns from the literature
  (Dimson–Marsh–Staunton, UBS Global Investment Returns Yearbook): equities
  +5.2%, bonds +1.6%, gold +0.8% above inflation. Not our measurement, and
  not used in the projection — it is the sanity anchor that tells the
  reader our 20-year Russian window is an outlier.
- TPAY was dropped as a separate line: it duplicated the OFZ row.
- Bitcoin stays out: the free CoinGecko tier serves 365 days, over which BTC
  fell ~47% in RUB. One year is not a long-run average.

## Window sensitivity — why the answers keep changing

`scripts/fetch_history.py` now measures every asset over the same windows.
Nominal RUB CAGR as of 2026-07-25:

| Asset | 5y | 10y | 15y | 20y |
| --- | --- | --- | --- | --- |
| Stocks (MCFTR) | −2.6% | +8.6% | +8.1% | +7.8% |
| OFZ (RGBITR) | +4.7% | +6.9% | +7.2% | +8.1% |
| Gold | +18.9% | +14.0% | +13.9% | +15.9% |
| USD | +1.1% | +1.9% | +7.1% | +5.5% |

Three uncomfortable facts this exposes, all of which the site now states
plainly instead of hiding:

1. **Gold beat stocks over every Russian window.** Real, not an artifact of
   mismatched windows — but it is an artifact of *this* country and *this*
   window: gold gains twice over (world price plus ruble depreciation) while
   Russian equities absorbed 2008 and 2022.
2. **Bonds matched or beat stocks** over 20 years — an inverted risk
   premium. Not a law; a symptom of a bad two decades for equities, which
   are still 25% below their February 2025 peak.
3. **An earlier version of this file was wrong.** It quoted stocks at
   13.25%/yr and gold at 15.88%/yr as if comparable. They were not: the
   stock figure ran from 2003 and swept in a near-tripling during 2003–2005,
   while gold's ran from 2006. Same-window measurement cut stocks to 7.8%.
   Mixing windows is how a comparison lies while every individual number
   stays true.

A fourth was structural: OFZ used to be quoted at its current 13% yield
against historical averages for everything else, which made a low-risk asset
look equal to equities. Fixed by putting OFZ on the same historical basis.

## Peaks and drawdowns

`fetch_history.peak()` records each series' all-time high and the current
distance from it — a cheap read on "is this thing expensive right now".
As of 2026-07-25: stocks −25.1% (peak 2025-02-25), gold −24.3% (peak
2026-03-19), OFZ −2.2% (peak 2026-04-23, i.e. at the top because falling
rates lift bond prices), USD −35.2% (peak 2022-03-11, the panic spike).

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

## Measured history (superseded)

An earlier section here reported USD and gold CAGRs alone, over windows that
did not match the equity figures. It has been replaced by "Window
sensitivity" and "Peaks and drawdowns" above, which cover all four measured
assets on identical windows. `scripts/fetch_history.py` produces both.

## Reader-reported table defects (round 6)

The reader photographed the comparison table and sent it back without a
word. Reading it cold surfaced three ways the same column lied while every
number in it was arithmetically correct:

1. **Two rows showed 7.8% and different three-year sums** (deposit 13.2 mln,
   stocks 12.5 mln). Cause: the deposit's rate glides 12.9% → 8%, so it is
   front-loaded; 7.8% was its ten-year geometric average, true but useless
   as a row label.
2. **A row labelled 8.1% (OFZ) sat below a row labelled 7.8% (deposit)** at
   three and five years, for the same reason. It read as an arithmetic bug.
3. **Property rates were net of upkeep while every other row was gross.**
   "House 3.4%" against "gold 15.9%" invited a comparison that was never
   like-for-like — the house figure already had 1.6%/yr of costs removed.

Fixes: `rate_label_ru` now overrides the bare percentage wherever the rate
is not flat and gross ("12,9% сейчас, потом ниже", "3,4% после расходов"),
and the page carries a short "how to read the percentages" block.

**OFZ moved back to its current 13% yield to maturity** — reversing the
round-5 decision to put it on a historical basis. The round-5 reasoning was
that mixed bases had made a low-risk asset look like equities, which was
true of the *presentation*, but the underlying economics are not symmetric:
a bond held to maturity has a contractual future return, while equities and
gold have only a past. Quoting OFZ at 8.1% hid a real, low-risk, actionable
13% the family can lock today — a materially better answer to "where do we
park the money while we look" than the deposit. The 20-year average is kept
visible in the row's basis line, and `test_ofz_beats_deposit_at_every_horizon`
pins the corrected ordering so the inversion cannot return silently.
