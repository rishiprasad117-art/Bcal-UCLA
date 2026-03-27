import re
from typing import List, Dict

# Buckets
# bread, base (greens/grains), protein, starch, veg, fat_cheese, crunch, dressing, sauce, unknown
NAME_RX = {
    "bread": r"bread|wrap|pita|tortilla|roll|bagel|bun|naan",
    "base": r"romaine|spinach|kale|greens|spring|quinoa|rice",
    "protein": r"chicken|turkey|tofu|tempeh|salmon|tuna|egg|lentil|beans?",
    "starch": r"rice|quinoa|potato|pasta|noodle|oats?",
    "veg": r"tomato|onion|pepper|cucumber|broccoli|carrot|mushroom|lettuce|spinach|kale",
    "fat_cheese": r"feta|swiss|cheddar|mozz|parmes(an|a)|gouda|avocado|olives?|nuts?|tahini|cottage",
    "crunch": r"croutons?|seeds?|tortilla\s*strips|crisps?",
    "dressing": r"dressing|vinaigrette|ranch|caesar|italian|balsamic",
    "sauce": r"salsa|aioli|mayo|ketchup|mustard|bbq|pesto|teriyaki|tzatziki|chimichurri",
}


def _bucket_by_name(name: str) -> str:
    for bucket, rx in NAME_RX.items():
        if re.search(rx, name, re.I):
            return bucket
    return ""


def tag_foods(menu: List[dict]) -> List[dict]:
    """
    Add 'bucket' to each item using regex; if no match, apply nutrition fallbacks.
    Expected keys on input items: name, station, calories, protein, carbs, fat
    """
    tagged: List[Dict] = []
    for it in menu:
        name = it.get("name", "")
        bucket = _bucket_by_name(name)
        calories = int(it.get("calories", 0) or 0)
        protein = float(it.get("protein", it.get("protein_g", 0)) or 0)
        carbs = float(it.get("carbs", it.get("carbs_g", 0)) or 0)
        fat = float(it.get("fat", it.get("fat_g", 0)) or 0)

        if not bucket:
            # nutrition fallbacks
            if protein >= 8:
                bucket = "protein"
            elif fat >= 8 and protein < 2 and calories <= 120:
                bucket = "dressing"
            elif re.search(r"green|leaf|romaine|spinach|kale", name, re.I) and calories <= 30:
                bucket = "base"
            elif calories <= 30:
                bucket = "veg"
            else:
                bucket = "unknown"

        out = dict(it)
        out["calories"] = calories
        out["protein"] = protein
        out["carbs"] = carbs
        out["fat"] = fat
        out["bucket"] = bucket
        tagged.append(out)
    return tagged


