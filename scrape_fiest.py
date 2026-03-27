import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os

# --- CONFIGURATION ---
BASE_URL = "https://dining.ucla.edu/spice-kitchen/"
DOMAIN = "https://dining.ucla.edu"
LOCATION_NAME = "Feast at Rieber"

# KNOWN STATIONS (Specific to Feast at Rieber)
KNOWN_STATIONS = [
    "Stone Oven",
    "Spice Kitchen",
    "Iron Grill",
    "Feast Toppings Bar",
    "Sweets Station",
    "Greens",
    "Beverages",
    "Sides"
]

# EXCLUDED SECTIONS
EXCLUDED_SECTIONS = [
    "Feast Toppings Bar",
    "Feast Salad Bar Selections"
]

_MEAL_KEYWORDS = {"BREAKFAST", "LUNCH", "DINNER", "EXTENDED DINNER", "LUNCH / DINNER", "ALL DAY", "LATE NIGHT"}

_OUTPUT_FILE = "data/raw/ucla_feast_nutrition.csv"

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


def get_menu_links():
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

    elements = main_content.find_all(['h2', 'h3', 'h4', 'h5', 'li', 'div', 'p', 'span', 'a'])

    for elem in elements:
        text = elem.get_text(strip=True)
        if not text: continue

        # 1. Update Meal Period
        if text.upper() in _MEAL_KEYWORDS:
            current_meal = text.title()
            active_meals.add(current_meal)
            continue

        # 2. Update Station (Section Logic)
        if len(text) < 50:
            for station in KNOWN_STATIONS:
                if text.lower() == station.lower():
                    current_station = station
                    break

        # 3. Process Food Item
        if elem.name == 'a' and 'See Meal Details' in text:

            # --- EXCLUSION LOGIC ---
            is_excluded = False
            for excl in EXCLUDED_SECTIONS:
                if excl.lower() in current_station.lower():
                    is_excluded = True
                    break

            if is_excluded:
                continue
            # -----------------------

            href = elem.get('href')
            parent = elem.find_parent('li') or elem.find_parent('div')

            if parent:
                full_text = parent.get_text(strip=True)
                food_name = full_text.replace("See Meal Details", "").strip()

                if href:
                    full_url = DOMAIN + href if href.startswith('/') else href

                    if menu_items and menu_items[-1]['url'] == full_url and menu_items[-1]['Meal'] == current_meal:
                        continue

                    menu_items.append({
                        'Meal': current_meal,
                        'Station': current_station,
                        'Food Name': food_name,
                        'url': full_url
                    })

    # Only keep items for meal periods detected on this page
    if active_meals:
        menu_items = [it for it in menu_items if it['Meal'] in active_meals]

    print(f"Found {len(menu_items)} items.")
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
    """Visits the detail page to get Nutrition Facts and Ounces."""
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
        data['Detailed Name'] = header.get_text(strip=True)

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
    items = get_menu_links()

    if items is None:  # Location is closed
        os.makedirs("data/raw", exist_ok=True)
        pd.DataFrame(columns=_EMPTY_COLS).to_csv(_OUTPUT_FILE, index=False)
        return

    if not items:
        print("No items found. Check if the menu is empty.")
        return

    full_data = []
    print(f"Scraping nutrition for {len(items)} items...")

    for i, item in enumerate(items):
        if i % 10 == 0: print(f"Processing {i}/{len(items)}...")

        nutri_data = get_nutrition_data(item['url'])
        final_name = nutri_data.get('Detailed Name', item['Food Name'])

        row = {
            'Meal': item['Meal'],
            'Station': item['Station'],
            'Food Name': final_name,
            'Ounces': nutri_data.get('Ounces'),
            'Calories': nutri_data.get('Calories'),
            'Total Fat': nutri_data.get('Total Fat'),
            'Saturated Fat': nutri_data.get('Saturated Fat'),
            'Trans Fat': nutri_data.get('Trans Fat'),
            'Cholesterol': nutri_data.get('Cholesterol'),
            'Sodium': nutri_data.get('Sodium'),
            'Total Carbohydrate': nutri_data.get('Total Carbohydrate'),
            'Dietary Fiber': nutri_data.get('Dietary Fiber'),
            'Sugars': nutri_data.get('Sugars'),
            'Protein': nutri_data.get('Protein'),
            'Calcium': nutri_data.get('Calcium'),
            'Iron': nutri_data.get('Iron'),
            'Potassium': nutri_data.get('Potassium'),
            'is_vegetarian': nutri_data.get('is_vegetarian'),
            'is_vegan': nutri_data.get('is_vegan'),
            'is_halal': nutri_data.get('is_halal'),
            'allergens': nutri_data.get('allergens'),
        }
        full_data.append(row)
        time.sleep(0.1)

    df = pd.DataFrame(full_data)
    df = df.reindex(columns=_EMPTY_COLS)

    os.makedirs("data/raw", exist_ok=True)
    df.to_csv(_OUTPUT_FILE, index=False)
    print(f"Done! Saved to {_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
