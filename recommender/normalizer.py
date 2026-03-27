"""
normalizer.py — maps raw UCLA menu item names to canonical names.

UCLA dining item names are often branded, inconsistent, or ambiguous.
Example: "DFC Classic" -> "Chicken Sandwich", "Citrus Herb Tofu" -> "Tofu Entree"

The translator table (item_translator.csv) is the bridge between the raw scraped
menu and our internal canonical food representation.

TODO: As more UCLA items are seen, grow item_translator.csv with new mappings.
      Flag low-confidence translations for human review to catch mislabels.
      Future: consider fuzzy-match fallback to suggest probable translations for unknowns.
"""

import csv
import os

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_TRANSLATOR_CSV = os.path.join(_DATA_DIR, "item_translator.csv")

# Module-level cache: loaded once on first call
_TRANSLATOR: dict | None = None


def _load_translator() -> dict:
    """
    Load item_translator.csv into a dict keyed by lowercased raw_item_name.
    Value: { canonical_name, category, translation_confidence }
    """
    global _TRANSLATOR
    if _TRANSLATOR is not None:
        return _TRANSLATOR

    _TRANSLATOR = {}
    with open(_TRANSLATOR_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row["raw_item_name"].strip().lower()
            _TRANSLATOR[key] = {
                "canonical_name": row["canonical_name"].strip(),
                "category": row["category"].strip(),
                "translation_confidence": row["translation_confidence"].strip(),
            }
    return _TRANSLATOR


def normalize_item_name(raw_name: str) -> tuple[str, str, str]:
    """
    Map a raw UCLA menu item name to (canonical_name, category, translation_confidence).

    Match priority:
      1. Exact case-insensitive match
      2. Substring match (raw_name appears in a known key, or vice versa)
      3. Identity fallback — returns (raw_name, "unknown", "low")

    The fallback keeps unknown items in the pipeline rather than crashing.
    They will score 0 due to missing food_tags entries and appear at the bottom.

    TODO: Log items that hit the fallback path for pipeline review.
    """
    translator = _load_translator()
    key = raw_name.strip().lower()

    # 1. Exact match
    if key in translator:
        entry = translator[key]
        return entry["canonical_name"], entry["category"], entry["translation_confidence"]

    # 2. Substring match (check if raw name contains a known key, or known key contains raw name)
    for known_key, entry in translator.items():
        if known_key in key or key in known_key:
            return entry["canonical_name"], entry["category"], "low"

    # 3. Identity fallback
    return raw_name, "unknown", "low"
