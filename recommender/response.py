"""
response.py — formats the final recommendation output.

This module does no computation — it only shapes the data into the output
schema expected by the API and frontend.

Output schema:
{
    "location": str,
    "location_id": str,
    "meal": str,
    "date": str,
    "goal": str,
    "recommendations": [
        {
            "item": str,           # raw item name as it appeared on the menu
            "canonical_name": str,
            "station": str,
            "section_type": str,   # "rotating", "build_your_own", or "static"
            "score": float,
            "calories": float,
            "protein_grams": float,
            "data_quality": str,   # "complete", "estimated", or "missing"
            "data_note": str,      # present only if data_quality != "complete"
            "reasons": [str]
        }
    ],
    "filtered_out": [
        {
            "item": str,           # raw item name
            "reason": str          # why it was filtered
        }
    ]
}
"""


def make_response(
    location_id: str,
    location_info: dict | None,
    meal: str,
    date: str,
    ranked_items: list[dict],
    filtered_out: list[dict],
    top_n: int = 5,
    goal: str = "balanced",
    targets: dict | None = None,
) -> dict:
    """
    Build the final JSON-serializable recommendation response.

    Args:
        location_id:   the location key used in the request
        location_info: dict from get_location() or None if location unknown
        meal:          meal period (Breakfast/Lunch/Dinner)
        date:          YYYY-MM-DD string
        ranked_items:  items after scoring, sorted best-first (from rank_items())
        filtered_out:  items rejected by any filter, with filter_reason attached
        top_n:         how many recommendations to include (default 5)
        goal:          the goal string passed in the request

    Returns:
        Dict matching the output schema above, ready for json.dumps().
    """
    location_name = location_info["name"] if location_info else location_id

    # Build recommendation entries from the top N scored items
    recommendations = []
    for item in ranked_items[:top_n]:
        entry = {
            "item": item.get("item_name", item.get("canonical_name", "")),
            "canonical_name": item.get("canonical_name", ""),
            "station": item.get("station", ""),
            "section_type": item.get("section_type", ""),
            "score": item.get("score", 0.0),
            "calories": item.get("calories", 0.0),
            "protein_grams": item.get("protein_grams", 0.0),
            "data_quality": item.get("data_quality", "missing"),
            "reasons": item.get("reasons", []),
        }

        # Surface a note when data is incomplete so the user knows to verify
        if entry["data_quality"] == "missing":
            entry["data_note"] = "Nutrition info unavailable — data not yet in our database."
        elif entry["data_quality"] == "estimated":
            entry["data_note"] = "Nutrition info is approximate."

        # Surface a note when the item's name could not be reliably translated
        if item.get("_unknown"):
            entry["data_note"] = "Item not yet in our database — score may be inaccurate."

        recommendations.append(entry)

    # Build the filtered-out entries (condensed: just name + reason)
    filtered_out_entries = []
    for item in filtered_out:
        filtered_out_entries.append({
            "item": item.get("item_name", item.get("canonical_name", "")),
            "reason": item.get("filter_reason", "filtered"),
        })

    return {
        "location": location_name,
        "location_id": location_id,
        "meal": meal,
        "date": date,
        "goal": goal,
        "targets": targets,
        "recommendations": recommendations,
        "filtered_out": filtered_out_entries,
    }
