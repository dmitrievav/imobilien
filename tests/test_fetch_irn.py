import sys
from unittest import mock

import pytest

sys.path.insert(0, "scripts")
import fetch_irn

CITIES_HTML = """
<table class="list1">
<tr><th>Рейтинг городов Подмосковья по стоимости квартир, руб./кв.м.</th>
<th>Июн 26</th><th>Мая 26</th></tr>
<tr>
  <td class="text-center"><label><input class="check-row" type="checkbox"
      name="district[]" value="380"></label></td>
  <td><a name="1"></a>1</td>
  <td class="text-center">&nbsp;</td>
  <td><a target="_blank"
      href="https://www.irn.ru/kvartiry/podmoskovie/dolgoprudniy/">
      Долгопрудный </a></td>
  <td class="text-right whitespace-nowrap"> 210 174 </td>
  <td class="text-right text-green"> +0,5% </td>
</tr>
<tr>
  <td class="text-center"><label><input class="check-row" type="checkbox"
      name="district[]" value="519"></label></td>
  <td><a name="17"></a>17</td>
  <td class="text-center text-red" title="изменение позиции"> -1 </td>
  <td><a target="_blank"
      href="https://www.irn.ru/kvartiry/podmoskovie/pushkino/">
      Пушкино </a></td>
  <td class="text-right whitespace-nowrap"> 153 304 </td>
  <td class="text-right text-green"> +0,5% </td>
</tr>
</table>
"""

REGION_HTML = """
<table class="index-table">
<tr><th class="center"><h3>Цены на недвижимость</h3></th>
    <th class="center">Июн 26</th><th class="center">Дек 25</th></tr>
<tr><td><a href="/gd/" class="black">Москва</a></td>
    <td class="center"> 299 543 </td>
    <td class="center color-green"> +4,8% </td></tr>
<tr><td><a href="/gd/novaya-moskva/" class="black">Новая Москва</a></td>
    <td class="center"> 218 533 </td>
    <td class="center color-green"> +4,8% </td></tr>
<tr><td><a href="/gd/podmoskovie/" class="black">Подмосковье</a></td>
    <td class="center"> 161 832 </td>
    <td class="center color-green"> +3,8% </td></tr>
</table>
<table class="index-table">
<tr><th class="center"><h3>Цены на жильё по типам домов</h3></th>
    <th class="center">Москва</th><th class="center">Новая Москва</th>
    <th class="center">Подмосковье</th></tr>
<tr><td>Старая и типовая советская панель</td>
    <td class="center">+6,1%</td><td class="center">-</td>
    <td class="center">+1,7%</td></tr>
<tr><td>Современный монолит-кирпич</td>
    <td class="center">+3,8%</td><td class="center">+2,9%</td>
    <td class="center">+3,7%</td></tr>
</table>
<table class="index-table">
<tr><th class="center"><h3>Цены на жилье по территориям за МКАД</h3></th>
    <th class="center">Июн 26</th><th class="center">Дек 25</th></tr>
<tr><td>Ближнее Подмосковье</td><td class="center">184 383</td>
    <td class="center">+5,6%</td></tr>
<tr><td>Среднее Подмосковье</td><td class="center">140 470</td>
    <td class="center">+2,0%</td></tr>
<tr><td>Дальнее Подмосковье</td><td class="center">112 209</td>
    <td class="center">+3,5%</td></tr>
</table>
"""

MOSCOW_TYPES_HTML = """
<table class="index-table">
<tr><th class="center"><h3>Цены на жильё по типам домов</h3></th>
    <th class="center">Руб.</th><th>Июн 26</th><th>Дек 25</th></tr>
<tr><td colspan="2">Старая панель (5-этажки и иные квартиры)</td>
    <td class="center">265 755</td>
    <td class="center color-green">+5,4%</td></tr>
<tr><td colspan="2">Современный монолит-кирпич (монолиты, кирпич)</td>
    <td class="center">298 030</td>
    <td class="center color-green">+3,8%</td></tr>
</table>
"""

PUSHKINO_HTML = """
<html><head><script>
window.Laravel = {csrfToken: 'TESTTOKEN123'};
</script></head><body>
<geo-chart chart-url="https://www.irn.ru/graph/services/index_history.php?geo_id=2480"
  geo-id="2480" :period="5"></geo-chart>
<div class="text-xl">153 304 руб.</div>
</body></html>
"""


def _resp(text, status=200, payload=None):
    r = mock.Mock()
    r.text = text
    r.status_code = status
    r.raise_for_status = mock.Mock()
    r.json = mock.Mock(return_value=payload or {})
    return r


# ---------------------------------------------------------------- parsing


def test_parse_cities_reads_name_and_price():
    cities = fetch_irn.parse_cities(CITIES_HTML)
    assert cities["Пушкино"] == 153304
    assert cities["Долгопрудный"] == 210174
    assert len(cities) == 2


def test_parse_cities_ignores_rank_and_percent_cells():
    """Rank ("17") and change ("+0,5%") must never be mistaken for a price."""
    assert set(fetch_irn.parse_cities(CITIES_HTML).values()) == {153304, 210174}


def test_labelled_prices_on_region_table():
    table = fetch_irn.find_table(REGION_HTML, "Цены на недвижимость")
    assert fetch_irn.labelled_prices(table) == {
        "Москва": 299543, "Новая Москва": 218533, "Подмосковье": 161832}


def test_labelled_prices_skips_header_row():
    table = fetch_irn.find_table(REGION_HTML, "по территориям за МКАД")
    prices = fetch_irn.labelled_prices(table)
    assert prices["Среднее Подмосковье"] == 140470
    assert not any("Июн" in k for k in prices)


def test_moscow_house_types_absolute_levels():
    types = fetch_irn.parse_house_type_prices(MOSCOW_TYPES_HTML)
    assert types["Старая панель (5-этажки и иные квартиры)"] == 265755
    assert types["Современный монолит-кирпич (монолиты, кирпич)"] == 298030


def test_podmoskovye_house_type_percentages():
    """Podmoskovye publishes only % change by house type, in the 4th column."""
    pct = fetch_irn.parse_house_type_changes(REGION_HTML)
    assert pct == {"Старая и типовая советская панель": 1.7,
                   "Современный монолит-кирпич": 3.7}


def test_parse_period_label():
    assert fetch_irn.parse_period(REGION_HTML) == "Июн 26"


def test_parse_geo_id():
    assert fetch_irn.parse_geo_id(PUSHKINO_HTML) == "2480"


def test_parse_csrf_token():
    assert fetch_irn.parse_csrf(PUSHKINO_HTML) == "TESTTOKEN123"


# ---------------------------------------------------------------- history


def test_implied_history_back_computes_levels():
    hist = fetch_irn.implied_history(153304, {1: 5.9, 10: 112.4}, this_year=2026)
    by_years = {h["years_ago"]: h for h in hist}
    # 153304 / 2.124 = 72177
    assert by_years[10]["implied_rub_m2"] == 72177
    assert by_years[10]["approx_year"] == 2016
    assert by_years[1]["implied_rub_m2"] == 144763  # 153304 / 1.059
    assert by_years[1]["change_pct"] == 5.9


def test_implied_history_sorted_and_rejects_impossible_drop():
    """A -100% change would divide by zero; it must be dropped, not crash."""
    hist = fetch_irn.implied_history(100000, {1: -100.0, 5: 10.0})
    assert [h["years_ago"] for h in hist] == [5]


# ---------------------------------------------------------------- failures


def test_find_table_raises_when_heading_gone():
    """The single most likely breakage: IRN renames or drops a table."""
    with pytest.raises(ValueError, match="no table"):
        fetch_irn.find_table(REGION_HTML, "Цены на вертолётные площадки")


def test_parse_cities_raises_on_empty_table():
    with pytest.raises(ValueError, match="no city rows"):
        fetch_irn.parse_cities("<table><tr><td>nothing here</td></tr></table>")


def test_fetch_geo_diffs_survives_a_failing_period():
    """One bad period must not lose the other four."""
    calls = []

    def post(url, **kw):
        years = kw["json"]["diff_years"]
        calls.append(years)
        if years == 3:
            raise fetch_irn.requests.RequestException("boom")
        return _resp("", payload={"diff": 10.0 * years})

    session = mock.Mock()
    session.post = post
    session.get = mock.Mock(return_value=_resp(PUSHKINO_HTML))
    diffs = fetch_irn.fetch_geo_diffs(session, "2480", "TOK", "http://x/")
    assert 3 not in diffs
    assert diffs[10] == 100.0
    assert len(diffs) == len(fetch_irn.DIFF_YEARS) - 1


def test_main_appends(tmp_path):
    def get(url, **kw):
        if "ceny-po-rayonam" in url:
            return _resp(CITIES_HTML)
        if "novaya-moskva-i-podmoskovie" in url:
            return _resp(REGION_HTML)
        if url.rstrip("/").endswith("/index"):
            return _resp(MOSCOW_TYPES_HTML)
        return _resp(PUSHKINO_HTML)

    session = mock.Mock()
    session.get = get
    session.post = mock.Mock(return_value=_resp("", payload={"diff": 112.4}))
    session.headers = {}
    with mock.patch("fetch_irn.requests.Session", return_value=session), \
         mock.patch("fetch_irn.DATA_PATH", tmp_path / "irn_prices.json"):
        assert fetch_irn.main() is True
        assert fetch_irn.main() is False  # same date -> no duplicate


def test_main_records_the_numbers_we_care_about(tmp_path):
    import json

    def get(url, **kw):
        if "ceny-po-rayonam" in url:
            return _resp(CITIES_HTML)
        if "novaya-moskva-i-podmoskovie" in url:
            return _resp(REGION_HTML)
        if url.rstrip("/").endswith("/index"):
            return _resp(MOSCOW_TYPES_HTML)
        return _resp(PUSHKINO_HTML)

    session = mock.Mock()
    session.get = get
    session.post = mock.Mock(return_value=_resp("", payload={"diff": 112.4}))
    session.headers = {}
    path = tmp_path / "irn_prices.json"
    with mock.patch("fetch_irn.requests.Session", return_value=session), \
         mock.patch("fetch_irn.DATA_PATH", path):
        fetch_irn.main()
    point = json.loads(path.read_text())["points"][0]
    assert point["period"] == "Июн 26"
    assert point["cities_rub_m2"]["Пушкино"] == 153304
    assert point["region_rub_m2"]["Подмосковье"] == 161832
    assert point["podmoskovye_zones_rub_m2"]["Среднее Подмосковье"] == 140470
    assert point["moscow_by_house_type_rub_m2"][
        "Старая панель (5-этажки и иные квартиры)"] == 265755
    assert point["reference_town"]["name"] == "Пушкино"
    assert point["reference_town"]["rub_m2"] == 153304
    assert point["reference_town"]["implied_history"]


def test_http_failure_propagates(tmp_path):
    session = mock.Mock()
    session.get = mock.Mock(side_effect=fetch_irn.requests.RequestException("down"))
    session.headers = {}
    with mock.patch("fetch_irn.requests.Session", return_value=session), \
         mock.patch("fetch_irn.DATA_PATH", tmp_path / "irn_prices.json"), \
         pytest.raises(fetch_irn.requests.RequestException):
        fetch_irn.main()
