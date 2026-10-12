"""Fixed test cases for the listing checker: one good listing that must pass,
and bad listings that must each fail exactly the rule they break."""
import json
from pathlib import Path

import pytest

from checker import check_listing

PRODUCTS = {p["sku"]: p for p in json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "products.json").read_text(encoding="utf-8"))}

GOOD = {
    "title": "Little Fern Ribbed Romper in GOTS organic cotton",
    "description": (
        "A soft everyday romper for babies from 0-12 months, made from GOTS certified organic cotton. "
        "The ribbed knit stretches as your baby kicks, crawls and rolls, so it stays comfortable through "
        "a whole day of play and naps. Press studs run along the legs, which makes nappy changes quick, "
        "even at night. Fold-over cuffs keep little hands warm when it is cool outside. Choose Oat or Sage, "
        "and wash it at 40 degrees with the rest of the laundry."
    ),
    "bullets": [
        "GOTS certified organic cotton, soft on new skin",
        "Press studs along the legs for quick nappy changes",
        "Stretchy ribbed knit that moves with your baby",
        "Fold-over cuffs on the sleeves",
    ],
}


def failed(listing, sku="LF-1001"):
    return {r["rule"] for r in check_listing(PRODUCTS[sku], listing)["failed_rules"]}


def test_good_listing_passes():
    result = check_listing(PRODUCTS["LF-1001"], GOOD)
    assert result["passed"], result["failed_rules"]


@pytest.mark.parametrize("change, rule", [
    ({"title": "Little Fern Ribbed Romper " + "x" * 60}, "title length"),
    ({"title": "Ribbed Romper in organic cotton"}, "title has brand"),
    ({"description": "A soft romper for babies 0-12 months in organic cotton."}, "description length"),
    ({"bullets": GOOD["bullets"][:2]}, "bullet count"),
    ({"bullets": GOOD["bullets"][:3] + ["y" * 95]}, "bullet length"),
    ({"description": GOOD["description"].replace("0-12 months", "small babies")}, "age range mentioned"),
    ({"description": GOOD["description"] + " It is 100% safe."}, "no banned claims"),
    ({"description": GOOD["description"] + " Certified OEKO-TEX."}, "no invented certifications"),
    ({"description": GOOD["description"] + " Order now!"}, "no exclamation marks"),
    ({"description": GOOD["description"].replace(". The ribbed", " — the ribbed")}, "no long dashes"),
])
def test_each_rule_catches_its_mistake(change, rule):
    assert rule in failed({**GOOD, **change})


def test_missing_material_is_caught():
    listing = {**GOOD,
               "title": "Little Fern Ribbed Romper",
               "description": GOOD["description"].replace("GOTS certified organic cotton", "a soft fabric"),
               "bullets": ["Soft on new skin", "Press studs along the legs", "Stretchy ribbed knit"]}
    assert "materials mentioned" in failed(listing)


def test_age_range_with_words_is_accepted():
    listing = {**GOOD, "description": GOOD["description"].replace("0-12 months", "0 to 12 months")}
    assert "age range mentioned" not in failed(listing)
