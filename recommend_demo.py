"""
recommend_demo.py — end-to-end demo of the BCAL recommendation engine.

Runs two example scenarios to demonstrate:
  1. A student cutting weight, vegetarian, gluten allergy, at De Neve Lunch
  2. A student bulking, no restrictions, likes grilled food, at De Neve Dinner

Run with:
    cd /Users/rishiprasad/BCAL/Code
    python recommend_demo.py
"""

import json
from recommender import recommend

# ── Demo date (matches the mock data in data/daily_menu.csv) ──────────────────
DEMO_DATE = "2026-03-25"


def print_result(result: dict) -> None:
    """Pretty-print a recommendation result."""
    print(f"\n{'='*60}")
    print(f"  {result['location']} — {result['meal']} ({result['date']})")
    print(f"  Goal: {result['goal'].upper()}")
    print(f"{'='*60}")

    if not result["recommendations"]:
        print("  No recommendations — all items were filtered out.")
    else:
        print(f"\n  TOP RECOMMENDATIONS ({len(result['recommendations'])} items):\n")
        for i, item in enumerate(result["recommendations"], 1):
            print(f"  {i}. {item['item']}")
            print(f"     Score: {item['score']}  |  {item['calories']:.0f} cal  |  {item['protein_grams']:.0f}g protein")
            print(f"     Station: {item['station']} ({item['section_type']})")
            if item.get("data_note"):
                print(f"     Note: {item['data_note']}")
            if item["reasons"]:
                print(f"     Why: {' / '.join(item['reasons'])}")
            print()

    if result["filtered_out"]:
        print(f"  FILTERED OUT ({len(result['filtered_out'])} items):")
        for item in result["filtered_out"]:
            print(f"    - {item['item']}: {item['reason']}")

    print()


# ── Scenario 1: Vegetarian student cutting, gluten allergy ───────────────────
print("\n" + "─"*60)
print("SCENARIO 1: Vegetarian student cutting, gluten allergy")
print("─"*60)

result1 = recommend(
    location_id="de_neve",
    meal="Lunch",
    goal="cut",
    user_profile={
        "diet": "vegetarian",
        "allergies": ["gluten"],
        "likes": ["tofu", "broccoli"],
        "dislikes": ["mushrooms"],
    },
    date=DEMO_DATE,
    top_n=5,
)
print_result(result1)


# ── Scenario 2: Bulking student, no restrictions, likes grilled ──────────────
print("─"*60)
print("SCENARIO 2: No restrictions, bulking, likes grilled food")
print("─"*60)

result2 = recommend(
    location_id="de_neve",
    meal="Dinner",
    goal="bulk",
    user_profile={
        "diet": "none",
        "allergies": [],
        "likes": ["grilled", "chicken"],
        "dislikes": [],
    },
    date=DEMO_DATE,
    top_n=5,
)
print_result(result2)


# ── Scenario 3: Vegan student, high protein goal, at Bruin Plate ─────────────
print("─"*60)
print("SCENARIO 3: Vegan student, high protein goal, Bruin Plate Breakfast")
print("─"*60)

result3 = recommend(
    location_id="bruin_plate",
    meal="Breakfast",
    goal="high_protein",
    user_profile={
        "diet": "vegan",
        "allergies": [],
        "likes": [],
        "dislikes": [],
    },
    date=DEMO_DATE,
    top_n=5,
)
print_result(result3)


# ── Raw JSON output for one scenario ─────────────────────────────────────────
print("\n" + "─"*60)
print("RAW JSON OUTPUT (Scenario 1):")
print("─"*60)
print(json.dumps(result1, indent=2))
