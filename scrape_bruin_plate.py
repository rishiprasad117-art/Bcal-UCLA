import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os

# Base URL
BASE_URL = "https://dining.ucla.edu/bruin-plate/"
DOMAIN = "https://dining.ucla.edu"
LOCATION_NAME = "Bruin Plate"

# --- CONFIGURATION: ITEMS TO SKIP ---
EXCLUDED_TERMS = [
    "Frozen Yogurt",
    "Salad Bar",
    "Create-Your-Own",
    "Greens 'N More", "Yogurt Bar",
    "BYO"
]

_MEAL_KEYWORDS = {"BREAKFAST", "LUNCH", "DINNER", "EXTENDED DINNER"}

_OUTPUT_FILE = "data/raw/ucla_bruin_plate_final_cleaned.csv"

_EMPTY_COLS = [
    "Meal", "Station", "Food Name", "Ounces", "Calories", "Total Fat",
    "Saturated Fat", "Trans Fat", "Cholesterol", "Sodium",
    "Total Carbohydrate", "Dietary Fiber", "Sugars", "Protein",
    "Calcium", "Iron", "Potassium",
    "is_vegetarian", "is_vegan", "is_halal", "allergens"
]


def _is_closed(soup) -> bool:
    """Return True if the page signals the location is closed today."""
    main = soup.find('div', id='main-content') or soup.find('body')
    for tag in main.find_all(['h1', 'h2', 'h3']):
        if re.search(r'\bclosed\b', tag.get_text(strip=True), re.I):
            return True
    return False


def get_full_menu_list():
    """Scrapes the menu but FILTERS OUT specific stations and BYO items."""
    print(f"Fetching menu from {BASE_URL}...")
    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching menu: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    # --- AVAILABILITY CHECK ---
    if _is_closed(soup):
        print(f"{LOCATION_NAME} is closed today — skipping.")
        return None
    # -------------------------

    menu_items = []
    active_meals = set()

    current_meal = "Unknown"
    current_station = "Unknown"

    main_content = soup.find('div', id='main-content') or soup.find('body')

    elements = main_content.find_all(['h2', 'h3', 'h4', 'li', 'div', 'a'])

    for elem in elements:
        text = elem.get_text(strip=True)

        # 1. Detect Meal Period
        if text.upper() in _MEAL_KEYWORDS:
            current_meal = text.title()
            active_meals.add(current_meal)
            continue

        # 2. Detect Station
        known_stations = [
            "Freshly Bowled", "Harvest", "Stone Fired", "Simply Grilled",
            "Fruit", "Sweet Bites", "Yogurt Bar", "Beverage Special",
            "Greens 'N More", "Cereal / Oatmeal", "Soups", "Farmstand", "Frozen Yogurt"
        ]

        if text in known_stations:
            current_station = text
            continue

        # 3. Detect Food Item Link
        if elem.name == 'a' and 'See Meal Details' in text:
            href = elem.get('href')

            parent = elem.find_parent('li')
            if not parent:
                parent = elem.find_parent('div')

            if parent:
                full_text = parent.get_text(strip=True)
                food_name = full_text.replace("See Meal Details", "").strip()

                should_skip = False
                for term in EXCLUDED_TERMS:
                    if term.lower() in current_station.lower() or term.lower() in food_name.lower():
                        should_skip = True
                        break

                if should_skip:
                    continue

                if href:
                    full_url = DOMAIN + href if href.startswith('/') else href

                    menu_items.append({
                        'Meal': current_meal,
                        'Station': current_station,
                        'Menu Name': food_name,
                        'url': full_url
                    })

    # Only keep items for meal periods detected on this page
    if active_meals:
        menu_items = [it for it in menu_items if it['Meal'] in active_meals]

    print(f"Found {len(menu_items)} valid menu items (filtered).")
    return menu_items


def _parse_icons(soup) -> dict:
    """Parse dietary flags and allergens from single-metadata-item-wrapper icons."""
    _ALLERGEN_MAP = [
        ('gluten',    ['gluten']),
        ('wheat',     ['wheat']),
        ('dairy',     ['dairy', 'milk']),
        ('eggs',      ['egg']),
        ('soy',       ['soy']),
        ('peanuts',   ['peanut']),
        ('tree_nuts', ['tree nut']),
        ('fish',      ['fish']),
        ('shellfish', ['shellfish', 'crustacean']),
        ('sesame',    ['sesame']),
        ('alcohol',   ['alcohol']),
    ]
    is_vegetarian = False
    is_vegan = False
    is_halal = False
    allergens = []
    for div in soup.find_all('div', class_='single-metadata-item-wrapper'):
        img = div.find('img')
        if not img:
            continue
        alt = img.get('alt', '').lower()
        if 'vegetarian food item' in alt:
            is_vegetarian = True
            continue
        if 'vegan food item' in alt:
            is_vegan = True
            is_vegetarian = True
            continue
        if 'halal food item' in alt:
            is_halal = True
            continue
        for name, kws in _ALLERGEN_MAP:
            if any(kw in alt for kw in kws) and name not in allergens:
                allergens.append(name)
                break
    return {
        'is_vegetarian': is_vegetarian,
        'is_vegan': is_vegan,
        'is_halal': is_halal,
        'allergens': ','.join(allergens),
    }


def get_nutrition_data(url):
    """Visits detail page to get Calories, Ounces, and Nutrients. Includes caching."""
    if hasattr(get_nutrition_data, "cache") and url in get_nutrition_data.cache:
        return get_nutrition_data.cache[url]

    try:
        response = requests.get(url)
        if response.status_code != 200: return {}
    except:
        return {}

    soup = BeautifulSoup(response.text, 'html.parser')
    data = {}

    header = soup.find(['h1', 'h2'])
    if header:
        data['Food Name'] = header.get_text(strip=True)

    text_content = soup.get_text(" ", strip=True)

    oz_match = re.search(r"Serving Size[:\s]+([\d\.]+)\s*oz", text_content, re.IGNORECASE)
    data['Ounces'] = oz_match.group(1) if oz_match else None

    cal_match = re.search(r"Calories\s*(\d+)", text_content, re.IGNORECASE)
    data['Calories'] = cal_match.group(1) if cal_match else "N/A"

    target_nutrients = [
        "Total Fat", "Saturated Fat", "Trans Fat", "Cholesterol",
        "Sodium", "Total Carbohydrate", "Dietary Fiber", "Sugars",
        "Protein", "Calcium", "Iron", "Potassium"
    ]

    for nutrient in target_nutrients:
        pattern = re.compile(rf"{nutrient}\s*([\d\.]+)\s*([a-zA-Z%µ]*)", re.IGNORECASE)
        match = pattern.search(text_content)
        if match:
            data[nutrient] = f"{match.group(1)}{match.group(2)}"
        else:
            data[nutrient] = None

    # Parse dietary/allergen icons
    data.update(_parse_icons(soup))

    if not hasattr(get_nutrition_data, "cache"):
        get_nutrition_data.cache = {}
    get_nutrition_data.cache[url] = data

    return data


def main():
    menu_list = get_full_menu_list()

    if menu_list is None:  # Location is closed
        os.makedirs("data/raw", exist_ok=True)
        pd.DataFrame(columns=_EMPTY_COLS).to_csv(_OUTPUT_FILE, index=False)
        return

    if not menu_list:
        print("No items found.")
        return

    full_data = []
    print(f"Starting nutrition extraction for {len(menu_list)} items...")

    for i, item in enumerate(menu_list):
        if i % 10 == 0:
            print(f"Processing {i}/{len(menu_list)}...")

        nutri = get_nutrition_data(item['url'])
        combined = {**item, **nutri}
        full_data.append(combined)

        time.sleep(0.1)

    if full_data:
        df = pd.DataFrame(full_data)

        cols = ['Meal', 'Station', 'Food Name', 'Ounces', 'Calories'] + \
               [c for c in df.columns if c not in ['Meal', 'Station', 'Food Name', 'Ounces', 'Calories', 'Menu Name', 'url']]
        cols = [c for c in cols if c in df.columns]

        df = df[cols]
        df = df.reindex(columns=_EMPTY_COLS)

        os.makedirs("data/raw", exist_ok=True)
        df.to_csv(_OUTPUT_FILE, index=False)
        print(f"Done! Saved to {_OUTPUT_FILE}")
    else:
        print("No data extracted.")


if __name__ == "__main__":
    main()
