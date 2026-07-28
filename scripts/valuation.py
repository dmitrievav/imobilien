"""Per-listing valuation by comparison with adjustments.

The method appraisers actually use: start from a typical price per m² for the
segment, then correct for how this particular object differs — floor, age,
walls, renovation, utilities, distance, plot size. The output is a RANGE, not
a point, because every coefficient here is a practice-based estimate rather
than a regression on a large sample, and the band widens honestly whenever
the inputs are thin.

Two guards against fooling ourselves:
  * when the base comes from listing-specific comparables (same building or
    next door), the adjustments are damped, because those comparables already
    embed typical renovation and building type — applying full corrections on
    top would double-count;
  * a base that is itself an unmeasured estimate widens the band a lot, so a
    confident-looking verdict cannot rest on a guessed benchmark.
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import store

FACTORS_PATH = Path("data/valuation_factors.json")
REALTY_PATH = Path("data/realty.json")

RENOVATION_KEYWORDS = [
    ("designer", "designer"), ("дизайнер", "designer"),
    ("euro", "euro"), ("евро", "euro"), ("quality renovation", "euro"),
    ("cosmetic", "cosmetic"), ("косметич", "cosmetic"),
    ("without renovation", "none"), ("без ремонта", "none"),
]
RENOVATION_RU = {"none": "без ремонта", "cosmetic": "косметический ремонт",
                 "euro": "хороший ремонт", "designer": "дизайнерский ремонт"}
# The journal stores source-language values; the family reads Russian.
WALL_RU = {"panel": "панельный", "brick": "кирпичный", "monolith": "монолитный",
           "block": "блочный", "timber (brus)": "из бруса", "log": "бревенчатый",
           "frame": "каркасный", "aerated concrete": "из газобетона"}
EXTRA_RU = {"banya/sauna": "баня", "terrace": "терраса", "garage": "гараж"}


def load_factors(path=FACTORS_PATH):
    return json.loads(Path(path).read_text())


def latest_benchmarks(path=REALTY_PATH):
    """Segment -> {price_per_m2, estimated}. Points are chronological; last wins."""
    out = {}
    for pt in store.load(path)["points"]:
        out[pt["segment"]] = {"price_per_m2": pt["price_per_m2"],
                              "estimated": bool(pt.get("estimated"))}
    return out


def renovation_of(listing):
    """Explicit field wins; otherwise read it off the extras text."""
    if listing.get("renovation"):
        return listing["renovation"]
    text = " ".join(listing.get("extras") or []).lower()
    for needle, value in RENOVATION_KEYWORDS:
        if needle in text:
            return value
    return None


def _band_step(value, table):
    for row in table:
        if value < row["until"]:
            return row
    return table[-1]


def _floor_kind(floor):
    """'8/9' -> middle, '1/9' -> first, '9/9' -> last."""
    if not floor or "/" not in str(floor):
        return None
    try:
        cur, top = (int(x) for x in str(floor).split("/"))
    except ValueError:
        return None
    if cur == 1:
        return "first"
    return "last" if cur == top else "middle"


def _flat_adjustments(listing, f):
    adj = []
    kind = _floor_kind(listing.get("floor"))
    if kind:
        why = {"first": "первый этаж", "last": "последний этаж", "middle": "не первый и не последний этаж"}
        adj.append(("Этаж", f["floor"][kind], why[kind]))
    if listing.get("year_built"):
        row = _band_step(listing["year_built"], f["year_built"])
        adj.append(("Возраст дома", row["pct"], row["why_ru"]))
    wall = (listing.get("wall_material") or "").lower()
    if wall in f["wall_material"]:
        adj.append(("Материал дома", f["wall_material"][wall], WALL_RU.get(wall, wall)))
    ren = renovation_of(listing)
    if ren in f["renovation"]:
        adj.append(("Ремонт", f["renovation"][ren], RENOVATION_RU[ren]))
    if (listing.get("kitchen_m2") or 0) >= f["kitchen_large_m2"]:
        adj.append(("Кухня", f["kitchen_large_pct"], f"кухня {listing['kitchen_m2']} м²"))
    if (listing.get("ceiling_m") or 0) >= f["ceiling_tall_m"]:
        adj.append(("Потолки", f["ceiling_tall_pct"], f"потолки {listing['ceiling_m']} м"))
    area = listing.get("flat_m2") or 0
    # Unit price is a power function of area (C = b·S^n) with the "coefficient of
    # deceleration" n from a matched-pair regression, not a step function. The
    # exact form compares against each analogue's area; lacking those, we compare
    # against the segment's reference area.
    if area:
        pct = (area / f["reference_area_m2"]) ** f["area_exponent"] - 1
        adj.append(("Площадь", pct,
                    f"{area} м² против типовых {f['reference_area_m2']} м²: "
                    "чем больше, тем дешевле метр"))
    return adj


def _house_adjustments(listing, f):
    adj = []
    u = listing.get("utilities") or {}
    if u.get("heating"):
        gas = "yes" if "gas" in str(u["heating"]).lower() else "no"
        adj.append(("Газ", f["gas"][gas], "газ в доме" if gas == "yes" else "газа нет"))
    if u.get("water") or u.get("sewage"):
        both = f"{u.get('water')} {u.get('sewage')}".lower()
        key = "central" if "central" in both else "own"
        adj.append(("Вода и канализация", f["water_sewage"][key],
                    "центральные" if key == "central" else "скважина и септик"))
    cat = listing.get("land_category")
    if cat in f["land_category"]:
        adj.append(("Категория земли", f["land_category"][cat],
                    "ИЖС" if cat == "IZhS" else "СНТ"))
    wall = (listing.get("wall_material") or "").lower()
    if wall in f["wall_material"]:
        adj.append(("Материал стен", f["wall_material"][wall], WALL_RU.get(wall, wall)))
    if listing.get("year_built"):
        row = _band_step(listing["year_built"], f["year_built"])
        adj.append(("Возраст дома", row["pct"], row["why_ru"]))
    if listing.get("mkad_km") is not None:
        row = _band_step(listing["mkad_km"], f["mkad_km"])
        adj.append(("Удалённость", row["pct"], row["why_ru"]))
    land = listing.get("land_sotki") or 0
    steps = int(max(0, land - f["reference_land_sotki"]) // f["land_step_sotki"])
    if steps:
        pct = min(f["land_step_cap_pct"], steps * f["land_step_pct"])
        adj.append(("Участок", pct, f"{land} соток"))
    ren = renovation_of(listing)
    if ren in f["renovation"]:
        adj.append(("Ремонт", f["renovation"][ren], RENOVATION_RU[ren]))
    for extra, pct in f["extras"].items():
        if extra in (listing.get("extras") or []):
            name = EXTRA_RU.get(extra, extra)
            adj.append((name[:1].upper() + name[1:], pct, "есть"))
    return adj


def variation(values):
    """Coefficient of variation — the appraiser's homogeneity check.

    Reported as an accuracy driver AND as a veto: past the threshold the
    comparables are too unlike each other for their average to mean anything.
    Note what it does not measure: the spread of the inputs, not the accuracy
    of the answer. Four near-identical listings give a tiny V while still
    being four asking prices from one street.
    """
    if not values or len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return (var ** 0.5) / mean


def homogeneity_label(v, cfg):
    if v is None:
        return None
    for row in cfg["homogeneity"]["bands_ru"]:
        if v < row["until"]:
            return row["label_ru"]
    return cfg["homogeneity"]["bands_ru"][-1]["label_ru"]


def bargaining_coef(listing, cfg):
    """Asking price -> expected transaction price. Sellers close below the ad."""
    b = cfg["bargaining"]
    if listing["segment"] != "flat":
        return b["house_coef"], b["house_note_ru"]
    area = listing.get("flat_m2") or 0
    for row in b["flat_by_area"]:
        if area <= row["until_m2"]:
            return row["coef"], b["source_ru"]
    return b["flat_by_area"][-1]["coef"], b["source_ru"]


def _band_pct(cfg, has_comparables, base_estimated, missing, v):
    """Accuracy band: the measured spread of the comparables, floored at the
    base assumption, plus penalties for everything we had to guess."""
    b = cfg["band"]
    pct = max(b["base_pct"], v or 0) + missing * b["per_missing_field_pct"]
    if not has_comparables:
        pct += b["no_comparables_pct"]
    if base_estimated:
        pct += b["estimated_base_pct"]
    return min(b["max_pct"], pct)


def estimate(listing, benchmarks, cfg=None):
    """Fair-value range for one listing, with the reasoning attached."""
    cfg = cfg or load_factors()
    is_flat = listing["segment"] == "flat"
    kind = "flat" if is_flat else "house"
    f = cfg[kind]
    area = listing.get("flat_m2") if is_flat else listing.get("house_m2")
    if not area:
        raise ValueError(f"{listing.get('id')}: no area to value")

    comps = listing.get("comparables_per_m2")
    if comps:
        base = statistics.median(comps)
        base_why = f"медиана {len(comps)} похожих объявлений рядом"
        base_estimated = False
    else:
        bench = benchmarks[listing["segment"]]
        base = bench["price_per_m2"]
        base_estimated = bench["estimated"]
        base_why = ("средняя по округу для этого типа жилья"
                    + (" — оценка, не измерение" if base_estimated else ""))

    weight = cfg["comparable_adjustment_weight"] if comps else 1.0
    raw = _flat_adjustments(listing, f) if is_flat else _house_adjustments(listing, f)
    # A zero correction is kept on purpose: "30 km from MKAD, typical, no
    # adjustment" tells the reader the factor was weighed, not overlooked.
    adjustments = [{"name_ru": n, "pct": round(p * weight, 4), "why_ru": w}
                   for n, p, w in raw]

    multiplier = 1.0
    for a in adjustments:
        multiplier *= 1 + a["pct"]

    per_m2 = base * multiplier
    fair = per_m2 * area
    missing = sum(1 for key in f["key_fields"]
                  if key == "renovation" and renovation_of(listing) is None
                  or key != "renovation" and listing.get(key) in (None, "", {}))

    # Measured spread of the comparables drives the accuracy band and can veto
    # the whole estimate — the appraiser's homogeneity gate.
    v = variation(comps) if comps and len(comps) > 1 else None
    band = _band_pct(cfg, bool(comps), base_estimated, missing, v)
    low, high = fair * (1 - band), fair * (1 + band)

    price = listing["price_rub"]
    refuse = v is not None and v > cfg["homogeneity"]["refuse_above"]
    if refuse:
        verdict = "unreliable"
    else:
        verdict = "below" if price < low else "above" if price > high else "inside"

    # What the object is likely to actually change hands for, and therefore how
    # far down it is worth negotiating.
    coef, coef_why = bargaining_coef(listing, cfg)
    return {"base_per_m2": round(base), "base_why_ru": base_why,
            "adjustments": adjustments,
            "adjustment_weight": weight,
            "per_m2": round(per_m2), "price_per_m2": round(price / area),
            "fair": round(fair), "low": round(low), "high": round(high),
            "band_pct": round(band, 4), "missing_fields": missing,
            "variation_pct": None if v is None else round(v, 4),
            "homogeneity_ru": homogeneity_label(v, cfg),
            "bargaining_coef": coef, "bargaining_why_ru": coef_why,
            "likely_deal": round(fair * coef),
            "vs_fair_pct": round(price / fair - 1, 4),
            "verdict": verdict}
