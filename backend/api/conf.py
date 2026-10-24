"""Reads config.json once (single source for tuneable numbers, spec 3.11)."""
import json
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _load() -> dict:
    return json.loads((settings.REPO_ROOT / "config.json").read_text(encoding="utf-8"))


def cfg(*path, default=None):
    node = _load()
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def level_for(points: int) -> dict:
    levels = sorted(cfg("levels", default=[]), key=lambda l: l["min_points"])
    current = levels[0] if levels else {"id": "L1", "name": "Beginner", "min_points": 0}
    nxt = None
    for lv in levels:
        if points >= lv["min_points"]:
            current = lv
        elif nxt is None:
            nxt = lv
    return {"id": current["id"], "name": current["name"], "min_points": current["min_points"],
            "next": ({"id": nxt["id"], "name": nxt["name"], "min_points": nxt["min_points"]} if nxt else None)}
