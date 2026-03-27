"""
filters.py — hard filters applied before scoring.

These filters are binary: an item either passes or is excluded with a reason.
Filters run in order: diet → allergies → preferences (dislikes/likes).

Each function returns (kept: list, rejected: list).
Rejected items have a "filter_reason" key added for the response layer.

The two-return-value convention is consistent across all three functions so that
engine.py can accumulate filtered_out items incrementally through the pipeline.
"""


def filter_by_diet(items: list[dict], user_profile: dict) -> tuple[list, list]:
    """
    Remove items that don't meet the user's dietary restriction.

    Supported diet values:
        "none"         — no filter applied
        "vegetarian"   — requires item["vegetarian"] == True
        "vegan"        — requires item["vegan"] == True
        "halal"        — requires item["halal"] == True

    Unknown diet values are treated as "none" (no filtering).
    """
    diet = user_profile.get("diet", "none").strip().lower()

    if diet == "none":
        return items, []

    kept = []
    rejected = []

    for item in items:
        passes = False

        if diet == "vegetarian":
            passes = item.get("vegetarian", False)
        elif diet == "vegan":
            passes = item.get("vegan", False)
        elif diet == "halal":
            passes = item.get("halal", False)
        else:
            # Unknown diet value — pass everything through
            passes = True

        if passes:
            kept.append(item)
        else:
            rejected_item = dict(item)
            rejected_item["filter_reason"] = f"not {diet}"
            rejected.append(rejected_item)

    return kept, rejected


def filter_by_allergies(items: list[dict], user_profile: dict) -> tuple[list, list]:
    """
    Remove items that contain any of the user's listed allergens.

    Matching is case-insensitive substring match:
        user allergen "nuts" matches item allergen "tree_nuts" or "peanuts"

    This is intentionally broad to err on the side of safety with UCLA's
    often-incomplete allergen labeling.
    """
    user_allergies = [a.strip().lower() for a in user_profile.get("allergies", [])]

    if not user_allergies:
        return items, []

    kept = []
    rejected = []

    for item in items:
        item_allergens = item.get("allergens", [])  # already lowercased from tagger

        # Find any allergen overlap using substring matching
        matched = None
        for user_allergen in user_allergies:
            for item_allergen in item_allergens:
                if user_allergen in item_allergen or item_allergen in user_allergen:
                    matched = item_allergen
                    break
            if matched:
                break

        if matched:
            rejected_item = dict(item)
            rejected_item["filter_reason"] = f"contains allergen: {matched}"
            rejected.append(rejected_item)
        else:
            kept.append(item)

    return kept, rejected


def filter_by_preferences(items: list[dict], user_profile: dict) -> tuple[list, list]:
    """
    Apply user likes and dislikes.

    Dislikes: remove items whose canonical_name contains any dislike term
              (case-insensitive substring match).
    Likes:    attach _liked=True to items that match a like term.
              Liked items are NOT removed — they receive a score bonus in scorer.py.

    Matching is done against canonical_name and item tags for flexibility.
    """
    dislikes = [d.strip().lower() for d in user_profile.get("dislikes", [])]
    likes = [lk.strip().lower() for lk in user_profile.get("likes", [])]

    kept = []
    rejected = []

    for item in items:
        canonical = item.get("canonical_name", "").lower()
        tags = [t.lower() for t in item.get("tags", [])]

        # Check dislikes: match against canonical name or any tag
        disliked = None
        for dislike in dislikes:
            if dislike in canonical:
                disliked = dislike
                break
            for tag in tags:
                if dislike in tag:
                    disliked = dislike
                    break
            if disliked:
                break

        if disliked:
            rejected_item = dict(item)
            rejected_item["filter_reason"] = f"matches dislike: {disliked}"
            rejected.append(rejected_item)
            continue

        # Check likes: match against canonical name or any tag
        enriched_item = dict(item)
        for like in likes:
            if like in canonical:
                enriched_item["_liked"] = True
                break
            for tag in tags:
                if like in tag:
                    enriched_item["_liked"] = True
                    break
            if enriched_item.get("_liked"):
                break

        kept.append(enriched_item)

    return kept, rejected
