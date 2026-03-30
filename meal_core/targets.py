from math import ceil

LBS_PER_KG = 2.20462

AF_MAP = {
    "sedentary": 1.20,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very": 1.725,
    "athlete": 1.90,
}

GOAL_MULT = {
    "maintenance": 1.00,
    "maintain": 1.00,
    "recomp": 1.00,
}

GOAL_DELTA = {
    "cut":  -500,
    "bulk": +300,
}


def _mifflin_st_jeor(sex: str, age: int, height_cm: float, weight_kg: float) -> float:
    s = 5 if sex == "male" else -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + s


def compute_targets(sex: str, age: int, height_cm: float, weight_kg: float,
                    activity: str, goal: str) -> dict:
    """
    Return macro targets dict per spec.
    """
    notes = []
    bmr = _mifflin_st_jeor(sex or "male", int(age), float(height_cm), float(weight_kg))
    af = AF_MAP.get(activity or "moderate", 1.55)
    tdee = bmr * af

    if goal == "recomp":
        notes.append("Recomp baseline (0%); adjust ±7% on training/rest days if needed")

    delta = GOAL_DELTA.get(goal or "maintain", 0)
    mult = GOAL_MULT.get(goal or "maintain", 1.0)
    target_cal = tdee * mult + delta

    weight_lb = weight_kg * LBS_PER_KG
    protein_per_lb = {
        "cut":          0.85,
        "maintain":     0.8,
        "maintenance":  0.8,
        "bulk":         1.0,
        "high_protein": 1.1,
    }.get(goal, 0.8)
    protein_g = int(round(weight_lb * protein_per_lb))

    fat_floor_g = int(ceil(weight_lb * 0.4))
    fat_g = fat_floor_g

    # carbs remainder
    carbs_kcal = target_cal - (protein_g * 4 + fat_g * 9)
    carbs_g = max(0, int(round(carbs_kcal / 4)))

    # round target calories to nearest 5 for display consistency
    target_cal_rounded = int(round(target_cal / 5) * 5)

    notes.append(f"BMR (Mifflin–St Jeor): {int(round(bmr))}")
    notes.append(f"AF {af} → TDEE {int(round(tdee))}")
    if delta != 0:
        notes.append(f"Goal {goal or 'maintain'} {delta:+d} kcal")
    else:
        notes.append(f"Goal {goal or 'maintain'} ×{mult}")

    return {
        "target_cal": target_cal_rounded,
        "protein_g": protein_g,
        "fat_g": fat_g,
        "carbs_g": carbs_g,
        "notes": notes,
    }


