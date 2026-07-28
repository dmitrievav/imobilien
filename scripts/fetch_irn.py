"""IRN.RU price-per-m2 benchmarks: the base our valuation compares against.

Why this exists: the base price per square metre was the weakest input in the
whole model. Flats used the median of three or four asking prices read off a
single listing page; houses and dachas used a flat guess. IRN.RU publishes a
monthly index of the average asking price per square metre computed over its
own whole database -- for every town in Podmoskovye, for the near/middle/far
Podmoskovye belts, and for Moscow broken down by house type. Fifty towns
indexed consistently every month is a far broader base than four listings,
and because we append monthly the series accumulates from the day we start.

What this does NOT give us, and must not be read as giving us:

  * IRN indexes FLATS only. Houses and dachas stay unmeasured; no number in
    this file is a house or dacha benchmark.
  * These are asking prices, exactly like ours -- not registered
    transactions. IRN's index is broader and consistently computed, which is
    a real improvement, but it is not a different KIND of measurement.
  * By-house-type absolute levels are published for Moscow only. For
    Podmoskovye IRN publishes the by-type change in percent and no level, so
    that is what we store: percentages, honestly labelled as percentages.

On long history: IRN's since-2000 charts are server-rendered images under
/graph/, which robots.txt disallows, so we never touch them -- and reading
values off a coarse y-axis would be less precise than what we already have.
Instead /api/v1/calc/geo/diff returns a town's cumulative percentage change
over 1/2/3/5/10 years as JSON. Dividing today's level by those ratios gives
five dated anchor points per town: coarse, but arithmetic on published
numbers rather than pixel-reading.

Robots: irn.ru/robots.txt disallows /graph/, /*?* (i.e. EVERY query-string
URL) and the query forms of the calculators (/iprice/?, /compare/?, /calc/?).
Every URL below is a clean path carrying no query string, plus one POST to
/api/v1/ -- none of which is disallowed. The browser User-Agent is required:
irn.ru answers the default urllib/requests agent with a tiny error stub.
"""
import html
import re
import sys
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
import store

DATA_PATH = Path("data/irn_prices.json")
TIMEOUT = 30

BASE = "https://www.irn.ru"
CITIES_URL = f"{BASE}/kvartiry/podmoskovie/ceny-po-rayonam-i-gorodam/"
REGION_URL = f"{BASE}/index/novaya-moskva-i-podmoskovie/"
MOSCOW_URL = f"{BASE}/index/"
DIFF_URL = f"{BASE}/api/v1/calc/geo/diff"

# The town our two flats are in, so its own series is the one we anchor on.
# The page is fetched anyway (for the CSRF token the diff API wants), and the
# geo id is read back out of it rather than hardcoded, so a renumbering on
# IRN's side surfaces as a parse failure instead of silently wrong history.
REFERENCE_TOWN = "Пушкино"
REFERENCE_URL = f"{BASE}/kvartiry/podmoskovie/pushkino/"
DIFF_YEARS = (1, 2, 3, 5, 10)

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")

TABLE_RE = re.compile(r"(?s)<table[^>]*>.*?</table>")
ROW_RE = re.compile(r"(?s)<tr[^>]*>(.*?)</tr>")
CELL_RE = re.compile(r"(?s)<t[dh][^>]*>(.*?)</t[dh]>")
SCRIPT_RE = re.compile(r"(?s)<(script|style)\b.*?</\1>")
CITY_LINK_RE = re.compile(
    r'href="[^"]*/kvartiry/podmoskovie/[a-z0-9-]+/"[^>]*>\s*([^<]+?)\s*</a>')
# Grouped thousands only: matches "153 304" and "88 371" but never a rank
# ("17"), a change ("+0,5%") or a bare id ("2480").
PRICE_RE = re.compile(r"^\d{1,3}(?: \d{3})+$")
PCT_RE = re.compile(r"^([+-]?\d+(?:,\d+)?)\s*%$")
PERIOD_RE = re.compile(
    r"\b(Янв|Фев|Мар|Апр|Мая|Май|Июн|Июл|Авг|Сен|Окт|Ноя|Дек)\s+(\d{2})\b")
GEO_ID_RE = re.compile(r'geo-id="(\d+)"')
CSRF_RE = re.compile(r"csrfToken:\s*'([^']+)'")

HOUSE_TYPE_HEADING = "по типам домов"
# Column 3 of the cross-region by-type table is Podmoskovye (1 = Moscow,
# 2 = New Moscow).
PODMOSKOVYE_COLUMN = 3


def _text(fragment):
    """Visible text of an HTML fragment, whitespace collapsed.

    Non-breaking spaces become ordinary ones: IRN separates thousands with
    them, and PRICE_RE expects a plain space.
    """
    out = html.unescape(re.sub(r"(?s)<[^>]+>", " ", fragment))
    return re.sub(r"\s+", " ", out.replace("\u00a0", " ")).strip()


def _price(cell):
    return int(cell.replace(" ", "")) if PRICE_RE.match(cell) else None


def _pct(cell):
    m = PCT_RE.match(cell)
    return float(m.group(1).replace(",", ".")) if m else None


def tables(page):
    return TABLE_RE.findall(SCRIPT_RE.sub(" ", page))


def find_table(page, heading):
    """First table whose text contains `heading`.

    Selecting by heading rather than by position means IRN inserting a table
    cannot silently shift us onto the wrong numbers.
    """
    for table in tables(page):
        if heading in _text(table):
            return table
    raise ValueError(f"no table matching {heading!r}")


def rows(table):
    return [[_text(c) for c in CELL_RE.findall(raw)] for raw in ROW_RE.findall(table)]


def labelled_prices(table):
    """{first cell: first grouped-thousands number in the row}."""
    out = {}
    for cells in rows(table):
        if len(cells) < 2 or not cells[0]:
            continue
        prices = [p for p in (_price(c) for c in cells[1:]) if p is not None]
        if prices:
            out[cells[0]] = prices[0]
    return out


def parse_cities(page):
    """{town: RUB/m2} from the Podmoskovye town ranking."""
    out = {}
    for raw in ROW_RE.findall(SCRIPT_RE.sub(" ", page)):
        link = CITY_LINK_RE.search(raw)
        if not link:
            continue
        cells = [_text(c) for c in CELL_RE.findall(raw)]
        prices = [p for p in (_price(c) for c in cells) if p is not None]
        if prices:
            out[_text(link.group(1))] = prices[0]
    if not out:
        raise ValueError("no city rows found in the Podmoskovye ranking")
    return out


def parse_house_type_prices(page):
    """{house type: RUB/m2} -- Moscow only; IRN publishes no such levels
    for Podmoskovye."""
    return labelled_prices(find_table(page, HOUSE_TYPE_HEADING))


def parse_house_type_changes(page):
    """{house type: % change} for Podmoskovye, from the cross-region table."""
    out = {}
    for cells in rows(find_table(page, HOUSE_TYPE_HEADING)):
        if len(cells) <= PODMOSKOVYE_COLUMN or not cells[0]:
            continue
        pct = _pct(cells[PODMOSKOVYE_COLUMN])
        if pct is not None:
            out[cells[0]] = pct
    return out


def parse_period(page):
    """The month the index refers to, e.g. "Июн 26"."""
    m = PERIOD_RE.search(_text(SCRIPT_RE.sub(" ", page)))
    return f"{m.group(1)} {m.group(2)}" if m else None


def parse_geo_id(page):
    m = GEO_ID_RE.search(page)
    if not m:
        raise ValueError("no geo-id on the reference town page")
    return m.group(1)


def parse_csrf(page):
    m = CSRF_RE.search(page)
    if not m:
        raise ValueError("no CSRF token on the reference town page")
    return m.group(1)


def parse_level(page):
    """Today's RUB/m2 as printed on a town page ("153 304 руб.")."""
    m = re.search(r"([\d]{1,3}(?:[   ]\d{3})+)\s*руб", page)
    return int(re.sub(r"\D", "", m.group(1))) if m else None


def fetch_geo_diffs(session, geo_id, token, referer):
    """{years: cumulative % change} for one town.

    One period failing must not cost us the other four, so each is tried
    independently.
    """
    out = {}
    for years in DIFF_YEARS:
        try:
            r = session.post(DIFF_URL, json={"diff_years": years, "geo_id": geo_id},
                             headers={"X-CSRF-TOKEN": token,
                                      "X-Requested-With": "XMLHttpRequest",
                                      "Referer": referer,
                                      "Accept": "application/json"},
                             timeout=TIMEOUT)
            r.raise_for_status()
            diff = r.json().get("diff")
            if diff is not None:
                out[years] = round(float(diff), 2)
        except (requests.RequestException, ValueError):
            continue
    return out


def implied_history(level_now, diffs, this_year=None):
    """Back-compute past price levels from today's level and % changes.

    level_then = level_now / (1 + pct/100). Coarse -- five points, and the
    year is approximate because the change is quoted against the same month
    N years back -- but it is arithmetic on published numbers.
    """
    this_year = this_year or date.today().year
    out = []
    for years in sorted(diffs):
        ratio = 1 + diffs[years] / 100
        if ratio <= 0:
            continue
        out.append({"years_ago": years,
                    "approx_year": this_year - years,
                    "change_pct": diffs[years],
                    "implied_rub_m2": round(level_now / ratio)})
    return out


def main():
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    def get(url):
        r = session.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        return r.text

    cities = parse_cities(get(CITIES_URL))
    region_page = get(REGION_URL)
    reference_page = get(REFERENCE_URL)

    level = cities.get(REFERENCE_TOWN) or parse_level(reference_page)
    diffs = fetch_geo_diffs(session, parse_geo_id(reference_page),
                            parse_csrf(reference_page), REFERENCE_URL)

    point = {
        "date": date.today().isoformat(),
        "period": parse_period(region_page),
        "source": f"{CITIES_URL} , {REGION_URL} , {MOSCOW_URL} , "
                  f"{DIFF_URL} (POST diff_years+geo_id)",
        "note": "IRN.RU index of average ASKING price per m2, FLATS ONLY -- "
                "no house or dacha benchmark is derivable from this file",
        "region_rub_m2": labelled_prices(
            find_table(region_page, "Цены на недвижимость")),
        "podmoskovye_zones_rub_m2": labelled_prices(
            find_table(region_page, "по территориям за МКАД")),
        "cities_rub_m2": cities,
        "podmoskovye_by_house_type_change_pct": parse_house_type_changes(region_page),
        "reference_town": {
            "name": REFERENCE_TOWN,
            "rub_m2": level,
            "change_pct_by_years": diffs,
            "implied_history": implied_history(level, diffs) if level else [],
            "history_note": "levels back-computed from today's level and IRN's "
                            "cumulative % change; five anchors, not a monthly series",
        },
    }
    try:
        point["moscow_by_house_type_rub_m2"] = parse_house_type_prices(get(MOSCOW_URL))
    except (requests.RequestException, ValueError):
        point["moscow_by_house_type_rub_m2"] = {}

    return store.append_point(DATA_PATH, point,
                              ["date", "region_rub_m2", "cities_rub_m2"])


if __name__ == "__main__":
    print("irn prices:", "appended" if main() else "already have today")
