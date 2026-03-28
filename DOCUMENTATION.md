# BCAL — Bruin Calorie and Lifestyle Planner
### Technical Documentation

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Layout](#2-repository-layout)
3. [Architecture Overview](#3-architecture-overview)
4. [Data Flow: Scraper → Pipeline → Recommender](#4-data-flow-scraper--pipeline--recommender)
5. [Module Reference](#5-module-reference)
   - 5.1 [Scrapers (`scrape_*.py`)](#51-scrapers-scrape_py)
   - 5.2 [Ingest Pipeline (`pipeline/ingest.py`)](#52-ingest-pipeline-pipelineingestpy)
   - 5.3 [Recommender Engine (`recommender/`)](#53-recommender-engine-recommender)
   - 5.4 [Meal Planner (`meal_core/`)](#54-meal-planner-meal_core)
   - 5.5 [Flask API (`api.py`)](#55-flask-api-apipy)
   - 5.6 [Streamlit UI (`app.py`)](#56-streamlit-ui-apppy)
   - 5.7 [Integration Layer (`bcal_core.py`)](#57-integration-layer-bcal_corepy)
6. [File Schemas](#6-file-schemas)
   - 6.1 [`data/daily_menu.csv`](#61-datadaily_menucsv)
   - 6.2 [`data/food_tags.csv`](#62-datafood_tagscsv)
   - 6.3 [`data/item_translator.csv`](#63-dataitem_translatorcsv)
   - 6.4 [`data/locations.csv`](#64-datalocationscsv)
   - 6.5 [`data/unresolved_items.csv`](#65-dataunresolved_itemscsv)
   - 6.6 [`data/goal_weights.json`](#66-datagoal_weightsjson)
   - 6.7 [Raw Scraper CSVs (`data/raw/*.csv`)](#67-raw-scraper-csvs-datarawcsv)
7. [API Endpoints](#7-api-endpoints)
8. [Algorithms & Formulas](#8-algorithms--formulas)
9. [How to Run Locally](#9-how-to-run-locally)
10. [Testing](#10-testing)
11. [Known TODOs & Limitations](#11-known-todos--limitations)

---

## 1. Project Overview

BCAL is a UCLA-specific nutrition planner and meal recommender. It scrapes live menu data from all nine UCLA dining locations every day, normalizes and enriches it through an ETL pipeline, then serves personalized food recommendations via a Flask API and Streamlit web UI.

**Core capabilities:**
- Daily menu collection from nine UCLA dining locations via web scraping
- Nutrition enrichment: calories, macros, allergens, and dietary flags per item
- Personalized recommendations filtered by diet, allergens, and preferences
- Goal-aware scoring (cut, bulk, maintain, high-protein, balanced)
- Meal plan composition that hits daily TDEE and macro targets

**Tech stack:** Python 3.11+, Flask, Streamlit, BeautifulSoup4, Pandas, pytest

---

## 2. Repository Layout

```
BCAL/Code/
│
├── api.py                        # Flask REST API
├── app.py                        # Streamlit web UI
├── bcal_core.py                  # Thin integration/bridge layer
├── recommend_demo.py             # Standalone demo of the recommendation engine
├── requirements.txt              # Python package dependencies
│
├── scrape_bruin_plate.py         # Scraper: Bruin Plate
├── scrape_bruin_cafe.py          # Scraper: Bruin Cafe
├── scrape_cafe1919.py            # Scraper: Cafe 1919
├── scrape_deneve.py              # Scraper: De Neve
├── scrape_epic_covel.py          # Scraper: Epicuria at Covel
├── scrape_epic_ackerman.py       # Scraper: Epicuria at Ackerman
├── scrape_fiest.py               # Scraper: Feast at Rieber (Spice Kitchen URL)
├── scrape_rende.py               # Scraper: Rendezvous
├── scrape_thestudy.py            # Scraper: The Study at Hedrick
│
├── pipeline/
│   ├── ingest.py                 # ETL: raw CSVs → recommender-ready data
│   └── autotag.py                # Auto-infer tags for untagged food_tags.csv rows
│
├── frontend/                     # React SPA (Vite + Tailwind CSS)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js            # Dev server + /api/* proxy to Flask :5000
│   ├── tailwind.config.js        # UCLA color palette
│   ├── postcss.config.js
│   └── src/
│       ├── main.jsx
│       ├── index.css
│       ├── App.jsx               # Root state, API calls, layout
│       └── components/
│           ├── LocationMealPicker.jsx   # Location dropdown + meal period pills
│           ├── PreferencesForm.jsx      # Diet / goal / allergies / likes inputs
│           ├── RecommendationCard.jsx   # Single food item card with score
│           └── ResultsView.jsx          # Results list + filtered-out section
│
├── recommender/
│   ├── __init__.py               # Exports recommend()
│   ├── engine.py                 # Pipeline orchestrator
│   ├── menu_loader.py            # Reads daily_menu.csv and locations.csv
│   ├── normalizer.py             # Maps raw UCLA names → canonical names
│   ├── tagger.py                 # Looks up nutrition and tags from food_tags.csv
│   ├── filters.py                # Hard filters: diet, allergens, preferences
│   ├── scorer.py                 # Rule-based scoring via goal_weights.json
│   └── response.py               # JSON response builder
│
├── meal_core/
│   ├── __init__.py               # Exports compute_targets, tag_foods, compose_meals, plan_day
│   ├── planner.py                # Top-level meal plan orchestrator
│   ├── targets.py                # TDEE and macro target calculation
│   ├── tagger.py                 # Regex-based food bucket classification
│   ├── composer.py               # Builds meals from food buckets
│   └── validator.py              # Validates meal completeness
│
├── data/
│   ├── goal_weights.json         # Scoring weights by goal (human-editable)
│   ├── locations.csv             # Static UCLA location metadata
│   ├── daily_menu.csv            # Generated daily by pipeline/ingest.py
│   ├── food_tags.csv             # Nutrition + tag database (incrementally enriched)
│   ├── item_translator.csv       # Raw name → canonical name mapping
│   ├── unresolved_items.csv      # Low-confidence items for manual review
│   └── raw/                      # Scraper output (one CSV per location)
│       ├── ucla_bruin_plate_final_cleaned.csv
│       ├── ucla_bruin_cafe_nutrition_final.csv
│       ├── ucla_cafe_1919_nutrition.csv
│       ├── ucla_de_neve_nutrition_oz.csv
│       ├── ucla_epicuria_final_cleaned.csv
│       ├── ucla_epicuria_ackerman_nutrition.csv
│       ├── ucla_feast_nutrition.csv
│       ├── ucla_rendezvous_nutrition.csv
│       └── ucla_the_study_nutrition.csv
│
└── tests/
    ├── test_meal_core.py         # Unit tests for meal_core
    └── test_edge_cases.py        # Edge case tests for recommender + API
```

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         UCLA Dining Website                         │
│            dining.ucla.edu/{location}/  +  /menu-item/?recipe=N     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  HTTP GET (BeautifulSoup)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SCRAPERS  (scrape_*.py × 9)                     │
│  • detect if closed today                                           │
│  • parse meal period (BREAKFAST / LUNCH / DINNER / …)              │
│  • parse station names                                              │
│  • collect "See Meal Details" links                                 │
│  • visit each detail page → nutrition facts + dietary icons         │
│  • write data/raw/<location>.csv                                    │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  data/raw/*.csv
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   INGEST PIPELINE  (pipeline/ingest.py)             │
│  • normalise column names and units                                 │
│  • infer section_type (rotating / static / build_your_own)         │
│  • append new stubs to food_tags.csv + item_translator.csv         │
│  • write data/daily_menu.csv  (overwritten each run)               │
│  • write data/unresolved_items.csv  (items needing manual review)  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  data/daily_menu.csv
                               │  data/food_tags.csv
                               │  data/item_translator.csv
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│               RECOMMENDER ENGINE  (recommender/)                    │
│                                                                     │
│  engine.py (orchestrator)                                           │
│    ├── menu_loader.py   → load items for location/meal/date        │
│    ├── normalizer.py    → raw name → canonical name                │
│    ├── tagger.py        → canonical name → nutrition + tags        │
│    ├── filters.py       → remove diet / allergen / dislike items   │
│    ├── scorer.py        → score remaining items against goal       │
│    └── response.py      → build structured JSON response           │
└──────────┬──────────────────────────────────┬───────────────────────┘
           │                                  │
           ▼                                  ▼
┌──────────────────┐                ┌─────────────────────────────────┐
│  Flask API       │                │  Streamlit UI  (app.py)         │
│  (api.py)        │                │  • user profile form            │
│  :5000           │                │  • smart meal plan display      │
│  /locations      │                │  • item recommendations         │
│  /menu           │                │  • TDEE + macro summary         │
│  /recommend      │                └─────────────────────────────────┘
└────────┬─────────┘
         │  /api/* proxy (Vite dev server)
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│  React SPA  (frontend/)                                              │
│  • LocationMealPicker  — dining hall + meal period selector          │
│  • PreferencesForm     — diet, goal, allergies, likes/dislikes       │
│  • ResultsView         — ranked recommendation cards                 │
│  • RecommendationCard  — score badge, nutrition, reasons             │
│  :5173 (Vite dev) — /api/* proxied to Flask :5000                   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Flow: Scraper → Pipeline → Recommender

### Step 1 — Scraping (runs once per day, per location)

Each `scrape_*.py` script targets one UCLA dining page. The overall flow:

1. `GET {BASE_URL}` — fetch the main menu page for that location.
2. Check for "closed" signal by scanning `<h1>`/`<h2>`/`<h3>` tags for the word *closed*.
   - If closed: write an empty CSV with only the header row, then exit.
3. Walk all elements to detect **meal period** transitions (`BREAKFAST`, `LUNCH`, `DINNER`, `EXTENDED DINNER`, `ALL DAY`, `LATE NIGHT`).
4. Walk known station names to track the **current station context**.
5. For every `<a>` element whose text contains `"See Meal Details"`:
   - Apply exclusion rules (BYO stations, toppings bars, beverage sections, etc.).
   - Resolve the detail URL and call `get_nutrition_data(url)`.
6. `get_nutrition_data(url)` visits `https://dining.ucla.edu/menu-item/?recipe=N`:
   - Extracts serving size (oz), calories, and 12 macro/mineral fields via regex on the page text.
   - Calls `_parse_icons(soup)` to read `<div class="single-metadata-item-wrapper">` icon images.
   - Returns `is_vegetarian`, `is_vegan`, `is_halal`, and `allergens` (comma-separated).
7. After the loop, filter `menu_items` to keep only items whose meal period appeared on the page (`active_meals` set).
8. Write `data/raw/<filename>.csv`.

**Detail page icon logic (`_parse_icons`):**
```
<div class="single-metadata-item-wrapper">
  <img alt="Vegetarian food item" ...>   → is_vegetarian = True
  <img alt="Vegan food item" ...>        → is_vegan = True, is_vegetarian = True
  <img alt="Halal food item" ...>        → is_halal = True
  <img alt="Contains Gluten" ...>        → allergens += "gluten"
  <img alt="Contains egg" ...>           → allergens += "eggs"
  … (11 allergen types total)
</div>
```
If `get_nutrition_data` returns `{}` (network error / non-200), all dietary fields are `None` in the CSV row, signalling an unreachable detail page to the pipeline.

---

### Step 2 — Ingest Pipeline (`pipeline/ingest.py`)

Run after scrapers. Reads all nine raw CSVs and writes four output files.

| Output | Description | Overwritten? |
|--------|-------------|-------------|
| `data/daily_menu.csv` | Today's canonical menu | Yes |
| `data/food_tags.csv` | Nutrition + tag database | No — new rows appended |
| `data/item_translator.csv` | Name mapping table | No — new rows appended |
| `data/unresolved_items.csv` | Low-confidence items | Yes |

**Key transformations:**
- `parse_num("34.5g")` → `34.5` — strips unit suffixes from nutrition values.
- `infer_section_type(station, location_id)` → `"build_your_own"` (BYO keywords in station name), `"rotating"` (de_neve / bruin_plate / epicuria_covel), or `"static"`.
- `infer_category(name, protein, carbs, fat)` → classifies via ~20 regex patterns, falls back to nutrition thresholds.
- `scrape_bool_to_str(val)` → `"true"` / `"false"` / `"unknown"` — `"unknown"` when the CSV value is blank (detail page was unreachable).
- `scrape_allergens_to_str(allergens_val, is_vegetarian_val)` → allergen string, or `"unknown"` if the detail page was unreachable, or `""` if reachable but no allergens found.

**Existing `food_tags.csv` and `item_translator.csv` rows are never overwritten** — hand-curated tags are preserved across daily runs. Only genuinely new canonical names receive stub rows.

---

### Step 3 — Recommendation Engine (`recommender/`)

Called at request time by `api.py`. Stateless — reads from the pre-built CSV files.

```
recommend(location_id, meal, goal, user_profile, date, top_n)
  │
  ├── menu_loader.get_menu()      → list of raw items for location/meal/date
  │
  ├── normalizer.normalize_item_name()  → canonical_name, category, confidence
  │
  ├── tagger.get_tags_and_nutrition()   → tags, calories, macros, dietary flags
  │
  ├── filters.filter_by_diet()          → hard filter (vegetarian / vegan / halal)
  ├── filters.filter_by_allergies()     → hard filter (allergen substring match)
  ├── filters.filter_by_preferences()   → hard filter (dislikes removed; likes marked)
  │
  ├── scorer.rank_items()               → score each item, sort descending
  │
  └── response.make_response()          → structured JSON
```

---

## 5. Module Reference

### 5.1 Scrapers (`scrape_*.py`)

All nine scrapers share the same structure. Only the configuration constants at the top differ.

#### Per-scraper configuration

| Constant | Purpose |
|----------|---------|
| `BASE_URL` | UCLA dining page for this location |
| `LOCATION_NAME` | Human-readable name (used in log output) |
| `KNOWN_STATIONS` | Station names as they appear in the page HTML |
| `EXCLUDED_SECTIONS` / `EXCLUDED_TERMS` | Stations or keywords to skip (BYO, toppings, beverages) |
| `_MEAL_KEYWORDS` | Set of uppercase strings that signal a meal period change |
| `_OUTPUT_FILE` | Path to the output CSV in `data/raw/` |
| `_EMPTY_COLS` | Column list for the empty CSV written when closed |

#### Location → filename mapping

| Scraper file | Location | Output CSV stem |
|---|---|---|
| `scrape_bruin_plate.py` | Bruin Plate | `ucla_bruin_plate_final_cleaned` |
| `scrape_bruin_cafe.py` | Bruin Cafe | `ucla_bruin_cafe_nutrition_final` |
| `scrape_cafe1919.py` | Cafe 1919 | `ucla_cafe_1919_nutrition` |
| `scrape_deneve.py` | De Neve | `ucla_de_neve_nutrition_oz` |
| `scrape_epic_covel.py` | Epicuria at Covel | `ucla_epicuria_final_cleaned` |
| `scrape_epic_ackerman.py` | Epicuria at Ackerman | `ucla_epicuria_ackerman_nutrition` |
| `scrape_fiest.py` | Feast at Rieber | `ucla_feast_nutrition` |
| `scrape_rende.py` | Rendezvous | `ucla_rendezvous_nutrition` |
| `scrape_thestudy.py` | The Study at Hedrick | `ucla_the_study_nutrition` |

#### Key functions (identical across all scrapers)

**`_is_closed(soup) → bool`**
Scans `<h1>`, `<h2>`, `<h3>` in `#main-content` for the word "closed" (case-insensitive, whole-word). Returns `True` if matched.

**`get_menu_links() → list | None`**
- Returns `None` if the location is closed (triggers empty-CSV write in `main()`).
- Returns `[]` if open but no items found (e.g., menu not yet posted).
- Returns a list of dicts `{Meal, Station, Food Name, url}` otherwise.

**`get_nutrition_data(url) → dict`**
- In-memory cache keyed by URL (avoids re-fetching if the same item appears at multiple meal periods).
- Returns `{}` on network error or non-200 response.
- Fields returned: `Detailed Name`, `Ounces`, `Calories`, 12 nutrient fields, `is_vegetarian`, `is_vegan`, `is_halal`, `allergens`.

**`_parse_icons(soup) → dict`**
Reads `<div class="single-metadata-item-wrapper">` → `<img alt="...">` to set dietary flags and build allergen list.

---

### 5.2 Ingest Pipeline (`pipeline/ingest.py`)

**Entry point:** `run(date_str: str)`

**Usage:**
```bash
python pipeline/ingest.py                     # uses today's date
python pipeline/ingest.py --date 2026-03-25   # tag rows with specific date
```

#### Key functions

| Function | Signature | Description |
|---|---|---|
| `parse_num` | `(val) → float` | Strips unit suffix, returns 0.0 for blank/N/A |
| `infer_section_type` | `(station, location_id) → str` | "build_your_own" / "rotating" / "static" |
| `infer_category` | `(name, protein, carbs, fat) → str` | Regex + nutrition fallback classification |
| `scrape_bool_to_str` | `(val) → str` | "true"/"false"/"unknown" |
| `scrape_allergens_to_str` | `(allergens_val, is_vegetarian_val) → str` | Allergen string or "unknown" |
| `is_low_confidence` | `(section_type, cal, prot, carb, fat) → bool` | True for BYO or zero-nutrition items |
| `translation_confidence` | `(section_type, calories) → str` | "high" or "low" |
| `load_existing_csv` | `(path, key_col) → dict` | Load CSV to dict for dedup/merge |
| `read_raw_csv` | `(path) → list[dict]` | Safe read; returns [] for empty/missing files |

#### BYO detection keywords
`"build"`, `"byo"`, `"create your own"`, `"create-your-own"`, `"salad bar"`, `"toppings bar"`, `"field greens"`, `"greens bar"`

#### Rotating locations
`de_neve`, `bruin_plate`, `epicuria_covel` — these serve a different menu every day; all other locations are `"static"`.

---

### 5.2b Autotag Pipeline (`pipeline/autotag.py`)

**Entry point:** `run()`

**Usage:**
```bash
python pipeline/autotag.py
```

Reads `data/food_tags.csv` and infers tags for every row whose `tags` column is empty or null. Rows with existing tags are never overwritten (hand-curated tags are preserved).

**Tag inference rules** (applied in order, using item name regex + nutrition thresholds):

| Tag | Rule |
|---|---|
| `grilled` | Name contains: grilled, roasted, baked, broiled, steamed, sautéed |
| `fried` | Name contains: fried, crispy, tempura, breaded, battered, nugget, fries, tots |
| `veg_protein` | Name contains: tofu, tempeh, lentil, chickpea, bean, edamame, seitan, falafel |
| `veggies` | Name contains: salad, broccoli, spinach, kale, carrot, cucumber, etc. OR category=veg |
| `creamy` | Name contains: cream, cheese, butter, béchamel, alfredo, mayo, ranch, etc. |
| `sugary` | Name contains: syrup, honey, jam, candy, donut, etc. OR (dessert + sugar > 15g) |
| `starch` | Name contains: rice, pasta, noodle, bread, potato, fries, tater, etc. OR category=starch |
| `protein` | Name contains: chicken, beef, pork, fish, salmon, egg, turkey, etc. OR (protein ≥ 10g AND not beverage/sauce/dessert) |
| `carb` | (carbs ≥ 30g AND not starch AND not beverage/sauce/dessert) |
| `high_volume_low_cal` | (calories ≤ 80 AND protein < 5 AND not beverage/sauce) |
| `high_calorie` | (calories ≥ 400 AND not beverage/sauce) |

**Result after initial run:** 529 total rows — 22 already tagged (unchanged), 397 newly tagged, 110 still untagged (plain beverages, vinaigrettes, zero-nutrition ambiguous items).

---

### 5.3 Recommender Engine (`recommender/`)

#### `recommender/__init__.py`
Exports `recommend()` as the sole public interface. Import as:
```python
from recommender import recommend
```

#### `recommender/engine.py` — orchestrator

```python
recommend(
    location_id: str,
    meal: str,
    goal: str,           # "cut" | "bulk" | "maintain" | "high_protein" | "balanced"
    user_profile: dict,  # {diet, allergies, likes, dislikes}
    date: str | None,    # "YYYY-MM-DD", defaults to today
    top_n: int,          # number of recommendations, default 5
) → dict
```

Pipeline stages are strictly ordered and stateless. Each stage produces a list passed to the next. Filtered-out items accumulate in `filtered_out` with a `filter_reason` field attached.

#### `recommender/menu_loader.py`

**`get_menu(location_id, meal, date) → list[dict]`**
Reads `data/daily_menu.csv`. Returns rows matching location, meal, and date. Each row is a dict with keys: `date`, `location_id`, `meal`, `station`, `item_name`, `section_type`.

**`get_location(location_id) → dict | None`**
Returns location metadata from `data/locations.csv`. Locations are cached module-level after first load.

**`list_locations() → list[dict]`**
Returns all nine locations.

#### `recommender/normalizer.py`

**`normalize_item_name(raw_name) → (canonical_name, category, confidence)`**
Match order:
1. Exact case-insensitive lookup in `item_translator.csv`.
2. Substring match (fuzzy fallback).
3. Identity fallback: returns `(raw_name, "unknown", "low")`.

UCLA item names are often branded or inconsistent (e.g., `"DFC Classic"` → `"Chicken Sandwich"`). The translator table bridges this. New items get identity mappings from the ingest pipeline until manually curated.

#### `recommender/tagger.py`

**`get_tags_and_nutrition(canonical_name) → dict`**
Looks up `data/food_tags.csv` by canonical name (case-insensitive). Returns full nutrition dict including `tags`, `calories`, `protein_grams`, `fat_grams`, `carb_grams`, `vegetarian`, `vegan`, `halal`, `allergens`, `data_quality`.

If the item is not found, returns a **safe stub**:
```python
{
    "_unknown": True,
    "tags": [], "calories": 0, "protein_grams": 0,
    "fat_grams": 0, "carb_grams": 0,
    "vegetarian": False, "vegan": False, "halal": False,
    "allergens": [], "data_quality": "missing"
}
```
All dietary flags default to `False` (safe: don't assume compliance).

#### `recommender/filters.py`

Three hard-filter functions. All return `(kept: list, rejected: list)`. Rejected items have a `filter_reason` string attached.

| Function | What it removes |
|---|---|
| `filter_by_diet(items, user_profile)` | vegetarian: removes non-vegetarian; vegan: removes non-vegan; halal: removes non-halal |
| `filter_by_allergies(items, user_profile)` | items whose `allergens` field contains any user allergen (substring match — intentionally broad) |
| `filter_by_preferences(items, user_profile)` | items whose name contains a disliked term; liked items get `_liked=True` for scoring bonus |

Filter order is always: diet → allergies → preferences.

#### `recommender/scorer.py`

**`score_item(item, goal) → (score: float, reasons: list[str])`**

Formula:
```
score = Σ tag_weights[tag]  +  Σ nutrition_weights[field] × item[field]  +  like_bonus
```

Weights are loaded from `data/goal_weights.json`. `like_bonus = 2` if `item._liked` is set. Only reasons with contribution ≥ 0.5 points are included in the reasons list.

**`rank_items(items, goal) → list`**
Sorts by score descending; tiebreak alphabetically by item name.

#### `recommender/response.py`

**`make_response(...) → dict`**
Builds the final JSON. Top-N ranked items become `recommendations`; all filtered items become `filtered_out`. Each recommendation includes a `data_note` if nutrition data is missing or estimated.

---

### 5.4 Meal Planner (`meal_core/`)

A separate, self-contained module for composing full daily meal plans. Not used by the Flask API directly; exposed via `bcal_core.py` and the Streamlit UI.

#### `meal_core/targets.py`

**`compute_targets(sex, age, height_cm, weight_kg, activity, goal) → dict`**

Uses the Mifflin-St Jeor equation:
```
BMR  = 10×weight_kg + 6.25×height_cm − 5×age + (5 if male else −161)
TDEE = BMR × activity_factor
target_cal = TDEE × goal_multiplier
```

Activity factors: `sedentary=1.20`, `light=1.375`, `moderate=1.55`, `very=1.725`, `athlete=1.90`

Goal multipliers: `maintain=1.00`, `cut=0.85`, `bulk=1.12`, `recomp=1.00`

Macro splits:
- Protein: 1.1 g/lb (cut), 0.9 g/lb (all other goals)
- Fat: max(0.35 g/lb, 20% of total calories) ÷ 9
- Carbs: (target_cal − protein_cal − fat_cal) ÷ 4

#### `meal_core/tagger.py`

**`tag_foods(menu) → list`**
Classifies each menu item into one of nine buckets using regex patterns: `bread`, `base`, `protein`, `starch`, `veg`, `fat_cheese`, `crunch`, `dressing`, `sauce`. Falls back to nutrition-based classification if no pattern matches.

#### `meal_core/composer.py`

**`compose_meals(tagged, station, max_out=3) → list`**
Builds meal combinations per station type:

| Station | Components |
|---|---|
| SaladBar | base + top 3 proteins + 2 veg + fat + crunch + dressing |
| Deli | bread + 3 proteins + 2 veg + cheese + sauce |
| Grill | 4 proteins × starches + veg + sauce |
| Breakfast | 4 proteins × starches + veg/fruit + fat + sauce |

Meal score:
```
score = 0.5×protein + 0.2×diversity + 0.2×satiety + 0.1×cal_closeness
```
Returns top `max_out` meals per station.

#### `meal_core/validator.py`

**`is_meal(m) → bool`**
A composition passes if:
- ≥ 2 components
- calories ≥ 350 AND (protein ≥ 20g OR carbs ≥ 40g)
- not composed exclusively of sauces, dressings, or vegetables
- does not include disallowed solo items: capers, olives, pickles, relish, hot sauce, syrup, jam, butter, honey

#### `meal_core/planner.py`

**`plan_day(menu, user) → dict`**
Orchestrates targets → tag → compose → select. Selects meals that best match the per-meal calorie split (breakfast 25%, lunch 35%, dinner 40% of TDEE). Returns JSON with `targets` and `meals` (breakfast, lunch, dinner).

---

### 5.5 Flask API (`api.py`)

Starts on port 5000. See [Section 7](#7-api-endpoints) for full endpoint documentation.

Run:
```bash
python api.py
```

---

### 5.6 Streamlit UI (`app.py`)

Interactive web UI. Renders a multi-section form + meal plan display.

**Key functions:**
- `main()` — app entry point and page layout
- `generate_smart_meal_plan(user_profile, goal, location_id, meal)` — calls the recommender and formats a plan
- `display_user_profile()` — renders the profile setup form (weight, height, age, sex, activity level)
- `display_smart_meal_plan()` — renders the daily meal plan with calorie targets
- `display_smart_recommendations()` — renders ranked item recommendations with scores and filter reasons

`app.py` defines two local helpers (previously these were broken imports from `bcal_core`):
- `tdee_estimate(weight_lbs, height_in, age, sex, activity) → int` — Mifflin-St Jeor TDEE
- `smart_macro_targets(weight_lbs, target_calories, goal, user_preferences) → (protein_g, carbs_g, fat_g)`

Run:
```bash
streamlit run app.py
```

---

### 5.6b React Frontend (`frontend/`)

A mobile-first single-page app built with React 18, Vite 5, and Tailwind CSS. Calls the Flask API via the Vite dev server proxy.

**Design:** UCLA Blue (`#2774AE`) and Gold (`#FFD100`) accent palette. Single-column layout (`max-w-2xl` centered), works on iPhone and desktop. No external UI component libraries — Tailwind only.

**Component overview:**

| Component | Description |
|---|---|
| `App.jsx` | Root state machine: fetches locations on mount, POSTs to `/api/recommend`, manages loading/error |
| `LocationMealPicker` | `<select>` dropdown for dining hall, pill buttons for meal period |
| `PreferencesForm` | Toggle buttons for diet (blue) and goal (gold); pill toggles for allergens (red); text inputs for likes/dislikes |
| `RecommendationCard` | Shows rank bubble, item name, station, score badge (green ≥8, gold ≥4, gray <4), calories, protein, and scoring reasons |
| `ResultsView` | Summary header, empty state, card list, collapsible "filtered out" section |

**API calls made by the frontend:**
- `GET /api/locations` → populates location dropdown on mount
- `POST /api/recommend` → called on form submit; body mirrors the `/recommend` endpoint schema with `top_n: 10`

**Vite proxy configuration (`vite.config.js`):**
```js
proxy: {
  '/api': {
    target: 'http://localhost:5000',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
}
```
All `/api/*` calls are rewritten to `/*` before forwarding to Flask — no CORS configuration needed during development.

**Environment variable override:**
```bash
VITE_API_BASE=http://192.168.1.10:5000 npm run dev
```

Run:
```bash
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

---

### 5.7 Integration Layer (`bcal_core.py`)

A thin bridge used by earlier prototypes. Provides `generate_meal_plan()`, `_load_menu()`, and `_infer_station()`. Mostly superseded by the `meal_core/` and `recommender/` modules. Kept for compatibility.

---

## 6. File Schemas

### 6.1 `data/daily_menu.csv`

Generated by `pipeline/ingest.py`. Overwritten on every run.

| Column | Type | Description |
|---|---|---|
| `date` | string `YYYY-MM-DD` | Date this menu was scraped |
| `location_id` | string | e.g. `de_neve`, `bruin_plate` |
| `meal` | string | `Breakfast`, `Lunch`, `Dinner`, `Extended Dinner`, etc. |
| `station` | string | Station name as it appeared on the UCLA menu page |
| `item_name` | string | Food name (from detail page header if available, else link text) |
| `section_type` | string | `rotating`, `static`, or `build_your_own` |

---

### 6.2 `data/food_tags.csv`

Incrementally enriched. Existing rows are never overwritten by the pipeline; new items get stub rows that should be manually curated.

| Column | Type | Description |
|---|---|---|
| `canonical_name` | string | Primary key. Stable, human-readable food name |
| `category` | string | `protein`, `starch`, `veg`, `dairy`, `dessert`, `beverage`, `sauce`, `unknown` |
| `tags` | string | Comma-separated scoring tags: `protein`, `grilled`, `fried`, `sugary`, `creamy`, `high_calorie`, `high_volume_low_cal`, `veggies`, `carb`, `starch`, `veg_protein` |
| `calories` | float | Per-serving calories |
| `protein_grams` | float | Grams of protein |
| `fat_grams` | float | Grams of total fat |
| `carb_grams` | float | Grams of total carbohydrate |
| `vegetarian` | string | `"true"`, `"false"`, or `"unknown"` |
| `vegan` | string | `"true"`, `"false"`, or `"unknown"` |
| `halal` | string | `"true"`, `"false"`, or `"unknown"` |
| `allergens` | string | Comma-separated allergen names, `""` (confirmed none), or `"unknown"` |
| `data_quality` | string | `"complete"`, `"estimated"`, or `"missing"` |

**Allergen vocabulary:** `gluten`, `wheat`, `dairy`, `eggs`, `soy`, `peanuts`, `tree_nuts`, `fish`, `shellfish`, `sesame`, `alcohol`

---

### 6.3 `data/item_translator.csv`

Maps raw UCLA item names to canonical names. Existing rows preserved across pipeline runs.

| Column | Type | Description |
|---|---|---|
| `raw_item_name` | string | Primary key. Exactly as scraped from UCLA |
| `canonical_name` | string | Stable name used as key in `food_tags.csv` |
| `category` | string | Same vocabulary as food_tags |
| `translation_confidence` | string | `"high"` or `"low"` |

New items from the ingest pipeline receive identity mappings (`raw = canonical`) with `confidence = "low"` until manually reviewed.

---

### 6.4 `data/locations.csv`

Static file. Manually maintained.

| Column | Type | Description |
|---|---|---|
| `location_id` | string | Primary key used throughout the system |
| `name` | string | Human-readable display name |
| `type` | string | `"dining_hall"` or `"cafe"` |
| `meal_plan_accepted` | bool | Always `True` for current rows |
| `available_meals` | string | Comma-separated meal periods |

**Current locations:**

| location_id | Name | Type | Meals |
|---|---|---|---|
| `de_neve` | De Neve | dining_hall | Breakfast, Lunch, Dinner |
| `bruin_plate` | Bruin Plate | dining_hall | Breakfast, Lunch, Dinner |
| `bruin_cafe` | Bruin Cafe | dining_hall | Breakfast, Lunch, Dinner |
| `epicuria_covel` | Epicuria at Covel | dining_hall | Breakfast, Lunch, Dinner |
| `epicuria_ackerman` | Epicuria at Ackerman | cafe | Lunch, Dinner |
| `feast` | Feast at Rieber | dining_hall | Breakfast, Lunch, Dinner |
| `cafe_1919` | Cafe 1919 | cafe | Breakfast, Lunch, Dinner |
| `rendezvous` | Rendezvous | cafe | Lunch, Dinner |
| `the_study` | The Study at Hedrick | cafe | Breakfast, Lunch, Dinner |

All nine `location_id` values now match the `FILENAME_TO_LOCATION_ID` mapping in `pipeline/ingest.py`.

---

### 6.5 `data/unresolved_items.csv`

Overwritten daily. Items here need manual review before they can be recommended.

| Column | Type | Description |
|---|---|---|
| `location_id` | string | Where the item appears |
| `meal` | string | Meal period |
| `station` | string | Station name |
| `item_name` | string | Raw food name |
| `section_type` | string | Why it was flagged |
| `reason` | string | `"build_your_own station"`, `"zero nutrition"`, or both |
| `date` | string | Date of the run |

---

### 6.6 `data/goal_weights.json`

Controls item scoring. Edit to tune recommendations without touching Python code.

**Top-level keys:** `like_bonus`, `cut`, `bulk`, `maintain`, `high_protein`, `balanced`

Each goal has two sub-objects:

**`tag_weights`** — additive score per tag present on the item:

| Goal | High-weight tags | Penalised tags |
|---|---|---|
| `cut` | protein +4, grilled +3, high_volume_low_cal +3 | fried −4, high_calorie −3, sugary −3 |
| `bulk` | protein +4, carb +2, starch +2, high_calorie +2 | sugary −1 |
| `maintain` | protein +3, veggies +2, grilled +2 | fried −2, sugary −2 |
| `high_protein` | protein +5, veg_protein +4, grilled +2 | sugary −2, carb −1 |
| `balanced` | protein +3, veggies +2, carb +1 | fried −1, sugary −1, high_calorie −1 |

**`nutrition_weights`** — score contribution per unit of the nutrition field:

| Goal | calories | protein_grams |
|---|---|---|
| `cut` | −0.010 | +0.20 |
| `bulk` | +0.005 | +0.15 |
| `maintain` | −0.005 | +0.10 |
| `high_protein` | −0.005 | +0.30 |
| `balanced` | 0.000 | +0.10 |

**`like_bonus`**: `2` — added to the score of any item whose name matches a user like.

---

### 6.7 Raw Scraper CSVs (`data/raw/*.csv`)

Written by scrapers, read by `pipeline/ingest.py`. Columns:

| Column | Source |
|---|---|
| `Meal` | Detected meal period on the page |
| `Station` | Matched KNOWN_STATIONS entry |
| `Food Name` | Detail page `<h1>`/`<h2>` or link text fallback |
| `Ounces` | Serving size from detail page |
| `Calories` | From detail page |
| `Total Fat` | With unit suffix (e.g., `"12g"`) |
| `Saturated Fat` | With unit suffix |
| `Trans Fat` | With unit suffix |
| `Cholesterol` | With unit suffix |
| `Sodium` | With unit suffix |
| `Total Carbohydrate` | With unit suffix |
| `Dietary Fiber` | With unit suffix |
| `Sugars` | With unit suffix |
| `Protein` | With unit suffix |
| `Calcium` | With unit suffix |
| `Iron` | With unit suffix |
| `Potassium` | With unit suffix |
| `is_vegetarian` | `True` / `False` / blank (unreachable) |
| `is_vegan` | `True` / `False` / blank |
| `is_halal` | `True` / `False` / blank |
| `allergens` | Comma-separated names, or blank |

---

## 7. API Endpoints

Base URL: `http://localhost:5000`

---

### `GET /locations`

Returns all UCLA dining locations.

**Response 200:**
```json
[
  {
    "location_id": "de_neve",
    "name": "De Neve",
    "type": "dining_hall",
    "meal_plan_accepted": "True",
    "available_meals": "Breakfast,Lunch,Dinner"
  },
  ...
]
```

---

### `GET /menu`

Returns raw menu items for a location and meal period.

**Query parameters:**

| Parameter | Required | Description |
|---|---|---|
| `location` | Yes | `location_id` string |
| `meal` | Yes | `Breakfast`, `Lunch`, or `Dinner` |
| `date` | No | `YYYY-MM-DD` — defaults to today |

**Response 200:**
```json
{
  "location_id": "de_neve",
  "meal": "Lunch",
  "date": "2026-03-25",
  "count": 24,
  "items": [
    {
      "date": "2026-03-25",
      "location_id": "de_neve",
      "meal": "Lunch",
      "station": "Bruin Wok",
      "item_name": "Kung Pao Chicken",
      "section_type": "rotating"
    },
    ...
  ]
}
```

**Response 400:**
```json
{ "error": "Both 'location' and 'meal' query parameters are required." }
```

---

### `POST /recommend`

Main recommendation endpoint.

**Request body (JSON):**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `location_id` | string | Yes | — | e.g. `"de_neve"` |
| `meal` | string | Yes | — | `"Breakfast"`, `"Lunch"`, `"Dinner"` |
| `goal` | string | No | `"balanced"` | `"cut"`, `"bulk"`, `"maintain"`, `"high_protein"`, `"balanced"` |
| `diet` | string | No | `"none"` | `"none"`, `"vegetarian"`, `"vegan"`, `"halal"` |
| `allergies` | string[] | No | `[]` | e.g. `["gluten", "shellfish"]` |
| `likes` | string[] | No | `[]` | Preferred food terms |
| `dislikes` | string[] | No | `[]` | Avoided food terms |
| `date` | string | No | today | `"YYYY-MM-DD"` |
| `top_n` | int | No | `5` | Number of recommendations to return |

**Example request:**
```json
{
  "location_id": "de_neve",
  "meal": "Lunch",
  "goal": "cut",
  "diet": "vegetarian",
  "allergies": ["gluten"],
  "likes": ["tofu", "broccoli"],
  "dislikes": ["mushrooms"],
  "top_n": 3
}
```

**Response 200:**
```json
{
  "location": "De Neve",
  "location_id": "de_neve",
  "meal": "Lunch",
  "date": "2026-03-25",
  "goal": "cut",
  "recommendations": [
    {
      "item": "Stir-Fried Tofu",
      "canonical_name": "Stir-Fried Tofu",
      "station": "Bruin Wok",
      "section_type": "rotating",
      "score": 11.4,
      "calories": 210,
      "protein_grams": 14.0,
      "data_quality": "complete",
      "data_note": null,
      "reasons": [
        "protein: good for cut (+4.0 pts)",
        "veg_protein: plant-based protein (+2.0 pts)",
        "protein contribution: +2.80 pts"
      ]
    }
  ],
  "filtered_out": [
    {
      "item": "Cheese Pizza",
      "filter_reason": "not vegetarian"
    }
  ]
}
```

**Response 400:**
```json
{ "error": "Both 'location_id' and 'meal' are required." }
```

---

## 8. Algorithms & Formulas

### TDEE Calculation (Mifflin-St Jeor)

```
BMR = 10 × weight_kg  +  6.25 × height_cm  −  5 × age  +  (5  if male  else  −161)
TDEE = BMR × activity_factor
target_calories = TDEE × goal_multiplier
```

### Macro Targets

```
protein_g = weight_lb × (1.1 if cut else 0.9)
fat_g     = max(weight_lb × 0.35,  target_calories × 0.20 / 9)
carbs_g   = (target_calories − protein_g × 4 − fat_g × 9) / 4
```

### Meal Calorie Splits (meal_core)

```
breakfast_cal = target_calories × 0.25
lunch_cal     = target_calories × 0.35
dinner_cal    = target_calories × 0.40
```

### Meal Composition Score (meal_core/composer.py)

```
diversity    = number of distinct component buckets in the meal
satiety      = protein_g + min(20, carbs_g / 2)
cal_closeness = max(0, 1 − |calories − target_per_meal| / target_per_meal)

score = 0.5 × protein_g  +  0.2 × diversity  +  0.2 × satiety  +  0.1 × cal_closeness
```

### Item Recommendation Score (recommender/scorer.py)

```
score = Σ goal_weights.tag_weights[tag]          (for each tag on the item)
      + Σ goal_weights.nutrition_weights[field] × item[field]
      + like_bonus  (2 if item._liked else 0)
```

All weights are defined in `data/goal_weights.json` — no magic numbers in code.

---

## 9. How to Run Locally

### Prerequisites

```bash
pip install -r requirements.txt
```

Python 3.11+ is required for the `str | None` union type syntax used in `recommender/engine.py`.

For the React frontend, Node 18+ is required:
```bash
cd frontend && npm install
```

### 1. Run the scrapers

Run each scraper individually. UCLA only posts menus during or just before active service windows, so scrapers will output empty CSVs outside those windows.

```bash
python scrape_deneve.py
python scrape_bruin_plate.py
python scrape_epic_covel.py
python scrape_epic_ackerman.py
python scrape_bruin_cafe.py
python scrape_cafe1919.py
python scrape_rende.py
python scrape_thestudy.py
python scrape_fiest.py
```

### 2. Run the ingest pipeline

```bash
python pipeline/ingest.py
```

This overwrites `data/daily_menu.csv` and appends new rows to `data/food_tags.csv` and `data/item_translator.csv`.

### 3. Run autotag (optional but recommended)

```bash
python pipeline/autotag.py
```

Fills in tags for any items in `food_tags.csv` that the pipeline added without tags. Safe to re-run — existing tags are never overwritten.

### 4. Start the Flask API

```bash
python api.py
# → http://localhost:5000
```

### 5. Start the React frontend

```bash
cd frontend
npm run dev
# → http://localhost:5173
```

Vite proxies all `/api/*` requests to Flask on port 5000 — no CORS setup needed.

### 6. Start the Streamlit UI (alternative to React)

```bash
streamlit run app.py
# → http://localhost:8501
```

### Typical daily workflow

```bash
# 1. Scrape all locations
for f in scrape_*.py; do python "$f"; done

# 2. Run pipeline
python pipeline/ingest.py
python pipeline/autotag.py

# 3. Optionally review flagged items
cat data/unresolved_items.csv

# 4. Start services
python api.py &
cd frontend && npm run dev
```

### Quick API smoke test

```bash
# List locations
curl http://localhost:5000/locations

# Get today's De Neve lunch menu
curl "http://localhost:5000/menu?location=de_neve&meal=Lunch"

# Get cut-goal recommendations
curl -X POST http://localhost:5000/recommend \
  -H "Content-Type: application/json" \
  -d '{"location_id":"de_neve","meal":"Lunch","goal":"cut","diet":"vegetarian","allergies":["gluten"]}'
```

---

## 10. Testing

```bash
# Run all tests
pytest tests/

# Run a specific file
pytest tests/test_edge_cases.py -v
```

### `tests/test_meal_core.py`

| Test | What it verifies |
|---|---|
| `test_targets_cut` | TDEE and protein calculation for a cut goal |
| `test_no_component_only_recommendations` | Composed meals have ≥2 components; disallowed standalone items excluded |
| `test_planner_returns_three_meals` | `plan_day()` always returns breakfast, lunch, and dinner keys |

### `tests/test_edge_cases.py`

| Test | What it verifies |
|---|---|
| `test_empty_menu_returns_no_recommendations` | Empty menu → empty `recommendations` list |
| `test_all_items_filtered_out_by_diet` | Vegan filter → all items in `filtered_out` |
| `test_unknown_item_survives_pipeline_with_warning` | Items with no translator or tag entry pass through with `data_quality="missing"` |
| `test_dislike_wins_over_like` | Disliked items are removed even if they also match a like |
| `test_scoring_with_zero_nutrition_does_not_crash` | Zero-nutrition items score `0.0` without NaN or Inf |
| `test_scoring_with_zero_nutrition_all_goals` | Zero-nutrition behaviour is consistent across all five goals |
| `test_api_returns_400_for_missing_required_fields` | `/recommend` with missing `location_id` or `meal` → 400 |
| `test_api_returns_200_with_empty_recommendations_for_unknown_location` | Unknown `location_id` → 200 with empty recommendations |

---

## 11. Known TODOs & Limitations

### Data

- **`food_tags.csv` tags are partially auto-inferred.** After running `pipeline/autotag.py`, ~110 items remain untagged (plain beverages, vinaigrettes, zero-nutrition ambiguous items). These score `0.0` and rank last until manually tagged or the autotag rules are extended.

- **Allergen data is incomplete on the UCLA site.** UCLA does not publish allergen data for all items. Items scraped before the `_parse_icons` update, or where the detail page was unreachable, have `allergens = "unknown"` in `food_tags.csv`. These items will not be filtered out by allergen rules — they will pass through silently.

- **`unresolved_items.csv` requires manual follow-up.** BYO and zero-nutrition items are flagged but nothing automatically prevents them from appearing in recommendations. They score 0 and will rank last, but they won't be excluded unless manually tagged or moved to an exclusion list.

- **No mechanism to re-run scrapers on stale data.** If a scraper fails (network error, changed HTML), the previous CSV remains on disk and is silently used. There is no staleness check or last-modified timestamp.

### Recommender

- **`meal_core` and `recommender` are parallel systems.** `meal_core` builds composed multi-item meals; `recommender` ranks individual items. They use the same underlying data files but have separate tagger implementations (`meal_core/tagger.py` vs. `recommender/tagger.py`) with different regex patterns. A unified tagging layer would reduce duplication and inconsistency.

- **No personalisation memory.** User profiles are stateless — each API call is independent. There is no history of what a user has eaten, liked, or disliked across sessions.

- **Filter safety defaults may over-filter.** Unknown items default to `vegetarian=False`, `vegan=False`, `halal=False`. A vegan user will have all unknown-data items filtered out, potentially leaving very few recommendations if data coverage is low.

- **`filter_by_allergies` uses substring matching.** `"nuts"` matches `"tree_nuts"` and `"peanuts"`, which is intentionally safe but may occasionally over-filter (e.g., `"soy"` matching an item tagged `"soy sauce"`).

### Infrastructure

- **No scheduling.** Scrapers must be triggered manually or via an external cron job. There is no built-in scheduler or retry logic.

- **No deduplication across meal periods.** If an item appears at both Lunch and Dinner (common for static locations), it gets two rows in `daily_menu.csv` and may create a duplicate stub in `food_tags.csv` if it wasn't present before — protected only by the `canonical_name` dedup check in `ingest.py`.

- **No deployment configuration.** There is no `Dockerfile`, `Procfile`, or environment variable documentation. The Flask server runs with `debug=True` which is not suitable for production.

- **React frontend requires Vite dev server for the API proxy.** In production, either: (a) copy `frontend/dist/` into Flask's static folder and add a catch-all `index.html` route, or (b) install `flask-cors` and set `VITE_API_BASE` at build time. Neither is currently configured.

- **`scrape_fiest.py` uses the Spice Kitchen URL** (`https://dining.ucla.edu/spice-kitchen/`) but outputs to `ucla_feast_nutrition.csv` and uses `LOCATION_NAME = "Feast at Rieber"`. These two dining halls appear to share a menu page, but the discrepancy is confusing and should be documented or resolved.
