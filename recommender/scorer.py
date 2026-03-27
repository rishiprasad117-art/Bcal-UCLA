"""
scorer.py — rule-based scoring and ranking of menu items.

All weights are loaded from data/goal_weights.json.
NO weights are hardcoded in this file — edit the JSON to tune scoring behavior.

Scoring formula for each item:
  score = sum(tag_weights[tag] for tag in item.tags if tag in tag_weights)
        + sum(nutrition_weights[field] * item[field] for field in nutrition_weights)
        + like_bonus (if item was liked by the user)

The like_bonus is defined at the top level of goal_weights.json so it can be
tuned without touching code.
"""

import json
import os

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_WEIGHTS_JSON = os.path.join(_DATA_DIR, "goal_weights.json")

# Load once at module import time — weights don't change during a request
with open(_WEIGHTS_JSON, encoding="utf-8") as f:
    _WEIGHTS = json.load(f)

# Top-level like bonus (shared across all goals)
_LIKE_BONUS = _WEIGHTS.get("like_bonus", 2)

# Minimum contribution magnitude to include in reasons (avoids noisy micro-contributions)
_REASON_THRESHOLD = 0.5


def score_item(item: dict, goal: str) -> tuple[float, list[str]]:
    """
    Compute a score and list of human-readable reasons for a single item.

    Args:
        item: enriched item dict (has tags, calories, protein_grams, etc.)
        goal: one of "cut", "bulk", "maintain", "high_protein", "balanced"
              Falls back to "balanced" if goal is unknown.

    Returns:
        (score: float, reasons: list[str])
        Score can be negative. Reasons list is empty for items with no matching weights.
    """
    # Fall back to "balanced" for unknown goal values
    if goal not in _WEIGHTS:
        goal = "balanced"

    goal_config = _WEIGHTS[goal]
    tag_weights = goal_config.get("tag_weights", {})
    nutrition_weights = goal_config.get("nutrition_weights", {})

    score = 0.0
    reasons = []

    # --- Tag-based scoring ---
    for tag in item.get("tags", []):
        if tag in tag_weights:
            w = tag_weights[tag]
            if w == 0:
                continue  # Neutral weight — don't penalize or reward, don't mention
            score += w
            if w > 0:
                reasons.append(f"{tag}: good for {goal} (+{w}pts)")
            else:
                reasons.append(f"{tag}: avoid for {goal} ({w}pts)")

    # --- Nutrition-based scoring ---
    for field, weight in nutrition_weights.items():
        value = item.get(field, 0.0)
        contribution = weight * value
        score += contribution

        # Only mention if the contribution is meaningful
        if abs(contribution) >= _REASON_THRESHOLD:
            if field == "protein_grams":
                if contribution > 0:
                    reasons.append(f"high protein: {value:.0f}g (+{contribution:.1f}pts)")
                else:
                    reasons.append(f"low protein: {value:.0f}g ({contribution:.1f}pts)")
            elif field == "calories":
                if contribution < 0:
                    reasons.append(f"calorie-dense: {value:.0f}cal ({contribution:.1f}pts)")
                else:
                    reasons.append(f"calorie boost: {value:.0f}cal (+{contribution:.1f}pts)")

    # --- Like bonus ---
    if item.get("_liked"):
        score += _LIKE_BONUS
        reasons.append(f"liked food: +{_LIKE_BONUS}pts")

    return round(score, 2), reasons


def rank_items(items: list[dict], goal: str) -> list[dict]:
    """
    Score all items and return them sorted by score descending (best first).

    Attaches "score" and "reasons" keys to each item dict.
    Does not modify the original dicts — works on copies.
    """
    scored = []
    for item in items:
        item_copy = dict(item)
        item_copy["score"], item_copy["reasons"] = score_item(item, goal)
        scored.append(item_copy)

    # Sort descending by score; use item_name as tiebreaker for determinism
    scored.sort(key=lambda x: (-x["score"], x.get("item_name", "")))
    return scored
