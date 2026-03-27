from typing import List, Dict
from .validator import is_meal


def _sum_macros(xs: List[dict]) -> Dict[str, float]:
    return {
        "calories": int(sum(x.get("calories", 0) for x in xs)),
        "protein": float(sum(x.get("protein", 0) for x in xs)),
        "carbs": float(sum(x.get("carbs", 0) for x in xs)),
        "fat": float(sum(x.get("fat", 0) for x in xs)),
    }


def _score_meal(m: dict) -> float:
    # score = 0.5*protein + 0.2*diversity + 0.2*satiety + 0.1*calorie_closeness
    comps = m.get("components", [])
    buckets = {c.get("bucket") for c in comps}
    diversity = len(buckets)
    satiety = m["protein"] + min(20, m["carbs"] / 2)
    # closeness to 400–650 kcal, peak around ~525
    mid = 525.0
    d = abs(m["calories"] - mid)
    cal_closeness = max(0.0, 1.0 - d / mid)
    return 0.5 * m["protein"] + 0.2 * diversity + 0.2 * satiety + 0.1 * cal_closeness


def _make_meal(name: str, station: str, comps: List[dict], rationale: str) -> dict:
    totals = _sum_macros(comps)
    return {
        "name": name,
        "station": station,
        "components": comps,
        "calories": totals["calories"],
        "protein": totals["protein"],
        "carbs": totals["carbs"],
        "fat": totals["fat"],
        "rationale": rationale,
    }


def compose_meals(tagged: List[dict], station: str, max_out: int = 3) -> List[dict]:
    pool = [x for x in tagged if x.get("station") == station]
    if not pool:
        return []

    def pick(bucket: str) -> List[dict]:
        return [x for x in pool if x.get("bucket") == bucket]

    meals: List[dict] = []

    if station == "SaladBar":
        base = pick("base")
        proteins = sorted(pick("protein"), key=lambda i: i.get("protein", 0), reverse=True)[:3]
        veg = pick("veg")
        fats = pick("fat_cheese")
        crunch = pick("crunch")
        dress = pick("dressing") + pick("sauce")
        for b in base:
            for p in proteins:
                comps = [b, p] + veg[:2]
                if fats: comps.append(fats[0])
                if crunch: comps.append(crunch[0])
                if dress: comps.append(dress[0])
                m = _make_meal(f"{p['name']} Salad Bowl", station, comps, "Base+protein+veg+(fat/crunch/dress)")
                if is_meal(m):
                    meals.append(m)

    elif station == "Deli":
        breads = pick("bread")
        proteins = sorted(pick("protein"), key=lambda i: i.get("protein", 0), reverse=True)[:3]
        veg = pick("veg")
        cheese = pick("fat_cheese")
        sauces = pick("sauce") + pick("dressing")
        for br in breads:
            for p in proteins:
                comps = [br, p] + veg[:2]
                if cheese: comps.append(cheese[0])
                if sauces: comps.append(sauces[0])
                m = _make_meal(f"{p['name']} on {br['name']}", station, comps, "Sandwich template")
                if is_meal(m):
                    meals.append(m)

    elif station in ("Grill", "Global"):
        proteins = pick("protein")[:4]
        starch = pick("starch")
        veg = pick("veg")
        sauces = pick("sauce") + pick("dressing")
        for p in proteins:
            for s in starch:
                comps = [p, s] + veg[:1]
                if sauces: comps.append(sauces[0])
                m = _make_meal(f"{p['name']} Plate with {s['name']}", station, comps, "Protein+starch+veg+sauce")
                if is_meal(m):
                    meals.append(m)

    elif station == "Breakfast":
        eggs_or_pro = pick("protein")[:4]
        starch = pick("starch") + pick("bread")
        vegfruit = pick("veg")
        fats = pick("fat_cheese")
        sauces = pick("sauce") + pick("dressing")
        for p in eggs_or_pro:
            for s in starch:
                comps = [p, s] + vegfruit[:1]
                if fats: comps.append(fats[0])
                if sauces: comps.append(sauces[0])
                m = _make_meal(f"{p['name']} Breakfast Plate", station, comps, "Protein+carb+veg/fruit")
                if is_meal(m):
                    meals.append(m)

    # Rank and return
    meals.sort(key=_score_meal, reverse=True)
    return meals[:max_out]


