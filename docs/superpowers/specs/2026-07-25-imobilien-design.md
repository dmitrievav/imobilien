# Imobilien — Family Real-Estate Decision Project — Design

Date: 2026-07-25
Status: **historical** — this is the original design the project was built
from. The implementation has since evolved well past it through reader
feedback (site reduced to two pages, per-listing valuation engine with a
computed accuracy band, world-evidence return bases, dual-currency view,
cache busting, and more). The living documentation is `CLAUDE.md`
(architecture, invariants, commands) and `notes/methodology.md` (every
number's provenance and every superseded decision with its reason). This
file is kept for the record of what was originally agreed, not as a
description of current behaviour.

## 1. Context and goals

Parents (70+) dream of buying a house in Pushkinsky district (Moscow region) to
gather the family under one roof. Budget: 10–25 mln RUB. Decision horizon is
undefined — the first question the project must answer is *whether and when* to
buy, not only *what* to buy.

Scope covers both **houses** (the dream scenario) and **flats** in the
district — the family actively considers flats too (scope extended
2026-07-25). Houses and flats are separate segments throughout: separate
benchmarks, segment-aware fair-price logic, one shared gallery.

The project serves three audiences with different needs:

- **Parents** — need a simple, visual, large-font presentation in Russian that
  respects their dream and shows the trade-offs honestly.
- **The user (heir, analyst)** — needs rigorous analysis: fair price
  assessment, benefit vs. alternatives, market prospects.
- **Claude agent / scripts** — semi-automated data refresh, run occasionally.

Success criteria:

1. A defensible answer to "buy now / wait / buy this one" backed by data.
2. Fair-price assessment for any concrete listing entered into the journal.
3. Scenario comparison of the capital against alternatives: bank deposits,
   OFZ bonds, MOEX index funds (TMOS, TPAY), gold, hard currency, crypto.
4. Parents can open a link and understand the conclusion in 5 minutes.

Non-goals (YAGNI):

- No scraping of Cian/Avito (they block it; listings are entered manually or
  by a Claude agent reading a listing page on demand).
- No backend, no database, no build toolchain for the site.
- No rent-vs-buy analysis and no alternative locations (explicitly descoped
  by the user).

## 2. Architecture overview

Static-data pipeline, published via GitHub Pages:

```
scripts/fetch_*.py ──► data/*.json (history, one point per run)
                            │
scripts/model.py  ──────────┴──► site/data/*.json (model outputs for charts)
                                       │
site/ (plain HTML + Chart.js) ◄────────┘
       │
GitHub Actions ──► GitHub Pages (public URL for parents)
```

Update workflow: `python scripts/update_all.py` → review diff → commit →
push → Pages redeploys. Run manually or by a Claude agent "time to time".

## 3. Repository layout

```
imobilien/
├── data/                  # raw time series, appended on each update
│   ├── cbr.json           # key rate, official inflation, USD/EUR, gold price
│   ├── deposits.json      # top deposit rates (manual/agent entry)
│   ├── moex.json          # TMOS, TPAY closes; OFZ yield (RGBI or ladder)
│   ├── crypto.json        # BTC price
│   ├── realty.json        # price-per-m2 benchmarks for Pushkinsky district
│   ├── listings.json      # journal of houses — LOCAL ONLY, gitignored
│   ├── photos/            # plaintext listing photos — LOCAL ONLY, gitignored
│   └── listings.enc       # encrypted journal, the committed source of truth
├── scripts/
│   ├── fetch_cbr.py       # CBR open XML/JSON APIs
│   ├── fetch_moex.py      # MOEX ISS public API
│   ├── fetch_crypto.py    # CoinGecko public API
│   ├── model.py           # scenario engine → site/data/scenarios.json
│   ├── add_listing.py     # ingest listing JSON + photos → journal + .enc
│   ├── fairprice.py       # listing vs. benchmark → site/data/listings.enc
│   ├── crypto_util.py     # AES-GCM encrypt/decrypt, PBKDF2 key derivation
│   └── update_all.py      # orchestrates fetches + model, fails soft per source
├── site/                  # static site, no build step
│   ├── index.html         # verdict page ("Вывод"): traffic light + 3 numbers
│   ├── scenarios.html     # capital scenarios charts
│   ├── listings.html      # gallery of considered houses + fair-price verdicts
│   ├── checklist.html     # how to inspect a house (для семьи)
│   ├── assets/            # chart.js (vendored), style.css, gate.js
│   ├── robots.txt         # Disallow: / (belt and suspenders with noindex)
│   └── data/              # model outputs (open) + listings.enc + photos/*.enc
├── notes/                 # working analysis, markdown, updated as we learn
│   ├── market-pushkino.md # district market overview and sources
│   ├── methodology.md     # fair-price and scenario assumptions, with dates
│   └── legal-checklist.md # ownership/encumbrance checks (protects parents)
├── .env                   # IMOBILIEN_KEY passphrase — gitignored
├── .github/workflows/pages.yml
└── docs/superpowers/specs/   # design docs (this file)
```

## 4. Data sources

Automated (public APIs, no keys):

- **CBR** — key rate, official USD/EUR, accounting gold price
  (`cbr.ru` XML services).
- **MOEX ISS** — TMOS and TPAY closing prices, RGBI / OFZ yields
  (`iss.moex.com`, JSON, no auth).
- **CoinGecko** — BTC price in RUB/USD.

Semi-manual (entered by the user or a Claude agent from public stat pages,
because no stable free API exists):

- **Realty benchmarks** — median asking price per m² in Pushkinsky
  district by segment (dacha / year-round house / flat; flats additionally
  by micro-district and building age band), with source URL and date
  recorded per data point (SberIndex, Rosstat IZhS stats, public market
  reports, comparable listings).
- **Deposit rates** — top-10 bank average (CBR publishes this decade-ly; can
  be automated later if the endpoint is stable).
- **IRN.RU indices** (irn.ru/analitika) — Podmoskovye price-per-m² index,
  housing yield index (vs. deposits and inflation), mortgage rate dynamics,
  secondary-market supply, and IRN forecasts; city-level prices for
  Pushkino when published. Charts are images with no open API, so values
  are read off the pages by the user or a Claude agent and recorded with
  date + source URL. Used for the macro layer and "wait" scenario paths —
  NOT a substitute for our own district benchmarks (IRN is flat-centric
  and aggregate).
- **Listings journal** — each considered house: asking price, area m², land,
  segment, distance to station, condition notes, listing URL. Fed by the
  ingestion workflow below.

### Listing ingestion workflow

The user drops a listing URL (Cian/Avito/etc.) into a Claude session. The
agent extracts the structured fields (using its web-extraction tooling —
these sites block dumb scripts, so extraction stays agent-driven, never a
cron job), downloads 3–5 representative photos, and calls
`scripts/add_listing.py` with the field JSON. The script:

1. Assigns a listing id, appends the entry to local `data/listings.json`.
2. Compresses photos to web size (~200 KB) into local `data/photos/<id>-<n>.jpg`
   (gitignored), then encrypts each to `site/data/photos/<id>-<n>.enc`.
3. Runs `fairprice.py` so the entry immediately gets a verdict.
4. Re-encrypts the journal to `data/listings.enc` / `site/data/listings.enc`.

Photos are stored in the repo (encrypted) rather than hotlinked, because
listings get taken down and the gallery must outlive them; the original
listing URL is kept in the entry for as long as it works.

Journal entry fields: `id`, `added` (date), `status`
(`considering / viewed / favorite / rejected`), `url`, `label` (short
human name, e.g. "дом в Ельдигино"), `settlement`, `price_rub`,
`segment` (`dacha / year-round house / flat`), `year_built`,
`condition_notes`, `family_notes`, `price_history` (list of dated asking
prices — repricing is itself a signal, see the bait-listing case L001),
`photos` (count), plus the `assessment` block written by `fairprice.py`.
Segment-specific fields — houses: `house_m2`, `land_sotki`,
`land_category`, `wall_material`, `utilities`, `mkad_km`, `station_km`;
flats: `flat_m2`, `living_m2`, `kitchen_m2`, `floor` ("4/18"),
`ceiling_m`.

Every data file is append-only history: `{"date": "YYYY-MM-DD", ...}` points,
so charts can show trends and the "wait" scenario can be evaluated against
what actually happened.

## 5. Scenario model (`model.py`)

Revised 2026-07-25 after the reader found the original presentation
counter-intuitive. Rationale and the superseded design are recorded in
`notes/methodology.md` ("Model shape").

Inputs (config in one place, documented in `notes/methodology.md`):

- Capital: a single 10 mln RUB.
- Horizon: 10 years, evaluated yearly.
- Inflation: one current measured rate, used only for the reference line.
- Per asset: one average annual return, its basis (measured window or
  current yield), and a risk rank.

Scenarios, all reported in **nominal RUB** so every line rises, which is
how a non-financial reader expects money to behave. Real-terms honesty is
carried by a dashed reference line rather than by falling curves:

1. **Buy house / buy flat** — entry costs once, then growth net of ~1.5%/yr
   maintenance and property tax. The house's use value (forgone rent) is
   never monetized into the line; it is stated in words beside it, so the
   dream is presented alongside the numbers, not inside them.
2. **Deposit** — glides from today's measured rate to an assumed floor,
   interest taxed; the table shows the average the path actually delivers.
3. **OFZ** — current yield to maturity (contractual if held to maturity).
4. **TMOS / TPAY** — long-run measured index returns (MCFTR, RGBITR).
5. **Gold / USD** — long-run measured CBR series. BTC is excluded: no long
   RUB history is available from a free source, so no honest average exists.
6. **Inflation line** — what the capital must reach merely to keep up.

Uncertainty is expressed as a **risk rank** (низкий / средний / высокий),
not a pessimistic/optimistic fan: the reader already knows nothing is
guaranteed, and the fan cost more comprehension than it bought.

Output: `site/data/scenarios.json` — per asset a nominal series, the
delivered average rate, the risk rank and the basis string; plus the
inflation line, the verdict block, the echoed assumptions and the latest
measured-history point (so the site can show "данные от 25.07.2026").

## 6. Fair-price assessment (`fairprice.py`)

For each listing in `listings.json`, segment-aware:

- Compute price per m² and compare with the district benchmark for the
  listing's segment (houses vs. the house benchmark; flats vs. the flat
  benchmark for their micro-district and building age band, plus direct
  comparables — same building or adjacent listings — when recorded).
- Apply documented adjustment factors (houses: condition, communications,
  distance to station/CKAD, land size; flats: floor position, building
  age, renovation) — factors listed in `notes/methodology.md`, kept crude
  and transparent rather than pseudo-precise.
- Flag anomalous `price_history` (a large repricing in either direction is
  a bait-listing / distress signal and is surfaced on the card).
- Verdict per listing: `below market / fair / overpriced` with a fair-price
  range in RUB.

Output merged into the journal payload and written as encrypted
`site/data/listings.enc` (see section 8) for the journal page.

## 7. Site design (for elderly parents)

- Plain HTML + vendored Chart.js, one shared stylesheet. Russian language.
- Large base font (≥20px), high contrast, no interactive controls beyond
  links between the four pages; charts have big labels and few series.
- `index.html` leads with a traffic-light verdict and at most three
  supporting numbers, followed by one sentence about the dream: the house
  question is not only about money.
- `listings.html` is a card gallery: one card per property (houses and
  flats mixed, filterable by segment) — cover photo, short label,
  settlement, price, m², price per m² vs. market, verdict badge
  (ниже рынка / справедливо / переоценён) and status badge
  (рассматриваем / смотрели / фаворит / отклонён). Clicking a card expands
  it in place: all photos, key parameters, the fair-price breakdown,
  family notes, and the link to the original listing. Rejected cards sink
  to the bottom, dimmed — the history stays visible. Photos and journal
  data are decrypted in the browser with the gate key (encrypted blobs →
  object URLs); without the key the gallery renders nothing.
- Every page shows the data as-of date.
- All pages are gated by the magic URL (section 8): without the key the
  page shows a neutral placeholder and renders nothing.

## 8. Access gate — magic URL (hybrid scheme)

Goal: the site is unusable for crawlers and casual visitors, while parents
only need to click one link. The repo stays public, so the scheme is honest
about what it protects: the *rendered site* is hash-gated, and the one truly
sensitive artifact — the listings journal — is additionally encrypted.

Mechanics:

- The family link is `https://<user>.github.io/imobilien/#<passphrase>`.
  The URL fragment is never sent to the server (absent from Pages logs and
  referrers) and is ignored by crawlers.
- `gate.js` on every page: reads the fragment (or localStorage), runs
  PBKDF2-HMAC-SHA256 over it with the salt and iteration count from
  `data/gate.json` via `crypto.subtle.deriveBits`, SHA-256s the derived
  bits, and base64-compares the result against the published `verifier`
  field. On match it stores the passphrase in localStorage (so bookmarks
  without the fragment keep working) and lets the page render.
- The verifier is deliberately **not** a plain hash of the passphrase: it
  is salted and costs a full PBKDF2 derivation per guess, so publishing it
  does not make the passphrase cheaper to attack than the ciphertext
  itself. Because the derived bits are the same bits that become the
  AES-GCM key, verification is free — one PBKDF2 pass per page load, then
  `importKey` on the bits already in hand.
- That AES-GCM key decrypts `site/data/listings.enc` and the photo blobs
  `site/data/photos/*.enc` in the browser. Open market data
  (`scenarios.json`, rates, indices) stays plaintext — it is not secret.
- Python side: `crypto_util.py` implements the identical PBKDF2 + AES-GCM
  parameters and owns `verifier_b64()`; `gen_gate.py` writes
  `{verifier, salt, iterations}`; `fairprice.py` reads/writes
  `data/listings.enc` using the passphrase from `IMOBILIEN_KEY` (in
  gitignored `.env`). Plaintext `data/listings.json` is a local working
  copy, gitignored.
- Failure messaging: a bare visit with no fragment and nothing stored
  leaves the neutral placeholder untouched. A candidate that was *present*
  but did not verify gets a distinct Russian message asking the reader to
  reopen the original family link — enough for a parent to tell "my link
  got mangled" from "the site is broken", with no hint about the key.
- The passphrase must be a strong multi-word phrase (the verifier and salt
  are public, so brute-force resistance comes from passphrase entropy plus
  PBKDF2 cost). Current scheme: four random words from a 130-word Russian
  list plus a two-digit number, hyphen-separated — dictatable over the
  phone, ~35 bits of entropy, which combined with 600k PBKDF2 iterations
  puts a full search well out of reach of an interested seller or agent.
- Anti-indexing: `<meta name="robots" content="noindex, nofollow">` on all
  four pages. This meta tag plus the gate is the *real* protection.
  `site/robots.txt` is kept but is **best-effort only**: on GitHub Pages a
  project site is served under `https://<user>.github.io/imobilien/`, so
  the file deploys to `/imobilien/robots.txt` while crawlers only read
  `robots.txt` at the domain root — which this repo does not control.
  Do not treat `robots.txt` as load-bearing here; it is harmless and would
  start working only if the site ever moved to its own domain or a user
  Pages root.

What this does NOT protect: the open data files and the code are readable
by anyone browsing the GitHub repo — acceptable because they contain no
personal information (see section 9). Losing the passphrase only requires
re-encrypting the journal and sending a new link.

## 9. Privacy rules (public repository)

- No family names, phone numbers, or personal details anywhere in the repo.
- Listings: even inside the encrypted journal, use public listing URL and
  area-level location only (settlement name), never a full address or
  cadastral number — defense in depth if the passphrase ever leaks.
- Git author for this repo must be a personal identity, not the work email
  (the `<work email>` address must not appear in commits).
- Capital is only ever shown as the already-public 10–25 mln range and the
  three model levels.
- `.gitignore` covers `.env`, `data/listings.json`, and `data/photos/`
  from the first commit; the passphrase never appears in code, tests, or
  CI. Photos reach the repo only as encrypted blobs.

## 10. Error handling

- `update_all.py` continues past a failed source, keeps the previous data
  point, and prints a summary of which sources refreshed; the site shows
  per-source as-of dates, so stale data is visible rather than silent.
- Fetch scripts validate response shape before appending; a malformed
  response never corrupts the history file (write via temp file + rename).
- `model.py` fails loudly on missing required inputs (better no update than
  a wrong chart for the parents).

## 11. Testing

- `pytest` unit tests for `model.py` and `fairprice.py` math (known inputs →
  known outputs, inflation adjustment, band ordering invariants).
- `crypto_util.py` round-trip test (encrypt → decrypt) with a test-only
  passphrase, plus a fixed-vector test guaranteeing the Python parameters
  match the documented WebCrypto parameters (PBKDF2 iterations, salt/IV
  layout), so a Python change can never silently break browser decryption.
- A schema check for each `data/*.json` file, run inside `update_all.py`.
- Site is static; a smoke test opens each page's JSON dependencies and
  asserts they parse and contain required keys; gate behavior is verified
  manually with a wrong key and the real key.

## 12. Build order (for the implementation plan)

1. Repo scaffolding, git init, `.gitignore` (`.env`, `data/listings.json`),
   Pages workflow.
2. Access gate: `crypto_util.py`, `gate.js`, digest/salt generation,
   round-trip tests.
3. Fetch scripts + data schemas (CBR, MOEX, crypto).
4. Scenario model + tests.
5. Fair-price module + encrypted listings journal + `add_listing.py`
   ingestion (including photo compression/encryption).
6. Site: verdict, scenarios, listings gallery, checklist pages (all gated).
7. First real data pull, first analysis pass in `notes/`, ingest the first
   real listing end-to-end.
