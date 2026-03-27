"""
meal_core package - deterministic, LLM-free meal planner
"""

from .targets import compute_targets  # noqa: F401
from .tagger import tag_foods         # noqa: F401
from .composer import compose_meals   # noqa: F401
from .planner import plan_day         # noqa: F401


