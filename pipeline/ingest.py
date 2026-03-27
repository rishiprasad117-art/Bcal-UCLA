"""
pipeline/ingest.py — transform raw scraper CSVs into the schema that
recommender/menu_loader.py expects.

Reads:  data/raw/*.csv           (output from each scraper)
Writes:
    data/daily_menu.csv          — today's menu rows (overwritten each run)
    data/food_tags.csv           — enriched with new items; existing rows preserved
    data/item_translator.csv     — enriched with new translations; existing rows preserved
    data/unresolved_items.csv    — items flagged for manual review (overwritten each run)

Run:
    python pipeline/ingest.py
    python pipeline/ingest.py --date 2026-03-25
"""

import argparse
import csv
import datetime
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (all relative to the project root, not this file's location)
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
_RAW_DIR = _ROOT / "data" / "raw"
_DAILY_MENU_CSV = _ROOT / "data" / "daily_menu.csv"
_FOOD_TAGS_CSV = _ROOT / "data" / "food_tags.csv"
_TRANSLATOR_CSV = _ROOT / "data" / "item_translator.csv"
_UNRESOLVED_CSV = _ROOT / "data" / "unresolved_items.csv"

# ---------------------------------------------------------------------------
# Location ID inferred from scraper output filename (stem only, no extension)
# ---------------------------------------------------------------------------
FILENAME_TO_LOCATION_ID = {
    "ucla_bruin_cafe_nutrition_final": "bruin_cafe",
    "ucla_bruin_plate_final_cleaned": "bruin_plate",
    "ucla_cafe_1919_nutrition": "cafe_1919",
    "ucla_de_neve_nutrition_oz": "de_neve",
    "ucla_epicuria_ackerman_nutrition": "epicuria_ackerman",
    "ucla_epicuria_final_cleaned": "epicuria_covel",
    "ucla_feast_nutrition": "feast",
    "ucla_rendezvous_nutrition": "rendezvous",
    "ucla_the_study_nutrition": "the_study",
}

# Rotating locations serve a different menu each day; all others are static.
ROTATING_LOCATIONS = {"de_neve", "bruin_plate", "epicuria_covel"}

# Station substrings that indicate a build-your-own section.
_BYO_KEYWORDS = (
    "build", "byo", "create your own", "create-your-own",
    "salad bar", "toppings bar", "field greens", "greens bar",
)

# ---------------------------------------------------------------------------
# Nutrition column names as written by the scrapers
# ---------------------------------------------------------------------------
_NUTRITION_COLS = [
    "Calories", "Total Fat", "Saturated Fat", "Trans Fat", "Cholesterol",
    "Sodium", "Total Carbohydrate", "Dietary Fiber", "Sugars", "Protein",
    "Calcium", "Iron", "Potassium",
]

# Category inference patterns (applied to item name, case-insensitive)
_CATEGORY_RX = [
    ("protein",  r"chicken|turkey|beef|pork|lamb|salmon|tuna|fish|shrimp|egg|tofu|tempeh|lentil|beans?|hummus"),
    ("starch",   r"rice|quinoa|potato|pasta|noodle|oat|bread|waffle|pancake|croissant|tortilla|pita|roll|bun|bagel|pizza"),
    ("veg",      r"broccoli|spinach|kale|tomato|pepper|cucumber|carrot|onion|lettuce|romaine|arugula|salad|cauliflower|zucchini|squash|corn|peas|edamame"),
    ("dairy",    r"yogurt|cheese|milk|cottage|cream|butter"),
    ("dessert",  r"cookie|cake|pie|tart|gelato|ice cream|brownie|pastry|muffin|donut|macaron|crepe"),
    ("beverage", r"coffee|tea|juice|lemonade|soda|water|boba|kombucha|smoothie|drink"),
    ("sauce",    r"salsa|sauce|dressing|aioli|mayo|ketchup|mustard|pesto|teriyaki|tzatziki|chimichurri|vinaigrette"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_num(val) -> float:
    """Strip unit suffixes (g, mg, %, etc.) and return float. Returns 0.0 for blank/N/A."""
    if val is None:
        return 0.0
    s = str(val).strip()
    if s in ("", "N/A", "nan", "None", "none"):
        return 0.0
    cleaned = re.sub(r"[^\d.]", "", s)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def infer_section_type(station: str, location_id: str) -> str:
    s = station.lower()
    if any(k in s for k in _BYO_KEYWORDS):
        return "build_your_own"
    return "rotating" if location_id in ROTATING_LOCATIONS else "static"


def infer_category(name: str, protein_g: float, carb_g: float, fat_g: float) -> str:
    n = name.lower()
    for cat, rx in _CATEGORY_RX:
        if re.search(rx, n, re.I):
            return cat
    # Nutrition fallback
    if protein_g >= 15:
        return "protein"
    if carb_g >= 40 and protein_g < 10:
        return "starch"
    if fat_g >= 10 and protein_g < 5:
        return "sauce"
    return "unknown"


def scrape_bool_to_str(val) -> str:
    """Convert a scraped is_X column value to 'true'/'false'/'unknown'.

    Scrapers write Python True/False when the detail page was reachable, and
    None (→ empty string in CSV) when the page was unreachable.
    """
    if val is None:
        return "unknown"
    s = str(val).strip()
    if s.lower() in ("true", "1", "yes"):
        return "true"
    if s.lower() in ("false", "0", "no"):
        return "false"
    return "unknown"  # blank → unreachable detail page


def scrape_allergens_to_str(allergens_val, is_vegetarian_val) -> str:
    """Convert scraped allergens column to a string with 'unknown' fallback.

    If the dietary flags are blank (detail page was unreachable), returns
    'unknown'.  If the page was reachable and no allergens were found, returns
    '' (confirmed clean).  Otherwise returns the comma-separated allergen list.
    """
    veg_raw = str(is_vegetarian_val).strip() if is_vegetarian_val is not None else ""
    if not veg_raw or veg_raw.lower() == "none":
        return "unknown"  # detail page was unreachable
    if allergens_val is None:
        return ""
    return str(allergens_val).strip()


def is_low_confidence(section_type: str, calories: float, protein: float,
                      carbs: float, fat: float) -> bool:
    if section_type == "build_your_own":
        return True
    return calories == 0.0 and protein == 0.0 and carbs == 0.0 and fat == 0.0


def translation_confidence(section_type: str, calories: float) -> str:
    if section_type == "build_your_own":
        return "low"
    if calories == 0.0:
        return "low"
    return "high"


def load_existing_csv(path: Path, key_col: str) -> dict:
    """Load a CSV into a dict keyed by lowercased key_col. Returns {} if file missing."""
    result = {}
    if not path.exists():
        return result
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            k = row.get(key_col, "").strip().lower()
            if k:
                result[k] = row
    return result


def read_raw_csv(path: Path) -> list[dict]:
    """Read a scraper CSV. Returns [] if file is empty (headers-only or missing)."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(date_str: str) -> None:
    print(f"\n{'='*60}")
    print(f"  BCAL ingest pipeline — {date_str}")
    print(f"{'='*60}\n")

    # Load existing lookup tables so we can append without overwriting hand-curated data
    existing_food_tags = load_existing_csv(_FOOD_TAGS_CSV, "canonical_name")
    existing_translator = load_existing_csv(_TRANSLATOR_CSV, "raw_item_name")

    daily_menu_rows: list[dict] = []
    new_food_tags: dict = {}       # canonical_name (lower) → row dict
    new_translator: dict = {}      # raw_item_name (lower) → row dict
    unresolved_rows: list[dict] = []

    files_processed = 0
    files_skipped = 0
    total_items = 0
    new_tags_count = 0
    new_trans_count = 0
    unresolved_count = 0

    # Process each known scraper output file
    for stem, location_id in FILENAME_TO_LOCATION_ID.items():
        csv_path = _RAW_DIR / f"{stem}.csv"
        rows = read_raw_csv(csv_path)

        if not rows:
            print(f"  [SKIP] {csv_path.name} — empty or missing (location may be closed today)")
            files_skipped += 1
            continue

        files_processed += 1
        loc_items = 0

        for row in rows:
            food_name = (row.get("Food Name") or "").strip()
            if not food_name:
                continue

            meal = (row.get("Meal") or "Unknown").strip()
            station = (row.get("Station") or "Unknown").strip()

            # Parse nutrition — strip unit suffixes
            calories = parse_num(row.get("Calories"))
            protein  = parse_num(row.get("Protein"))
            fat      = parse_num(row.get("Total Fat"))
            carbs    = parse_num(row.get("Total Carbohydrate"))

            section_type = infer_section_type(station, location_id)
            low_conf = is_low_confidence(section_type, calories, protein, carbs, fat)

            # ── daily_menu.csv row ─────────────────────────────────────────
            daily_menu_rows.append({
                "date":         date_str,
                "location_id":  location_id,
                "meal":         meal,
                "station":      station,
                "item_name":    food_name,
                "section_type": section_type,
            })
            loc_items += 1
            total_items += 1

            # ── item_translator.csv ────────────────────────────────────────
            raw_key = food_name.lower()
            if raw_key not in existing_translator and raw_key not in new_translator:
                category = infer_category(food_name, protein, carbs, fat)
                conf = translation_confidence(section_type, calories)
                new_translator[raw_key] = {
                    "raw_item_name":          food_name,
                    "canonical_name":         food_name,   # identity mapping — refine manually
                    "category":               category,
                    "translation_confidence": conf,
                }
                new_trans_count += 1

            # ── food_tags.csv ──────────────────────────────────────────────
            canonical_key = food_name.lower()
            if canonical_key not in existing_food_tags and canonical_key not in new_food_tags:
                category = infer_category(food_name, protein, carbs, fat)
                data_quality = "missing" if (calories == 0.0 and protein == 0.0) else "complete"
                is_veg_raw = row.get("is_vegetarian")
                new_food_tags[canonical_key] = {
                    "canonical_name": food_name,
                    "category":       category,
                    "tags":           "",
                    "calories":       calories,
                    "protein_grams":  protein,
                    "fat_grams":      fat,
                    "carb_grams":     carbs,
                    "vegetarian":     scrape_bool_to_str(is_veg_raw),
                    "vegan":          scrape_bool_to_str(row.get("is_vegan")),
                    "halal":          scrape_bool_to_str(row.get("is_halal")),
                    "allergens":      scrape_allergens_to_str(row.get("allergens"), is_veg_raw),
                    "data_quality":   data_quality,
                }
                new_tags_count += 1

            # ── unresolved_items.csv ───────────────────────────────────────
            if low_conf:
                reason = []
                if section_type == "build_your_own":
                    reason.append("build_your_own station")
                if calories == 0.0 and protein == 0.0 and carbs == 0.0 and fat == 0.0:
                    reason.append("zero nutrition")
                unresolved_rows.append({
                    "location_id":  location_id,
                    "meal":         meal,
                    "station":      station,
                    "item_name":    food_name,
                    "section_type": section_type,
                    "reason":       "; ".join(reason) or "low_confidence",
                    "date":         date_str,
                })
                unresolved_count += 1

        print(f"  [OK]   {csv_path.name} → {loc_items} items  (location_id={location_id})")

    # ── Write data/daily_menu.csv (fresh each run) ─────────────────────────
    _write_csv(
        _DAILY_MENU_CSV,
        ["date", "location_id", "meal", "station", "item_name", "section_type"],
        daily_menu_rows,
    )

    # ── Write data/food_tags.csv (existing + new stubs) ────────────────────
    merged_tags = list(existing_food_tags.values()) + list(new_food_tags.values())
    _write_csv(
        _FOOD_TAGS_CSV,
        ["canonical_name", "category", "tags", "calories", "protein_grams",
         "fat_grams", "carb_grams", "vegetarian", "vegan", "halal", "allergens", "data_quality"],
        merged_tags,
    )

    # ── Write data/item_translator.csv (existing + new stubs) ──────────────
    merged_trans = list(existing_translator.values()) + list(new_translator.values())
    _write_csv(
        _TRANSLATOR_CSV,
        ["raw_item_name", "canonical_name", "category", "translation_confidence"],
        merged_trans,
    )

    # ── Write data/unresolved_items.csv ────────────────────────────────────
    _write_csv(
        _UNRESOLVED_CSV,
        ["location_id", "meal", "station", "item_name", "section_type", "reason", "date"],
        unresolved_rows,
    )

    # ── Summary ────────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    print(f"  Files processed : {files_processed}  skipped: {files_skipped}")
    print(f"  Menu items      : {total_items}  → data/daily_menu.csv")
    print(f"  New food stubs  : {new_tags_count}  → data/food_tags.csv  (needs manual tagging)")
    print(f"  New translations: {new_trans_count}  → data/item_translator.csv")
    print(f"  Unresolved      : {unresolved_count}  → data/unresolved_items.csv")
    print(f"{'─'*60}\n")
    if unresolved_count > 0:
        print(f"  ⚠  Review data/unresolved_items.csv — BYO and zero-nutrition items")
        print(f"     need dietary flags and allergen info before they can be recommended.\n")


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BCAL ingest pipeline")
    parser.add_argument(
        "--date",
        default=datetime.date.today().isoformat(),
        help="Date to tag menu rows with (YYYY-MM-DD). Defaults to today.",
    )
    args = parser.parse_args()
    run(args.date)
