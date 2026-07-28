# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Decision-support project for a family purchase of a house or flat in
Pushkinsky district, Moscow region: per-listing valuation with a fair-price
range, capital-scenario comparison against alternatives (deposit, OFZ, bond
and equity funds, gold, USD), and a gated static site that presents it all
to elderly (70+) readers in plain Russian.

**Status: live** at `https://dmitrievav.github.io/imobilien/`. All content
renders only with the magic-URL key (passphrase in the URL fragment; local
`.env` holds it as `IMOBILIEN_KEY`). ~111 pytest tests. Remaining soft spots
are the **[refine]** marks in `notes/methodology.md` — the country-house
price benchmark is the weakest number in the project (no open data source
covers it; every checked source indexes flats only).

`notes/methodology.md` is the paper trail for every number and every
modelling decision, including the superseded designs and why they fell.
Read it before changing model behaviour; extend it when you do.

## Git model (unusual — read this first)

- Local branch **`public`** pushes to **`origin/main`**:
  `git push origin public:main`. Pages deploys from main via
  `.github/workflows/pages.yml`.
- Local branch `implementation` holds the full development history and must
  **never** be pushed: it contains the cleartext journal and a work email.
  The public repo intentionally started from one squashed commit.
- Before any push: `git status` must show no `.env`, `data/listings.json`,
  `data/photos/`, `*.png`; nothing from `.superpowers/` (session notes may
  contain third-party document extractions that must stay local).

## Architecture

Static-data pipeline published via GitHub Pages, no backend, no build step:

- `scripts/fetch_*.py` append dated points to `data/*.json` through
  `store.append_point` (append-only, atomic, dedupe by date[+segment]).
  Sources: CBR (fx/gold/key rate), MOEX ISS (TMOS/TPAY/RGBITR), CoinGecko,
  IRN.RU (town-level flat benchmarks; requires a browser User-Agent, uses
  only robots-allowed clean paths — `/graph/` and query-string URLs are
  disallowed, never fetch them). Cian cannot be scripted at all (WAF +
  robots): individual listings are extracted by a Claude agent in a
  supervised session, never by cron.
- `scripts/model.py` → `site/data/scenarios.json`: **nominal RUB**, one
  capital (10 mln), one average return per asset, a dashed inflation
  reference line, risk rank, and a dual-currency view (`series_usd`,
  ruble depreciation = inflation differential / relative PPP). Return
  bases are deliberately mixed and labelled: world 125-year real returns
  for globally traded classes (stocks, gold, realty), today's contractual
  Russian rates for the deposit and OFZ, a key-rate glide (`_glide_series`)
  for the deposit and the TPAY floater fund. BTC is excluded (no long RUB
  series exists). Do not reintroduce real-terms series, a pess/opt fan,
  property upkeep costs, or a Russian-window basis for world classes
  without asking — "Model shape" in the methodology records why each fell.
- `scripts/fetch_history.py` → `data/history.json`: same-window CAGRs,
  all-time-high drawdown and the 200-week (1000 trading days) moving-average
  position per asset; `model.py` copies the latest point into the site's
  "дорого или дёшево" column. The MA window is matched to the 3–10-year
  holding horizon — measured to predict multi-year returns far better than
  a 200-day window. Pre-1998 CBR quotes are rescaled 1000:1 by
  `denominate()` (ruble redenomination); without it 1997 reads as an
  unbeatable all-time high. Heavy; not part of `update_all`.
- `scripts/valuation.py` is the per-listing engine (appraiser method:
  base ₽/m² → adjustments → **range**, never a point). Key properties:
  coefficients live in `data/valuation_factors.json`, not code; adjustments
  are damped ×0.5 when the base comes from the listing's own comparables
  (else renovation double-counts); the accuracy band is the **measured
  coefficient of variation** of the comparables floored at 10%, and V>33%
  refuses the estimate (`verdict: "unreliable"`) instead of averaging junk;
  a Statrielt bargaining matrix converts asking → likely transaction price
  (`likely_deal` — the negotiation target shown on cards); area correction
  is the power law `(S/S_ref)^-0.11`. `scripts/fairprice.py` wires it to
  the encrypted journal and adds the independent `reprice_flag` (>20% jump
  in price_history — a bait-listing signal, separate from price fairness).
- `site/` — plain HTML + vendored Chart.js, TWO pages: `index.html`
  (comparison, ₽/$ toggle, index-mode tooltips) and `listings.html`
  (gallery: range bar with the asking-price dot, expandable adjustment
  table with Russian reasons, price-move line). Pages self-heal from stale
  caches via `assets/version.js` + `data/version.json`; all data fetches
  use `cache: "no-store"`.

## Access gate and crypto invariants

- `site/data/gate.json` publishes `{verifier, salt, iterations}` where
  `verifier = base64(SHA256(PBKDF2-HMAC-SHA256(passphrase, salt, 600000,
  32)))`. NOT a plain hash; the old unsalted `digest` field must not come
  back.
- `gate.js` derives bits ONCE per load, hashes them to verify, imports the
  same bits as the AES-GCM key. Blob layout: 12-byte IV || ciphertext+tag.
- `scripts/crypto_util.py` and `gate.js` MUST stay parameter-identical;
  `tests/vectors/gate_vector.json` pins both. A weakening is not
  retroactively fixable — old ciphertext stays in git history forever.
- Only the journal and photos are encrypted; market data is plaintext.
- Anti-indexing = per-page `noindex` meta + the gate. `site/robots.txt` is
  decorative on project Pages (crawlers read only the domain root).

## Privacy rules (the repo is PUBLIC)

- `.gitignore` must cover `.env`, `data/listings.json`, `data/photos/`.
  Plaintext journal and photos never reach git — only `*.enc` blobs.
- No family names, phone numbers, full addresses, or cadastral numbers
  anywhere — even inside encrypted payloads (settlement + listing URL only).
- Git author is the personal identity (`ave.dmitriev@gmail.com`), never a
  work email.

## Conventions

- Site copy is Russian for elderly readers: big fonts, few numbers per
  screen, no jargon, no replaying chat discussions on the page — necessary
  and sufficient explanations only; longer reasoning goes to `notes/`.
  Code, comments and repo docs are English.
- Every assumption lives in `notes/methodology.md` with its as-of date and
  an **[refine]** flag when it is an estimate rather than a measurement;
  outputs echo dates so the site shows data freshness.
- Fetchers fail soft and never corrupt a history file; `model.py` fails
  loud (better no update than a wrong chart).
- Verdict-affecting thresholds are pinned by tests (band floors, OFZ vs
  deposit ordering, cash-USD-flat-in-USD identity, denomination boundary).

## Commands

Use `.venv/bin/python` / `.venv/bin/pytest` (venv is set up; deps in
`requirements.txt`).

- `.venv/bin/pytest` — full suite; single file:
  `.venv/bin/pytest tests/test_valuation.py -q`.
- `.venv/bin/python scripts/update_all.py` — refresh CBR/MOEX/crypto/IRN,
  rerun model AND fair-price (assessment needs `IMOBILIEN_KEY`; without it
  it reports a skip).
- `.venv/bin/python scripts/stamp_build.py` — **run after ANY site/ edit,
  before committing**: stamps `?v=` on assets and writes
  `site/data/version.json` (elderly users cannot clear caches; this is the
  only cache-bust mechanism).
- `.venv/bin/python scripts/add_listing.py entry.json --photos p1.jpg ...` —
  ingest a new listing (agent-extracted JSON).
- `.venv/bin/python scripts/add_photos.py <id> <files...>` — attach photos
  to an existing listing.
- `.venv/bin/python scripts/fetch_history.py` — refresh long-run
  CAGRs/drawdowns/MA (heavy, occasional).
- Local preview: `python3 -m http.server 8000 -d site` and open
  `http://localhost:8000/#<passphrase from .env>` — WebCrypto needs a
  secure context (`localhost` qualifies, `file://` does not). Note: an
  in-page hash change does NOT re-run the gate; reload the page.
