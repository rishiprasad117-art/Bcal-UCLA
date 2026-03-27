DISALLOW_STANDALONE = {
  "capers","olives","pickles","salsa","tomatillo salsa",
  "spinach","lettuce","ketchup","mustard","aioli","mayo","croutons","crouton"
}


def is_meal(m: dict) -> bool:
    """
    Valid if:
      - calories >= 350 AND (protein >= 20 OR carbs >= 40)
      - >=2 components
      - not exclusively sauces/dressings/veg
      - none of DISALLOW_STANDALONE present as a single/solo item
    Expects: m = {"components":[{name,bucket,calories,protein,carbs,fat},...],
                   "calories","protein","carbs","fat"}
    """
    comps = m.get("components") or []
    if len(comps) < 2:
        return False
    calories = m.get("calories", 0)
    protein = m.get("protein", 0)
    carbs = m.get("carbs", 0)
    if not (calories >= 350 and (protein >= 20 or carbs >= 40)):
        return False
    # not exclusively sauces/dressings/veg
    non_light = [c for c in comps if c.get("bucket") not in ("dressing","sauce","veg")]
    if not non_light:
        return False
    # no disallowed solo items
    if len(comps) == 1 and comps[0].get("name", "").lower() in DISALLOW_STANDALONE:
        return False
    return True


