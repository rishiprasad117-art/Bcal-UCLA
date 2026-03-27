"""
bcal_core.py — connect scraper output to meal_core planner
"""
import json
import os
import csv
from meal_core.planner import plan_day


def _infer_station(category: str) -> str:
    c = (category or "").lower()
    if any(k in c for k in ("salad","market","freshly","greens","fruit")): return "SaladBar"
    if any(k in c for k in ("deli","sandwich","wrap")): return "Deli"
    if any(k in c for k in ("grill","kitchen","stone","harvest")): return "Grill"
    if any(k in c for k in ("breakfast","waffle","egg")): return "Breakfast"
    return "Unknown"


def _load_menu(path: str):
    if path.endswith('.json'):
        with open(path) as f:
            return json.load(f)
    # assume CSV
    items = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('Food Item') or row.get('name') or ''
            station = _infer_station(row.get('Category',''))
            calories = float(row.get('Calories (kcal)', row.get('calories', 0)) or 0)
            protein = float(row.get('Protein (g)', row.get('protein', 0)) or 0)
            carbs = float(row.get('Total Carbohydrate (g)', row.get('carbs', 0)) or 0)
            fat = float(row.get('Total Fat (g)', row.get('fat', 0)) or 0)
            items.append({
                'name': name,
                'station': station,
                'calories': calories,
                'protein': protein,
                'carbs': carbs,
                'fat': fat,
            })
    return items


def generate_meal_plan(scraped_file: str, output_file: str, user_profile: dict):
    menu = _load_menu(scraped_file)
    plan = plan_day(menu, user_profile)
    with open(output_file, "w") as f:
        json.dump(plan, f, indent=2)
    print(f"✅ Plan generated → {output_file}")
    return plan


if __name__ == "__main__":
    user = {
        "sex": "male", "age": 18, "height_cm": 173, "weight_kg": 68,
        "activity": "moderate", "goal": "cut",
        "avoid": ["pork", "beef"], "prefer": ["chicken", "rice", "salmon", "yogurt"],
    }
    generate_meal_plan("de_neve_menu_composed.json", "bcal_plan_output.json", user)


