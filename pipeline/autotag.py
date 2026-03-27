"""
pipeline/autotag.py — infer tags for untagged rows in data/food_tags.csv

Uses item name + nutrition values to assign tags from the vocabulary defined
in recommender/tagger.py and scored by recommender/scorer.py:
  protein, grilled, fried, sugary, creamy, high_calorie,
  high_volume_low_cal, veggies, carb, starch, veg_protein

Rows that already have tags are never modified.

Usage:
    python pipeline/autotag.py
"""

import csv
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
FOOD_TAGS_CSV = DATA_DIR / "food_tags.csv"

FIELDNAMES = [
    "canonical_name", "category", "tags",
    "calories", "protein_grams", "fat_grams", "carb_grams",
    "vegetarian", "vegan", "halal", "allergens", "data_quality",
]


def infer_tags(name: str, category: str, calories: float,
               protein: float, fat: float, carbs: float) -> list:
    """
    Return a sorted list of tags inferred from name, category, and nutrition.
    Uses the same tag vocabulary as recommender/scorer.py.
    """
    tags = set()
    n = name.lower()
    cat = (category or "").lower()

    # Classify item type to guard against false positives on sauces/beverages.
    is_beverage = cat == "beverage" or bool(re.search(
        r"\b(smoothie|coffee|latte|espresso|americano|cappuccino|mocha|chai|"
        r"tea\b|boba|horchata|spritzer|juice\b)\b", n))
    is_sauce = cat == "sauce" or bool(re.search(
        r"\b(dressing|vinaigrette|salsa|aioli|mayo|ketchup|mustard|sauce\b|"
        r"\bdip\b|spread\b|jam\b|marmalade|syrup\b)\b", n))
    is_dessert = cat == "dessert"

    # Whether we have real nutrition data (vs. all-zero missing rows).
    has_nutrition = calories > 0 or protein > 0 or fat > 0 or carbs > 0

    # ── GRILLED ────────────────────────────────────────────────────────────────
    if re.search(r"\bgrilled?\b|\bgrill\b|charred|flame[\s-]?broiled|"
                 r"flame[\s-]?grilled", n):
        tags.add("grilled")

    # ── FRIED ──────────────────────────────────────────────────────────────────
    if re.search(r"\bfried\b|\bfries\b|crispy\b|battered\b|\bkatsu\b|"
                 r"\btempura\b|\bfritter\b|\btots?\b|\bfrites?\b", n):
        tags.add("fried")

    # ── VEG_PROTEIN ────────────────────────────────────────────────────────────
    if re.search(r"\btofu\b|\btempeh\b|\bseitan\b|\blentils?\b|\bchickpea\b|"
                 r"\bgarbanzo\b|\bedamame\b|\bbeyond\b|veggie\s+burger|"
                 r"vegan\s+chicken|\bfalafel\b", n):
        tags.add("veg_protein")

    # ── VEGGIES ────────────────────────────────────────────────────────────────
    if cat == "veg":
        tags.add("veggies")
    elif not is_beverage and not is_sauce and not is_dessert:
        if re.search(
            r"\b(broccoli|spinach|kale|carrot|cucumber|tomato|lettuce|"
            r"greens?|cabbage|zucchini|cauliflower|asparagus|mushroom|"
            r"eggplant|bok\s+choy|brussels|beet|seaweed|arugula|rapini|"
            r"chard|artichoke|edamame|salad\b)\b", n
        ):
            tags.add("veggies")

    # ── CREAMY ─────────────────────────────────────────────────────────────────
    if re.search(r"\bcream(y)?\b|alfredo|hollandaise|\branch\b|caesar\b|"
                 r"cheese\s+sauce", n):
        tags.add("creamy")

    # ── SUGARY ─────────────────────────────────────────────────────────────────
    if is_dessert:
        tags.add("sugary")
    elif not is_sauce:
        if re.search(
            r"\b(cake|cookies?|muffin|donut|brownie|sorbet|pudding|mousse|"
            r"tart\b|cupcake|danish|pastry|blondie|churro|parfait|granola|"
            r"\bwaffle\b|\bpancake\b|boba|caramel|butterscotch|"
            r"chocolate\s+chip)\b", n
        ):
            tags.add("sugary")
        elif is_beverage and has_nutrition and calories > 0 and carbs > 0:
            # Beverages that are mostly sugar calories.
            if (carbs * 4) / calories > 0.65 and protein < 5:
                tags.add("sugary")

    # ── STARCH ─────────────────────────────────────────────────────────────────
    if cat == "starch":
        tags.add("starch")
    elif not is_beverage and not is_sauce:
        if re.search(
            r"\brice\b|\bpasta\b|\bbread\b|\bpotato\b|\bpotatoes\b|"
            r"\bnoodle\b|\boats?\b|oatmeal|\bbagel\b|\bwaffle\b|\bpancake\b|"
            r"\bpizza\b|\btortilla\b|\bpita\b|\bcroissant\b|focaccia|"
            r"\bcouscous\b|\bpilaf\b|\bquinoa\b|polenta|\bgnocchi\b|"
            r"\bmuffin\b|\bbun\b|\broll\b|\bfries\b|\btater\b", n
        ):
            tags.add("starch")

    # ── PROTEIN ────────────────────────────────────────────────────────────────
    if cat == "protein":
        tags.add("protein")
    elif not is_beverage and not is_sauce:
        if has_nutrition:
            # Items with meaningful protein content.
            if protein >= 15:
                tags.add("protein")
            elif protein >= 10 and cat not in ("veg", "starch", "dessert"):
                tags.add("protein")
        else:
            # Zero-nutrition rows: use name keywords.
            if re.search(
                r"\b(chicken|turkey|salmon|tuna|beef|pork|shrimp|fish|steak|"
                r"ham|bacon|egg|lamb|crab|mahi|sausage)\b", n
            ) and cat not in ("veg", "starch", "dessert"):
                tags.add("protein")

    # ── CARB ───────────────────────────────────────────────────────────────────
    if not is_beverage and not is_sauce:
        if has_nutrition and carbs >= 30:
            tags.add("carb")
        elif not has_nutrition:
            # Name-based inference for zero-nutrition rows.
            if re.search(
                r"\b(sandwich|wrap\b|burger|burrito|pizza|pasta\b|taco|"
                r"quesadilla|sub\b|hoagie|panini|bowl\b)\b", n
            ):
                tags.add("carb")

    # ── HIGH_VOLUME_LOW_CAL ────────────────────────────────────────────────────
    if "veggies" in tags and has_nutrition and 0 < calories <= 80:
        tags.add("high_volume_low_cal")

    # ── HIGH_CALORIE ───────────────────────────────────────────────────────────
    if not is_sauce and has_nutrition:
        if calories >= 500:
            tags.add("high_calorie")
        elif "sugary" in tags and calories >= 250:
            tags.add("high_calorie")
        elif "fried" in tags and calories >= 350:
            tags.add("high_calorie")

    return sorted(tags)


def _parse_float(val: str) -> float:
    try:
        return float(val) if val and val.strip() else 0.0
    except ValueError:
        return 0.0


def run():
    # Read all rows.
    rows = []
    with open(FOOD_TAGS_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    already_tagged = 0
    newly_tagged = 0
    still_empty = 0

    for row in rows:
        existing = row.get("tags", "").strip()
        if existing:
            already_tagged += 1
            continue  # Preserve existing tags — never overwrite.

        inferred = infer_tags(
            name=row.get("canonical_name", ""),
            category=row.get("category", ""),
            calories=_parse_float(row.get("calories", "")),
            protein=_parse_float(row.get("protein_grams", "")),
            fat=_parse_float(row.get("fat_grams", "")),
            carbs=_parse_float(row.get("carb_grams", "")),
        )

        if inferred:
            row["tags"] = ",".join(inferred)
            newly_tagged += 1
        else:
            still_empty += 1

    # Write back — preserve original quoting style (QUOTE_MINIMAL).
    with open(FOOD_TAGS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Total rows     : {len(rows)}")
    print(f"Already tagged : {already_tagged}  (unchanged)")
    print(f"Newly tagged   : {newly_tagged}")
    print(f"Still untagged : {still_empty}  (zero-nutrition + ambiguous name)")


if __name__ == "__main__":
    run()
