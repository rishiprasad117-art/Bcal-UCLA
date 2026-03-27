"""
tagger.py — fetches tags and nutrition info for a canonical food item.

food_tags.csv is the internal database of what we know about each food item:
  - semantic tags used for scoring (e.g. "grilled", "fried", "protein", "veggies")
  - nutrition per serving (calories, protein, fat, carbs)
  - dietary flags (vegetarian, vegan, halal)
  - allergens
  - data_quality: how reliable is this entry?

UCLA nutrition data is often missing or approximate. The data_quality field tracks this.

TODO: Connect data_quality="missing" items to a nutrition fetch pipeline that pulls
      from UCLA dining's official nutrition pages to fill in gaps over time.
"""

import csv
import os

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_FOOD_TAGS_CSV = os.path.join(_DATA_DIR, "food_tags.csv")

# Module-level cache: loaded once on first call
_FOOD_TAGS: dict | None = None


def _load_food_tags() -> dict:
    """
    Load food_tags.csv into a dict keyed by lowercased canonical_name.
    Parses all fields into their proper Python types.
    """
    global _FOOD_TAGS
    if _FOOD_TAGS is not None:
        return _FOOD_TAGS

    _FOOD_TAGS = {}
    with open(_FOOD_TAGS_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row["canonical_name"].strip().lower()

            # Parse comma-separated tags into a list, stripping whitespace
            raw_tags = row["tags"].strip()
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()] if raw_tags else []

            # Parse comma-separated allergens into a list
            raw_allergens = row["allergens"].strip()
            allergens = [a.strip().lower() for a in raw_allergens.split(",") if a.strip()] if raw_allergens else []

            # Parse boolean fields safely: treat anything other than "true" as False
            def parse_bool(val: str) -> bool:
                return val.strip().lower() == "true"

            # Parse numeric fields safely: blank cells become 0.0
            def parse_float(val: str) -> float:
                v = val.strip()
                return float(v) if v else 0.0

            _FOOD_TAGS[key] = {
                "canonical_name": row["canonical_name"].strip(),
                "category": row["category"].strip(),
                "tags": tags,
                "calories": parse_float(row["calories"]),
                "protein_grams": parse_float(row["protein_grams"]),
                "fat_grams": parse_float(row["fat_grams"]),
                "carb_grams": parse_float(row["carb_grams"]),
                "vegetarian": parse_bool(row["vegetarian"]),
                "vegan": parse_bool(row["vegan"]),
                "halal": parse_bool(row["halal"]),
                "allergens": allergens,
                "data_quality": row["data_quality"].strip(),
            }
    return _FOOD_TAGS


def get_tags_and_nutrition(canonical_name: str) -> dict:
    """
    Return the full tags + nutrition dict for a canonical food item.

    If the canonical name is not found (unknown item, not yet in our database),
    returns a safe stub with _unknown=True. This prevents pipeline crashes on
    unfamiliar items and lets them pass through with a score of 0.

    The safe stub defaults all dietary booleans to False — this is intentional.
    We never assume an unknown item is safe for dietary restrictions.

    TODO: Unknown items should be flagged for later addition to food_tags.csv.
    """
    food_tags = _load_food_tags()
    key = canonical_name.strip().lower()

    if key in food_tags:
        return food_tags[key]

    # Safe stub for unknown items
    return {
        "canonical_name": canonical_name,
        "category": "unknown",
        "tags": [],
        "calories": 0.0,
        "protein_grams": 0.0,
        "fat_grams": 0.0,
        "carb_grams": 0.0,
        "vegetarian": False,   # Safe default: don't assume compliant
        "vegan": False,
        "halal": False,
        "allergens": [],
        "data_quality": "missing",
        "_unknown": True,      # Flag for response layer to surface to user
    }
