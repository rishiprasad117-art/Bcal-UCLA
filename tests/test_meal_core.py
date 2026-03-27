import pytest
from meal_core.targets import compute_targets
from meal_core.tagger import tag_foods
from meal_core.composer import compose_meals
from meal_core.planner import plan_day

MENU = [
  {"name":"Capers","station":"SaladBar","calories":5,"protein":0,"carbs":1,"fat":0},
  {"name":"Spinach","station":"SaladBar","calories":10,"protein":1,"carbs":2,"fat":0},
  {"name":"Romaine Greens","station":"SaladBar","calories":15,"protein":1,"carbs":3,"fat":0},
  {"name":"Quinoa","station":"SaladBar","calories":180,"protein":6,"carbs":32,"fat":3},
  {"name":"Chicken Breast (4 oz)","station":"SaladBar","calories":180,"protein":34,"carbs":0,"fat":4},
  {"name":"Balsamic Vinaigrette","station":"SaladBar","calories":90,"protein":0,"carbs":5,"fat":9},
  {"name":"Sourdough Bread","station":"Deli","calories":200,"protein":7,"carbs":40,"fat":2},
  {"name":"Turkey (4 oz)","station":"Deli","calories":180,"protein":30,"carbs":0,"fat":4},
  {"name":"Tomato Slices","station":"Deli","calories":15,"protein":1,"carbs":3,"fat":0},
]


def test_targets_cut():
  t = compute_targets("male", 18, 173, 68, "moderate", "cut")
  assert 1800 < t["target_cal"] < 2600
  assert t["protein_g"] >= 140


def test_no_component_only_recommendations():
  tagged = tag_foods(MENU)
  salads = compose_meals(tagged, "SaladBar", 5)
  assert all(len(m["components"]) >= 2 for m in salads)
  names = " ".join(m["name"].lower() for m in salads)
  assert "capers" not in names


def test_planner_returns_three_meals():
  user = {"sex":"male","age":18,"height_cm":173,"weight_kg":68,"activity":"moderate","goal":"cut"}
  plan = plan_day(MENU, user)
  assert set(plan["meals"].keys()) == {"breakfast","lunch","dinner"}


