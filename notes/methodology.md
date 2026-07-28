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

## Currency: the assumption the ruble view was hiding (round 9)

The reader spotted that world statistics are dollar-denominated while every
number on the page was in rubles — so the model silently assumed something
about the exchange rate. It did: **relative purchasing power parity**, that
the ruble slides by exactly the inflation differential. `depreciation()`
makes it explicit at (1+6%)/(1+2.5%)−1 = **3.41%/yr**, and `to_usd()`
divides each series by that path.

The conversion is internally consistent by construction: a world asset
earning `r` real ends up at `(1+r)(1+US inflation)−1` in dollars and
`(1+r)(1+RU inflation)−1` in rubles, and cash dollars come out at exactly
0%/yr in dollars — a test pins that, because if it did not hold, the
conversion would be wrong somewhere.

What each view hides, and why both are on the page behind one toggle:

- **Rubles** flatter everything. 13% on OFZ becomes 9.3% for someone
  counting in dollars; the 3.7pp gap is currency slide, not return.
- **Dollars** are not what the family spends. They will buy a house priced
  in rubles, so a dollar-denominated gain that a ruble house price outran is
  no gain at all.
- Over ten years PPP is a defensible central case. Over one year it is
  nearly worthless: the ruble doubled against the dollar in months in 2022
  and has since given back 35% from that peak. The page says so.

## The Russian discount, without forecasting it

The reader also argued Russia is an emerging market whose growth lies ahead,
currently depressed by war and geopolitics, and that recovery waits on a
stable peace. Two things are worth separating here.

**What we refuse to model.** "Recovery is coming" is a forecast, and the
whole direction of this project has been to remove forecasts. Worse, the
underlying intuition — that a fast-growing economy pays shareholders more —
is not supported: over the long run emerging markets have *not* outpaced
developed ones in returns, only in volatility. Economic growth and equity
returns are different things.

**What is already measured.** The discount does not need forecasting because
it is visible in today's prices:

- OFZ yield 13% where world bonds return ~1.6% real.
- Russian equity dividends alone contributed **+7.77 pp/yr over the last 5
  years** (MCFTR 
  −2.40%/yr vs IMOEX −10.16%/yr), against **+4.81 pp/yr over 23 years**
  (13.25% vs 8.44%). Prices fell, payouts did not — that is what "cheap"
  looks like in a number rather than an opinion.
- Equities sit 25% below their February 2025 peak.

So the high local rates in the model *are* the risk premium for exactly the
risks the reader names. If conditions normalise, the discount compresses and
the holder earns more than the table shows; if they do not, the premium is
never collected. Adding a recovery premium on top would double-count what
the market has already priced.

## Moving averages: what they can and cannot do (round 10)

The reader proposed basing forecasts on a 200-day moving average, to escape
the peaks and drawdowns. Tested rather than argued. Same common window
(from 2003-02-26), CAGR computed from raw endpoints versus from 200-day
moving-average endpoints:

| Asset | raw | smoothed | difference |
| --- | --- | --- | --- |
| Stocks | 13.25% | 13.91% | +0.66 pp |
| OFZ | 8.60% | 8.80% | +0.20 pp |
| Gold | 15.33% | 16.16% | +0.83 pp |
| USD | 3.94% | 3.91% | −0.03 pp |

**Smoothing does not help the forecast.** Worst case 0.83 pp, against the
5.5 pp swing that came from moving the window start by three years (7.8% →
13.3% for equities). The reason is structural: over a long span both
endpoints get smoothed and the effects nearly cancel — a test pins this on
synthetic data. Window sensitivity comes from *which years are included*,
which no amount of averaging can change. And since round 8 the forecasts do
not use Russian price history at all; they come from 125-year world
statistics, so there is nothing left to smooth there.

**But it is a better "expensive or cheap right now" gauge than distance from
the all-time high**, and that is where it now lives:

| Asset | below ATH | vs 200-day average |
| --- | --- | --- |
| Stocks | −25.1% | −12.8% |
| OFZ | −2.2% | +2.2% |
| Gold | −24.3% | −8.8% |
| USD | −35.2% | **+0.6%** |

The dollar is the case that settles it. "35% below its record" suggests a
bargain; the record is a 2022 panic spike four years stale. Against its own
trailing average the dollar is sitting exactly where it usually sits. Only
one of those two numbers describes today, so the table now leads with the
moving-average reading and keeps the ATH figure as a small second line.

## Choosing the window: match it to the holding period (round 11)

The reader asked whether a 200-*week* average would be better, and how to
choose the window given a 3–10 year holding period. Answered by measuring,
on our own series, the correlation between "log distance from the average"
and the annualised return over the FOLLOWING 3 / 5 / 10 years:

| Asset | window | next 3y | next 5y | next 10y |
| --- | --- | --- | --- | --- |
| Stocks | 200 days | −0.35 | −0.31 | −0.47 |
| | **200 weeks** | **−0.55** | **−0.51** | **−0.83** |
| | 10 years | −0.62 | −0.78 | −0.82 |
| OFZ | 200 days | −0.09 | −0.35 | +0.04 |
| | **200 weeks** | **−0.31** | **−0.71** | +0.01 |
| | 10 years | −0.32 | −0.73 | −0.40 |
| Gold | 200 days | −0.30 | −0.26 | −0.14 |
| | **200 weeks** | **−0.55** | −0.29 | −0.40 |
| | 10 years | −0.61 | −0.45 | −0.65 |
| USD | 200 days | **+0.04** | **+0.01** | −0.14 |
| | **200 weeks** | −0.23 | −0.23 | −0.55 |
| | 10 years | −0.39 | −0.54 | −0.85 |

The pattern is consistent across all four assets: the longer the averaging
window, the better the deviation explains multi-year returns. The 200-day
window is near-useless for a decade-long decision — for the dollar it is
literally zero.

**Rule adopted: the averaging window should be on the order of the holding
period.** For 3–10 years that means years, not months. `MA_WINDOW` is now
1000 trading days ≈ 200 weeks ≈ four years — inside the horizon range, and
with more independent history behind it than a ten-year window has on a
23-year series.

### Two honest caveats

1. **The correlations are weaker than the sample sizes suggest.** Those
   n≈5000 daily observations of a 5-year forward return contain only about
   four independent 5-year periods in 23 years of data. The *direction* is
   consistent and matches theory; the magnitudes must not be read as laws.
2. **A long average assumes the old normal still applies.** Russian equities
   post-2022 lost their foreign investor base; a four-year average that
   still remembers 2021 may be a level the market never returns to. Mean
   reversion presumes the regime did not permanently change.

### What changed on the page

The window switch moves the readings materially, and mostly for the better:

| Asset | 200 days | 200 weeks |
| --- | --- | --- |
| Stocks | −12.8% | −6.7% |
| OFZ | +2.2% | **+19.8%** |
| Gold | −8.8% | **+38.6%** |
| USD | +0.6% | −5.5% |

Gold inverts outright: ten months of data call it 9% cheap, four years call
it **39% expensive**. The 24% pullback from March 2026 barely dents a run
that large — and that is the reading consistent with the world evidence,
which expects gold to return barely more than inflation. The short window
had been hiding exactly the "overbought" case the reader was asking about.

## Per-listing valuation (round 12)

The gallery used to show a bare "overpriced / fair" label from comparing
price per m² to a single benchmark. That compared unlike with unlike: a new
234 m² house with gas, central water and a designer interior was measured
against an unadjusted district average and came out "+43% overpriced".

`scripts/valuation.py` replaces it with the method appraisers use —
comparison with adjustments. Base price per m², then corrections for how
this object differs, then a **range** rather than a point.

Adjustments (all in `data/valuation_factors.json`, so they can be argued
with rather than dug out of code):

- **Flats:** floor position (first −7%, last −3%), building age band, wall
  material (panel −5%, brick +3%, monolith +5%), renovation (none −12% …
  designer +8%), large kitchen +3%, tall ceilings +2%, and a size discount
  because bigger flats sell for less per metre.
- **Houses:** gas ±15% (the single biggest factor in the country-house
  market), central water and sewage +7%, IZhS vs SNT, wall material, age,
  distance from MKAD in bands, plot size above 10 sotki, renovation, plus
  banya / terrace / garage.

Every coefficient is a practice-based order of magnitude, not a regression
on a large sample. The page says so.

### Two guards against fooling ourselves

1. **Damped adjustments when comparables are used.** If the base is the
   median of nearby listings, those already embed typical renovation and
   building type, so corrections on top would double-count. The weight drops
   to 0.5 (`comparable_adjustment_weight`). Without this, L003 came out
   "undervalued by 14%" purely from counting its euro renovation twice.
2. **The band widens when the inputs are thin**: ±10% base, +5% with no
   comparables, +10% when the benchmark itself is a flagged estimate, +2%
   per missing field, capped at ±30%. `data/realty.json` now marks which
   benchmarks are measured (flats, a median of real comparables) and which
   are guesses (houses, dachas).

### What this changed for the three real listings

| | asking | estimate | range | verdict |
| --- | --- | --- | --- | --- |
| House, Mogiltsy | 33.5 | 36.0 | 27.0–45.0 (±25%) | inside |
| Flat, Zapadny | 11.3 | 11.7 | 10.5–12.9 (±10%) | inside |
| Flat, O'Pushkin | 15.8 | 17.3 | 15.2–19.3 (±12%) | inside |

The house verdict flips from "overpriced" to "inside the range" — but with a
±25% band, because its base benchmark is unmeasured. That width is the point:
the honest answer for that house is "we cannot tell precisely", not a
confident verdict either way. The reprice flag (+116% in two weeks) is
reported separately, since a suspicious history is a different fact from a
fair price, and a test pins that independence.

### Gallery presentation

A range bar shows the band with the asking price as a dot on it, coloured by
verdict, with a grey tick at the estimate. Expanding a card shows the base,
every adjustment with its reason in Russian, the resulting price per m² next
to the asking one, and the accuracy band. The status badge now appears only
when it says something — every card reading "Рассматриваем" was noise.

Chart tooltips also fixed: `interaction: {mode: "index", intersect: false}`,
so hovering anywhere on a year lists every line, sorted by value. A 70+
reader should not have to hit a 3-pixel stroke.

## What the official court appraisal taught us (round 13)

The user supplied a 32-page expert opinion by an independent appraisal company,
prepared as court evidence. Full methodology extraction (no personal data) is
in `.superpowers/sdd/.../appraisal-methodology.md`. Four things were worth
adopting; two were not adoptable and are recorded as known gaps.

### Adopted

1. **Bargaining discount (скидка на торг).** The report converts asking prices
   to expected transaction prices before comparing anything, arguing that
   roughly 30% of listings are simply over-asked. It applies **−6.0%** to every
   comparable, from a Statrielt quarterly survey matrix keyed on
   market × area band × location group; secondary market, ≤100 m², group Б
   (Moscow-oblast cities inside the agglomeration — where Pushkinsky district
   falls) = 0.94. We now carry that matrix: 0.94 up to 100 m², 0.93 to 140 m²,
   0.90 above. For houses the table has no row, so 0.92 is our own flagged
   estimate — country property is less liquid, so the discount should be wider
   than a flat's, and we say that is a judgement.

   The valuation keeps the verdict on an asking-to-asking basis (comparables
   are asking prices too, so that comparison stays like-for-like) and reports
   the discounted figure separately as `likely_deal` — the price such objects
   actually change hands at, i.e. **how far it is worth negotiating**. That is
   the most directly useful number the report gave us.

2. **Area correction as a power law, not a bracket.** Unit price is
   `C = b·S^n` with a "коэффициент торможения" n = **−0.11** fitted at
   R² = 0.703 on matched pairs. Replaces our −2%-per-20 m² step function. The
   exact form is `(S_subject / S_analogue)^-0.11`, comparing against each
   analogue's area; we only store comparables' prices, not their areas, so we
   compare against the segment's reference area instead. **[refine]** —
   recording comparable areas at ingestion would let us use the real pairwise
   form.

3. **A computed dispersion statistic instead of an assumed band.** The report
   computes the coefficient of variation on the adjusted analogue prices
   (V = 0.65% in its case) and reads it against printed bands: <10%
   insignificant, 10–20% medium, 20–33% significant, **>33% ⇒ the comparative
   approach may not be used at all**. Our band was a constant we invented.
   Now `variation()` measures the spread of the comparables and the band is
   `max(base 10%, V)` plus the existing penalties, and V above 33% returns
   verdict `unreliable` rather than a confident-looking number.

   Effect on real listings: the Zapadny flat's comparables agree to 1.9%, so
   its band stays at the 10% floor; the O'Pushkin flat's disagree by **13.8%**
   ("разброс средний"), widening its band from ±12% to ±16%. That width is now
   measured rather than asserted.

4. **The report's own caveat, reproduced.** V is small *because* almost nothing
   was adjusted and all four analogues were near-identical listings from one
   neighbourhood. It measures the spread of the inputs, not the accuracy of the
   answer. Our code says so in the docstring, and the page says so in Russian.

### Not adopted, and why

- **Inverse-gross-adjustment weighting.** The report weights each analogue by
  `W_i = (1 − d_i/Σd)/Σ(...)`, so the analogue needing fewest corrections
  counts most. We cannot: we store comparables as bare prices per m² with no
  characteristics, so there is no per-analogue adjustment total to weight by.
  We take a median instead, which is at least robust to one outlier.
  **[refine]** — needs richer comparable records.
- **Zero corrections for location, transport, wall material, floor,
  renovation, bathroom, balcony.** The report applies *none* of these, because
  its four analogues were selected to match on all of them; only bargaining and
  area remained. That is the ideal, and it validates our damping of adjustments
  when comparables are close — but with 3–4 opportunistically collected
  comparables we cannot claim that degree of matching, so the corrections stay.

### Also notable, not actionable for us

Only the comparative approach was used, weight 1.0; the cost approach was
rejected under ФСО № 7 п. 24 (not applicable to parts of buildings, no
separable plot per ст. 36 ЗК РФ) and the income approach because the rental
market is unregistered and cash, leaving no reliable NOI. A single point figure
was reported, not a range — deliberately, and with no rounding to thousands.
We keep reporting a range, which for our data quality is the honest choice.

## Benchmark base: removing a circular reference (round 13)

The flat benchmark in `data/realty.json` was 160 000 RUB/m² — the median of
the very on-page comparables that the benchmark is then used to judge. That is
circular. Replaced with IRN.RU's independent Podmoskovye flat index,
**161 832 RUB/m²** (`https://www.irn.ru/analitika/`, read 2026-07-25). The two
agree within 1.2%, which is reassuring about both, but only one of them is
independent evidence.

Checked and not available: IRN publishes no RUB/m² statistics for country
houses (`irn.ru/zagorodnaya/` is a search page, not an index), and no open
series covers Pushkinsky-district IZhS. The house benchmark therefore stays a
flagged estimate at 100 000 RUB/m², which is why every house verdict carries a
±25% band. That remains the single weakest input in the project.
