# Methodology

Working notes on where every number in the model comes from, so future
refinement has a paper trail. Anything marked **[refine]** is an initial
estimate standing in until real data replaces it.

## Model shape (rewritten 2026-07-26, round 8)

Simplified again at the reader's direction, and this time the basis changed
rather than just the presentation:

- **World evidence, not a Russian window.** Stocks, gold and property now
  take their return *above inflation* from 125-year global statistics
  (Dimson–Marsh–Staunton; Shiller and Jordà et al. for housing) and add our
  inflation to it. Every Russian window we tried — 5, 10, 15, 20, 23 years —
  produced a different answer, and two of them inverted the risk premium.
  A local window cannot support a ten-year extrapolation; the world evidence
  can, and it is the only honest response to "23 года тоже слишком узко".
- **Deposit and OFZ keep today's Russian terms.** Their return is
  contractual and knowable in advance, so history would be the wrong source.
  `nominal_rate()` encodes the split: `real_rate` means world evidence,
  `rate` means a stated local rate.
- **House and flat merged into one `realty` row.** The two estimates were
  never distinguishable in the data.
- **No property costs.** Upkeep, property tax and transaction costs are
  gone, so every row is now gross and directly comparable — this removes the
  net-vs-gross asymmetry that had made "дом 3,4%" look worse than it was.
- **Drawdown from the all-time high** is now a table column, computed from
  the measured Russian series. It is the one place local history still
  appears, and it answers a question the averages cannot: is this asset
  expensive right now?
- **Verdict traffic light removed** along with the page that showed it; the
  table is the answer.

### Site shrunk to two pages

`index.html` (the calculator) and `listings.html` (the gallery).
`scenarios.html` and `checklist.html` were deleted at the reader's request —
the checklist content survives in `notes/legal-checklist.md`. The page no
longer replays the chat: the Q&A blocks explaining window sensitivity, the
gold-vs-stocks argument and the housing-data gap are gone, replaced by one
"Откуда цифры" section. The reasoning stays here, where it belongs.

### Resulting figures (2026-07-26)

| Asset | Rate | Below ATH | 10 years |
| --- | --- | --- | --- |
| OFZ | 13% locked | at peak | 33.9 mln |
| Stocks | 11.5% | −25% | 29.7 mln |
| Deposit | 12.9% → 8% | — | 21.2 mln |
| Realty | 7.1% | — | 19.8 mln |
| Gold | 6.9% | −24% | 19.4 mln |
| USD cash | 3.4% | −35% | 13.9 mln |
| (prices) | 6% | | 17.9 mln |

Gold drops from 15.3% to 6.9% purely by switching basis — the clearest
possible illustration of why the window question mattered.

### Denomination bug caught by this change

Extending the CBR fetch back to 1997 made every drawdown absurd (gold
−84.6%, USD −98.7%): the 1998 redenomination means pre-1998 quotes are in
old rubles, so a 1997 price registered as an unbeatable all-time high.
`denominate()` now rescales pre-1998 points by 1000, with a test pinning
both the boundary and the gold case.

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

## Why 23 years, and why not 20 (round 7)

The reader asked "почему среднее за 20 лет?" — a question with no good
answer, because there wasn't one. `WINDOWS = [5, 10, 15, 20]` and a fetch
start of `year - 21` were an arbitrary cap I wrote, not a constraint from
the data. Consequences, measured rather than argued:

| Window | Stocks | OFZ | Gold | USD |
| --- | --- | --- | --- | --- |
| 20 years | +7.8% | +8.1% | +15.9% | +5.5% |
| **23.4 years (all available)** | **+13.3%** | **+8.6%** | **+15.3%** | **+3.9%** |

Adding 3.4 years at the start nearly doubles the equity figure, because the
market roughly tripled during 2003–2005. The 20-year cap had cut that off —
which is precisely what produced the inverted risk premium the reader
questioned two rounds earlier. At the full window stocks (13.3%) beat bonds
(8.6%), and the inversion disappears. **The anomaly was an artifact of my
arbitrary window, not a property of the market.**

`fetch_history.common_window()` now derives the window instead of hardcoding
it: it starts where the youngest series starts and measures every asset from
that same date. `cagr_from()` takes the first point at or after that date —
never before it, which a test pins, since measuring one asset from earlier
than the shared start is exactly the mismatch the function exists to
prevent.

### Why not deeper than 2003

- MOEX MCFTR starts 2003-02-26 and RGBITR 2002-12-30; there is no earlier
  index. This is the binding constraint.
- CBR gold reaches back to 1997-03-25 and USD to 1992-07-01, so deeper
  numbers *can* be computed for two of the four assets — and doing so would
  recreate the very window mismatch we just removed.
- Worse, they would be meaningless. The 1998 redenomination divided the
  ruble by 1000 (USD 30.12.1997 = 5960 old rubles → 01.01.1998 = 5.96 new),
  and the early 1990s ran hyperinflation. A naive series through that gives
  USD +21%/yr since 1992 — arithmetically true, economically noise, and not
  comparable to today's 6% inflation without a matching CPI series we do not
  have.
- A 100-year Russian figure does not exist at all: no market, and no
  continuous currency. The 125-year global figures on the page are the only
  honest answer at that horizon.
