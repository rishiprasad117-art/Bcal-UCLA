"""
tests/test_edge_cases.py — edge case tests for the BCAL recommendation engine.

All tests use inline mock data and do not read from any CSV or JSON data files,
with the exception of goal_weights.json which scorer.py loads at import time
(it is configuration, not test data).

Test cases:
    1. Empty menu for a given location/meal
    2. All items filtered out by dietary restrictions
    3. An item with no translation or tag entry (unknown item)
    4. A user who both likes and dislikes the same item (dislike wins)
    5. An item with null/zero nutrition fields being scored
    6. Invalid location/meal period passed to the API
"""

import sys
import os
import pytest
from unittest.mock import patch

# Make sure imports resolve from the project root regardless of where pytest is invoked
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from recommender.engine import recommend
from recommender.scorer import score_item, rank_items


# ── Shared mock helpers ────────────────────────────────────────────────────────

def _raw_menu_item(item_name, station="Test Station", section_type="rotating"):
    """Build a minimal raw menu item dict (as returned by get_menu)."""
    return {
        "item_name": item_name,
        "location_id": "test_loc",
        "meal": "Lunch",
        "station": station,
        "section_type": section_type,
        "date": "2099-01-01",
    }


def _full_nutrition(
    canonical_name,
    tags=None,
    calories=300.0,
    protein_grams=20.0,
    vegetarian=True,
    vegan=False,
    halal=True,
    allergens=None,
    data_quality="complete",
):
    """Build a complete nutrition/tag dict (as returned by get_tags_and_nutrition)."""
    return {
        "canonical_name": canonical_name,
        "category": "protein",
        "tags": tags or ["protein"],
        "calories": calories,
        "protein_grams": protein_grams,
        "fat_grams": 10.0,
        "carb_grams": 20.0,
        "vegetarian": vegetarian,
        "vegan": vegan,
        "halal": halal,
        "allergens": allergens or [],
        "data_quality": data_quality,
    }


_MOCK_LOCATION = {"location_id": "test_loc", "name": "Test Hall", "type": "dining_hall"}


# ── Test 1: Empty menu ─────────────────────────────────────────────────────────

def test_empty_menu_returns_no_recommendations():
    """When get_menu returns no items, the result should have empty recommendations
    and empty filtered_out — not a crash or error."""
    with patch("recommender.engine.get_menu", return_value=[]), \
         patch("recommender.engine.get_location", return_value=_MOCK_LOCATION):

        result = recommend(
            location_id="test_loc",
            meal="Lunch",
            goal="balanced",
            user_profile={"diet": "none", "allergies": [], "likes": [], "dislikes": []},
            date="2099-01-01",
        )

    assert result["recommendations"] == []
    assert result["filtered_out"] == []
    assert result["location"] == "Test Hall"
    assert result["meal"] == "Lunch"


# ── Test 2: All items filtered out ────────────────────────────────────────────

def test_all_items_filtered_out_by_diet():
    """When every item fails the diet filter, recommendations should be empty
    and all items should appear in filtered_out with a clear reason."""
    mock_menu = [
        _raw_menu_item("Cheeseburger"),
        _raw_menu_item("Turkey Club"),
    ]

    def mock_normalize(name):
        return name, "protein", "high"

    def mock_tags(canonical):
        # Both items are not vegan
        return _full_nutrition(canonical, tags=["protein"], vegan=False, vegetarian=False)

    with patch("recommender.engine.get_menu", return_value=mock_menu), \
         patch("recommender.engine.get_location", return_value=_MOCK_LOCATION), \
         patch("recommender.engine.normalize_item_name", side_effect=mock_normalize), \
         patch("recommender.engine.get_tags_and_nutrition", side_effect=mock_tags):

        result = recommend(
            location_id="test_loc",
            meal="Lunch",
            goal="balanced",
            user_profile={"diet": "vegan", "allergies": [], "likes": [], "dislikes": []},
            date="2099-01-01",
        )

    assert result["recommendations"] == []
    assert len(result["filtered_out"]) == 2

    filtered_names = {item["item"] for item in result["filtered_out"]}
    assert filtered_names == {"Cheeseburger", "Turkey Club"}

    for item in result["filtered_out"]:
        assert "not vegan" in item["reason"]


# ── Test 3: Unknown item — no translation, no tag entry ───────────────────────

def test_unknown_item_survives_pipeline_with_warning():
    """An item with no translator entry and no tag entry should:
    - not be filtered out (no dietary flags to trigger filters)
    - appear in recommendations with data_quality="missing"
    - have a data_note surfacing the unknown status
    - score 0 (no tags, all nutrition zero)
    """
    mock_menu = [_raw_menu_item("Mystery Special 2099")]

    def mock_normalize(name):
        # Identity fallback — normalizer could not find a mapping
        return name, "unknown", "low"

    def mock_tags(canonical):
        # Safe stub — as returned by tagger.py when canonical is not in food_tags.csv
        return {
            "canonical_name": canonical,
            "category": "unknown",
            "tags": [],
            "calories": 0.0,
            "protein_grams": 0.0,
            "fat_grams": 0.0,
            "carb_grams": 0.0,
            "vegetarian": False,  # safe default: don't assume compliant
            "vegan": False,
            "halal": False,
            "allergens": [],
            "data_quality": "missing",
            "_unknown": True,
        }

    with patch("recommender.engine.get_menu", return_value=mock_menu), \
         patch("recommender.engine.get_location", return_value=_MOCK_LOCATION), \
         patch("recommender.engine.normalize_item_name", side_effect=mock_normalize), \
         patch("recommender.engine.get_tags_and_nutrition", side_effect=mock_tags):

        result = recommend(
            location_id="test_loc",
            meal="Lunch",
            goal="cut",
            user_profile={"diet": "none", "allergies": [], "likes": [], "dislikes": []},
            date="2099-01-01",
        )

    # Item must pass through (no diet/allergy filters triggered)
    assert len(result["recommendations"]) == 1
    rec = result["recommendations"][0]

    assert rec["item"] == "Mystery Special 2099"
    assert rec["score"] == 0.0          # no tags + zero nutrition = no score
    assert rec["data_quality"] == "missing"
    assert "data_note" in rec
    assert "not yet in our database" in rec["data_note"]
    assert result["filtered_out"] == []


# ── Test 4: User likes and dislikes the same item ─────────────────────────────

def test_dislike_wins_over_like_for_same_item():
    """If a user lists a term in both likes and dislikes, the dislike takes
    precedence (filter_by_preferences checks dislikes first and short-circuits).
    The item must appear in filtered_out, not in recommendations."""
    mock_menu = [_raw_menu_item("Grilled Chicken Breast")]

    def mock_normalize(name):
        return "Grilled Chicken Breast", "protein", "high"

    def mock_tags(canonical):
        return _full_nutrition(
            canonical,
            tags=["protein", "grilled"],
            calories=180.0,
            protein_grams=28.0,
            vegetarian=False,
            vegan=False,
            halal=True,
        )

    with patch("recommender.engine.get_menu", return_value=mock_menu), \
         patch("recommender.engine.get_location", return_value=_MOCK_LOCATION), \
         patch("recommender.engine.normalize_item_name", side_effect=mock_normalize), \
         patch("recommender.engine.get_tags_and_nutrition", side_effect=mock_tags):

        result = recommend(
            location_id="test_loc",
            meal="Lunch",
            goal="cut",
            user_profile={
                "diet": "none",
                "allergies": [],
                "likes": ["chicken"],    # likes it…
                "dislikes": ["chicken"], # …but also dislikes it
            },
            date="2099-01-01",
        )

    # Dislike must win — nothing recommended
    assert result["recommendations"] == []
    assert len(result["filtered_out"]) == 1

    reason = result["filtered_out"][0]["reason"]
    assert "dislike" in reason
    assert "chicken" in reason

    # Confirm the like bonus was NOT applied (item never reached scorer)
    assert "liked food" not in str(result)


# ── Test 5: Null/zero nutrition fields being scored ───────────────────────────

def test_scoring_with_zero_nutrition_does_not_crash():
    """score_item and rank_items must handle an item where all numeric nutrition
    fields are 0.0 (the 'missing data' stub pattern from tagger.py) without
    crashing or producing NaN/Inf scores."""
    zero_nutrition_item = {
        "item_name": "Unknown Food",
        "canonical_name": "Unknown Food",
        "category": "unknown",
        "tags": [],            # no tags → no tag-based contribution
        "calories": 0.0,
        "protein_grams": 0.0,
        "fat_grams": 0.0,
        "carb_grams": 0.0,
        "vegetarian": False,
        "vegan": False,
        "halal": False,
        "allergens": [],
        "data_quality": "missing",
        "_unknown": True,
    }

    # score_item must return a finite float and an empty reasons list
    score, reasons = score_item(zero_nutrition_item, goal="cut")

    assert isinstance(score, float)
    assert score == 0.0
    assert reasons == []

    # rank_items must handle a single-item list without crashing
    ranked = rank_items([zero_nutrition_item], goal="high_protein")

    assert len(ranked) == 1
    assert ranked[0]["score"] == 0.0
    assert ranked[0]["reasons"] == []


def test_scoring_with_zero_nutrition_all_goals():
    """Zero-nutrition items should score 0.0 across every goal — none of the
    nutrition_weights produce a non-zero contribution when multiplied by 0."""
    item = {
        "tags": [],
        "calories": 0.0,
        "protein_grams": 0.0,
    }
    for goal in ("cut", "bulk", "maintain", "high_protein", "balanced"):
        score, _ = score_item(item, goal=goal)
        assert score == 0.0, f"Expected 0.0 for goal={goal}, got {score}"


# ── Test 6: Invalid location/meal to API ──────────────────────────────────────

def test_api_returns_400_for_missing_required_fields():
    """The /recommend endpoint must return 400 when required fields
    (location_id, meal) are absent or empty — before any recommender logic runs."""
    from api import app

    client = app.test_client()

    # Missing location_id entirely
    resp = client.post("/recommend", json={"meal": "Lunch", "goal": "cut"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()

    # Missing meal entirely
    resp = client.post("/recommend", json={"location_id": "de_neve", "goal": "cut"})
    assert resp.status_code == 400
    assert "error" in resp.get_json()

    # Both missing
    resp = client.post("/recommend", json={"goal": "balanced"})
    assert resp.status_code == 400

    # Empty strings for required fields
    resp = client.post("/recommend", json={"location_id": "", "meal": "", "goal": "cut"})
    assert resp.status_code == 400

    # Non-JSON body
    resp = client.post("/recommend", data="not json at all", content_type="text/plain")
    assert resp.status_code == 400


def test_api_returns_200_with_empty_recommendations_for_unknown_location():
    """An unrecognized location_id with valid required fields should return 200
    with empty recommendations — not a 500 or crash. The engine must handle
    an unknown location gracefully (get_menu returns [] for an unknown location)."""
    from api import app

    client = app.test_client()

    # Patch get_menu so we don't depend on CSV data and so we control the scenario:
    # a real location_id structure but a date with no menu rows = empty menu
    with patch("recommender.engine.get_menu", return_value=[]), \
         patch("recommender.engine.get_location", return_value=None):

        resp = client.post("/recommend", json={
            "location_id": "nonexistent_hall_xyz",
            "meal": "Brunch",           # not a valid UCLA meal period
            "goal": "balanced",
            "diet": "none",
            "allergies": [],
            "likes": [],
            "dislikes": [],
            "date": "2099-01-01",
        })

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["recommendations"] == []
    assert body["filtered_out"] == []
    # location falls back to location_id string when location_info is None
    assert body["location_id"] == "nonexistent_hall_xyz"
