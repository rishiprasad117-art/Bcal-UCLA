"""
engine.py — main recommendation pipeline orchestration.

This is the only public entry point. It wires together all modules in order:
  1. Load menu items for the requested location/meal/date
  2. Normalize raw UCLA item names → canonical names
  3. Fetch tags and nutrition for each canonical item
  4. Apply hard filters (diet, allergies, dislikes)
  5. Score and rank remaining items against the user's goal
  6. Format and return the final response

user_profile keys:
    diet:       "none" | "vegetarian" | "vegan" | "halal"
    allergies:  list[str]  — e.g. ["gluten", "shellfish"]
    likes:      list[str]  — e.g. ["tofu", "broccoli"]
    dislikes:   list[str]  — e.g. ["mushrooms"]

All filtering is hard (binary in/out). Scoring is rule-based using goal_weights.json.
"""

import datetime

from .menu_loader import get_menu, get_location
from .normalizer import normalize_item_name
from .tagger import get_tags_and_nutrition
from .filters import filter_by_diet, filter_by_allergies, filter_by_preferences
from .scorer import rank_items
from .response import make_response
from meal_core.targets import compute_targets

# Fraction of daily calories allocated per meal period
_MEAL_FRACTIONS = {"Breakfast": 0.30, "Lunch": 0.35, "Dinner": 0.40}


def recommend(
    location_id: str,
    meal: str,
    goal: str,
    user_profile: dict,
    date: str | None = None,
    top_n: int = 5,
    physical_profile: dict | None = None,
) -> dict:
    """
    Run the full recommendation pipeline and return a structured result.

    Args:
        location_id:  UCLA location key, e.g. "de_neve", "bruin_plate"
        meal:         "Breakfast", "Lunch", or "Dinner"
        goal:         "cut" | "bulk" | "maintain" | "high_protein" | "balanced"
        user_profile: dict with keys: diet, allergies, likes, dislikes
        date:         "YYYY-MM-DD" or None (defaults to today)
        top_n:        number of recommendations to return (default 5)

    Returns:
        Dict with recommendations, filtered_out, and metadata.
        recommendations is empty if all items are filtered out — handle at UI layer.
    """
    # Resolve date
    if date is None:
        date = datetime.date.today().isoformat()

    # --- Step 1: Load raw menu ---
    raw_items = get_menu(location_id, meal, date)
    location_info = get_location(location_id)

    # --- Step 2 & 3: Normalize names and fetch tags/nutrition ---
    enriched = []
    for raw in raw_items:
        canonical, category, confidence = normalize_item_name(raw["item_name"])
        nutrition = get_tags_and_nutrition(canonical)

        # Merge raw menu fields with normalized name and nutrition data
        enriched_item = {
            **raw,                          # item_name, station, section_type, date, etc.
            "canonical_name": canonical,
            "category": category,
            "translation_confidence": confidence,
            **nutrition,                    # tags, calories, protein_grams, dietary flags, etc.
        }
        enriched.append(enriched_item)

    # --- Step 4: Apply hard filters (accumulate rejected items for response) ---
    filtered_out = []

    kept, rejected = filter_by_diet(enriched, user_profile)
    filtered_out.extend(rejected)

    kept, rejected = filter_by_allergies(kept, user_profile)
    filtered_out.extend(rejected)

    kept, rejected = filter_by_preferences(kept, user_profile)
    filtered_out.extend(rejected)

    # --- Step 5: Score and rank remaining items ---
    ranked = rank_items(kept, goal)

    # --- Step 5b: Apply per-meal calorie bonus/penalty if physical profile provided ---
    targets = None
    if physical_profile:
        targets = compute_targets(
            sex=physical_profile["sex"],
            age=physical_profile["age"],
            height_cm=physical_profile["height_cm"],
            weight_kg=physical_profile["weight_kg"],
            activity=physical_profile.get("activity", "moderate"),
            goal=goal,
        )

        meal_fraction = _MEAL_FRACTIONS.get(meal, 0.35)
        meal_cal_target = targets["target_cal"] * meal_fraction

        for item in ranked:
            cal = item.get("calories") or 0
            if not cal:
                continue
            ratio = cal / meal_cal_target
            if 0.7 <= ratio <= 1.3:
                item["score"] = round(item["score"] + 1.5, 2)
                item["reasons"].append(
                    f"fits meal calorie target (~{meal_cal_target:.0f} kcal) +1.5pts"
                )
            elif ratio > 1.8:
                item["score"] = round(item["score"] - 1.0, 2)
                item["reasons"].append(
                    f"too calorie-dense for this meal (~{meal_cal_target:.0f} kcal target) -1.0pts"
                )

        ranked.sort(key=lambda x: (-x["score"], x.get("item_name", "")))

    # --- Step 6: Format and return response ---
    return make_response(
        location_id=location_id,
        location_info=location_info,
        meal=meal,
        date=date,
        ranked_items=ranked,
        filtered_out=filtered_out,
        top_n=top_n,
        goal=goal,
        targets=targets,
    )
