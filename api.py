"""
api.py — Flask API endpoints for the BCAL recommendation backend.

Endpoints:
    GET  /locations
        Returns all UCLA meal-plan-accepted locations.

    GET  /menu?location=<id>&meal=<m>&date=<YYYY-MM-DD>
        Returns raw menu items for a location/meal/date combo.
        date defaults to today.

    POST /recommend
        Body (JSON):
        {
            "location_id": "de_neve",
            "meal": "Lunch",
            "goal": "cut",
            "diet": "none",
            "allergies": ["gluten"],
            "likes": ["broccoli"],
            "dislikes": ["mushrooms"],
            "date": "2026-03-25"   (optional)
        }
        Returns ranked recommendations with reasons.

Run locally:
    pip install flask
    python api.py
    # Server starts at http://localhost:5000
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from recommender import recommend
from recommender.menu_loader import list_locations, get_menu

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])


@app.route("/locations", methods=["GET"])
def locations():
    """Return all UCLA meal-plan-accepted food locations."""
    return jsonify(list_locations())


@app.route("/menu", methods=["GET"])
def menu():
    """
    Return raw menu items for a location, meal, and date.

    Query params:
        location  — location_id (required)
        meal      — Breakfast / Lunch / Dinner (required)
        date      — YYYY-MM-DD (optional, defaults to today)
    """
    location_id = request.args.get("location", "").strip()
    meal = request.args.get("meal", "").strip()
    date = request.args.get("date", None)

    if not location_id or not meal:
        return jsonify({"error": "Both 'location' and 'meal' query parameters are required."}), 400

    items = get_menu(location_id, meal, date)
    return jsonify({
        "location_id": location_id,
        "meal": meal,
        "date": date,
        "count": len(items),
        "items": items,
    })


@app.route("/recommend", methods=["POST"])
def recommend_endpoint():
    """
    Main recommendation endpoint.

    Accepts a JSON body and returns ranked food recommendations with reasons
    and a list of items that were filtered out and why.
    """
    body = request.get_json(silent=True)
    if not body:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    # Required fields
    location_id = body.get("location_id", "").strip()
    meal = body.get("meal", "").strip()
    goal = body.get("goal", "balanced").strip()

    if not location_id or not meal:
        return jsonify({"error": "Both 'location_id' and 'meal' are required."}), 400

    # Optional fields with defaults
    user_profile = {
        "diet": body.get("diet", "none"),
        "allergies": body.get("allergies", []),
        "likes": body.get("likes", []),
        "dislikes": body.get("dislikes", []),
    }
    date = body.get("date", None)
    top_n = int(body.get("top_n", 5))

    # Build physical profile if all required fields are present
    physical_profile = None
    age = body.get("age")
    weight_lbs = body.get("weight_lbs")
    height_ft = body.get("height_ft")
    if age and weight_lbs and height_ft is not None:
        height_in = body.get("height_in", 0) or 0
        height_cm = ((int(height_ft) * 12) + int(height_in)) * 2.54
        weight_kg = float(weight_lbs) / 2.20462
        physical_profile = {
            "sex": body.get("sex", "male"),
            "age": int(age),
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity": body.get("activity", "moderate"),
        }

    result = recommend(
        location_id=location_id,
        meal=meal,
        goal=goal,
        user_profile=user_profile,
        date=date,
        top_n=top_n,
        physical_profile=physical_profile,
    )
    return jsonify(result)


if __name__ == "__main__":
    # Run in debug mode for local development
    app.run(debug=True, port=5000)
