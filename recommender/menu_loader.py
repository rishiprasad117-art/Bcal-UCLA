"""
menu_loader.py — loads menu items and location info from CSV data files.

Data source: data/daily_menu.csv and data/locations.csv
These are the TARGET SCHEMAS for UCLA dining data.

TODO: Replace CSV reads with scraper/API output once the data pipeline is built.
      UCLA menu data is inconsistent — the pipeline will normalize it into this schema.
"""

import csv
import datetime
import os

# Resolve paths relative to this file so the module works from any working directory
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_MENU_CSV = os.path.join(_DATA_DIR, "daily_menu.csv")
_LOCATIONS_CSV = os.path.join(_DATA_DIR, "locations.csv")

# Module-level cache for locations (static, loaded once)
_LOCATIONS = None

# Maps canonical frontend meal names to the set of meal-period strings that
# appear in daily_menu.csv and should be treated as equivalent.
_MEAL_ALIASES: dict[str, set[str]] = {
    "breakfast": {"breakfast", "all day", "extended breakfast"},
    "lunch":     {"lunch", "all day", "lunch / dinner", "extended lunch"},
    "dinner":    {"dinner", "all day", "lunch / dinner", "extended dinner", "late night"},
}


def _load_locations() -> dict:
    """Load all UCLA meal-plan locations from CSV into a dict keyed by location_id."""
    global _LOCATIONS
    if _LOCATIONS is not None:
        return _LOCATIONS

    _LOCATIONS = {}
    with open(_LOCATIONS_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            loc_id = row["location_id"].strip()
            _LOCATIONS[loc_id] = {
                "location_id": loc_id,
                "name": row["name"].strip(),
                "type": row["type"].strip(),
                "meal_plan_accepted": row["meal_plan_accepted"].strip().lower() == "true",
                # available_meals stored as a list, e.g. ["Breakfast", "Lunch", "Dinner"]
                "available_meals": [
                    m.strip() for m in row["available_meals"].split(",")
                ],
            }
    return _LOCATIONS


def get_location(location_id: str) -> dict | None:
    """Return location metadata dict for the given location_id, or None if not found."""
    locs = _load_locations()
    return locs.get(location_id.strip().lower())


def list_locations() -> list[dict]:
    """Return all UCLA meal-plan-accepted locations as a list of dicts."""
    locs = _load_locations()
    return list(locs.values())


def get_menu(location_id: str, meal: str, date: str | None = None) -> list[dict]:
    """
    Load menu items for a specific location, meal period, and date.

    Args:
        location_id: e.g. "de_neve", "bruin_plate"
        meal:        "Breakfast", "Lunch", or "Dinner" (case-insensitive)
        date:        "YYYY-MM-DD" string; defaults to today if None

    Returns:
        List of raw menu item dicts. Each dict has:
            item_name, location_id, meal, station, section_type, date
        Returns [] if no rows match — not an error.

    TODO: When the data pipeline is live, replace this function body with a call
          to the pipeline's data access layer instead of reading a CSV directly.
    """
    if date is None:
        date = datetime.date.today().isoformat()

    location_id = location_id.strip().lower()
    meal = meal.strip()
    accepted_meals = _MEAL_ALIASES.get(meal.lower(), {meal.lower()})

    results = []
    with open(_MENU_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_date = row["date"].strip()
            row_loc = row["location_id"].strip().lower()
            row_meal = row["meal"].strip()

            if (row_date == date
                    and row_loc == location_id
                    and row_meal.lower() in accepted_meals):
                results.append({
                    "item_name": row["item_name"].strip(),
                    "location_id": row_loc,
                    "meal": row_meal,
                    "station": row["station"].strip(),
                    "section_type": row["section_type"].strip(),
                    "date": row_date,
                })

    return results
