# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Decision-support project for a family purchase of a house or flat in
Pushkinsky district, Moscow region (budget 10–25 mln RUB): fair-price
assessment of concrete listings (segment-aware: dacha / year-round house /
flat), scenario comparison of the capital against alternatives
(deposits, OFZ, TMOS/TPAY, gold, currency, crypto), and a simple static
site that presents the conclusion to elderly (70+) parents.

**Status: implemented, deploy pending.** The pipeline (CBR / MOEX / crypto
fetchers), the scenario model, the fair-price assessment with the encrypted
listings journal, and the gated four-page site all work end to end; 37+
pytest tests are green. What is left is the first public push and the
GitHub Pages deploy (`.github/workflows/pages.yml`), plus the **[refine]**
assumptions tracked in `notes/methodology.md`. Photos are supported by
`add_listing.py` but none have been ingested yet, so the gallery currently
renders text-only cards.

The authoritative design is
`docs/superpowers/specs/2026-07-25-imobilien-design.md` — read it before
changing anything structural; it is kept in sync with the implementation.

## Architecture

Static-data pipeline published via GitHub Pages, no backend, no site build
step:

- `scripts/fetch_*.py` append dated points to `data/*.json` (append-only
  history; sources: CBR, MOEX ISS, CoinGecko; realty benchmarks and
  deposit rates are entered semi-manually).
- `scripts/model.py` computes capital scenarios (all in inflation-adjusted
  RUB, three capital levels: 10 / 17.5 / 25 mln) → `site/data/scenarios.json`.
- `scripts/add_listing.py` ingests a listing (fields extracted by a Claude
  agent from a listing URL — Cian/Avito block plain scripts, so extraction
  is agent-driven, never automated) + photos; `scripts/fairprice.py`
  assigns a fair-price verdict vs. district benchmarks.
- `site/` is plain HTML + vendored Chart.js, Russian, large fonts, four
  pages; `site/listings.html` is a card gallery of considered houses.
- Update cycle: run scripts → review diff → commit → push → Pages
  redeploys. Runs are occasional and manual (user or Claude agent).

## Access gate and crypto invariants

The site is gated by a "magic URL": the passphrase lives in the URL
fragment, and the same PBKDF2 derivation both verifies it and produces the
AES-GCM key that decrypts the listings journal and photos in the browser.

- `site/data/gate.json` publishes `{verifier, salt, iterations}`. The
  `verifier` is `base64(SHA256(PBKDF2-HMAC-SHA256(passphrase, salt,
  iterations, 32)))` — salted and PBKDF2-expensive, so publishing it costs
  nothing. It is NOT a plain hash of the passphrase; the old unsalted
  `digest` field is gone and must not come back.
- `gate.js` runs ONE PBKDF2 pass per page load (`deriveBits`), SHA-256s the
  bits to compare against `verifier`, then `importKey`s the SAME bits as
  the AES-GCM key. Never derive twice.
- `scripts/crypto_util.py` and `gate.js` MUST use identical PBKDF2/AES-GCM
  parameters; `tests/vectors/gate_vector.json` + `tests/test_crypto_util.py`
  pin both the verifier and the blob format. Never change parameters on one
  side only — old ciphertext and the old gate.json stay in git history
  forever, so a weakening is not retroactively fixable.
- Market data stays plaintext (not secret); only the listings journal and
  photos are encrypted.
- Anti-indexing rests on the per-page `noindex` meta plus the gate.
  `site/robots.txt` deploys to `/imobilien/robots.txt` on project Pages,
  which no crawler reads — best-effort only, not protection.

## Privacy rules (the repo is PUBLIC)

Non-negotiable, enforced from the first commit:

- `.gitignore` must cover `.env` (holds `IMOBILIEN_KEY` passphrase),
  `data/listings.json`, `data/photos/`. Plaintext journal and photos never
  reach git — only `*.enc` blobs do.
- No family names, phone numbers, full addresses, or cadastral numbers
  anywhere — even inside encrypted payloads (settlement name + listing URL
  only).
- Git author must be the personal identity (`ave.dmitriev@gmail.com`),
  never the work email.

## Conventions

- Site-facing content (HTML text, chart labels, verdicts) is Russian and
  written for elderly readers: large fonts, few numbers per screen, no
  jargon. Code, comments, and repo docs are English.
- Model and fair-price assumptions are not hardcoded opinions: every
  assumption lives in `notes/methodology.md` with its as-of date, and
  model outputs echo the dates so the site can show data freshness.
- Data files are append-only history; fetch scripts must fail soft
  (keep the previous point, report the failure) and never corrupt a
  history file on a malformed response.

## Commands

- `python scripts/update_all.py` — refresh all data sources, rerun the
  model AND re-run the fair-price assessment (so edited benchmarks in
  `data/realty.json` reach the verdicts the site shows). The assessment
  step needs `IMOBILIEN_KEY`; without it the run reports a skip rather
  than failing.
- `python scripts/add_listing.py` — ingest a new listing (agent-supplied JSON).
- `pytest` — model/fair-price math, crypto round-trip and fixed-vector tests.
