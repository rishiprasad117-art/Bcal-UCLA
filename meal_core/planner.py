from typing import List, Dict
from .targets import compute_targets
from .tagger import tag_foods
from .composer import compose_meals


def _closest(meals: List[dict], cal_target: float) -> dict:
    if not meals:
        return {}
    return sorted(meals, key=lambda m: abs(m.get("calories", 0) - cal_target))[0]


def plan_day(menu: List[dict], user: Dict) -> Dict:
    """
    Orchestrate planning per spec.
    """
    targets = compute_targets(user.get("sex", "male"), user.get("age", 20), user.get("height_cm", 175),
                              user.get("weight_kg", 70), user.get("activity", "moderate"), user.get("goal", "maintain"))
    tagged = tag_foods(menu)

    tcals = targets["target_cal"]
    splits = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.40}

    # Compose options by station
    stations = ["Breakfast", "Grill", "Deli", "SaladBar"]
    options = {s: compose_meals(tagged, s, 5) for s in stations}

    b_opts = options.get("Breakfast") or options.get("Grill") or []
    l_opts = (options.get("Deli") or []) + (options.get("Grill") or []) + (options.get("SaladBar") or [])
    d_opts = (options.get("Grill") or []) + (options.get("Deli") or []) + (options.get("SaladBar") or [])

    breakfast = _closest(b_opts, tcals * splits["breakfast"]) or {}
    lunch = _closest(l_opts, tcals * splits["lunch"]) or {}
    dinner = _closest(d_opts, tcals * splits["dinner"]) or {}

    return {
        "targets": {
            "calories": targets["target_cal"],
            "protein_g": targets["protein_g"],
            "fat_g": targets["fat_g"],
            "carbs_g": targets["carbs_g"],
            "notes": targets["notes"],
        },
        "meals": {
            "breakfast": breakfast,
            "lunch": lunch,
            "dinner": dinner,
        },
        "errors": [],
    }


