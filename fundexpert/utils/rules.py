from __future__ import annotations

import json
import importlib.resources
from functools import lru_cache

@lru_cache(maxsize=1)
def _load_rules_json() -> dict:
    text = importlib.resources.files("fundexpert").joinpath("rules.json").read_text(encoding="utf-8")
    return json.loads(text)

@lru_cache(maxsize=1)
def get_bucket_rules() -> tuple[tuple[str, str], ...]:
    rules = _load_rules_json()
    return tuple(tuple(r) for r in rules.get("bucket_rules", []))

@lru_cache(maxsize=1)
def get_sector_rules() -> tuple[tuple[str, str], ...]:
    rules = _load_rules_json()
    return tuple(tuple(r) for r in rules.get("sector_rules", []))

@lru_cache(maxsize=1)
def get_exclusion_rules() -> tuple[str, ...]:
    rules = _load_rules_json()
    return tuple(rules.get("exclusion_rules", []))

@lru_cache(maxsize=1)
def get_cleanup_rules() -> dict[str, str]:
    rules = _load_rules_json()
    return rules.get("cleanup_rules", {})
