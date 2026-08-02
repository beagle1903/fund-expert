from __future__ import annotations

import copy
import json
import os
import tempfile
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any


RULES_FILE = Path(__file__).resolve().parent.parent / "rules.json"
_rules_write_lock = threading.Lock()


def _read_rules_json() -> dict[str, Any]:
    text = RULES_FILE.read_text(encoding="utf-8")
    return json.loads(text)


@lru_cache(maxsize=1)
def _load_rules_json() -> dict:
    return _read_rules_json()


def clear_rules_cache() -> None:
    """Make subsequent rule reads observe the latest on-disk configuration."""
    _load_rules_json.cache_clear()
    get_bucket_rules.cache_clear()
    get_sector_rules.cache_clear()
    get_exclusion_rules.cache_clear()
    get_cleanup_rules.cache_clear()


def get_editable_rules() -> dict[str, Any]:
    """Return a defensive copy of the selection rules exposed by the web UI."""
    rules = _read_rules_json()
    return copy.deepcopy(
        {
            "bucket_rules": rules.get("bucket_rules", []),
            "sector_rules": rules.get("sector_rules", []),
            "exclusion_rules": rules.get("exclusion_rules", []),
        }
    )


def save_editable_rules(rules: dict[str, Any]) -> None:
    """Atomically replace editable rules while preserving internal cleanup rules."""
    with _rules_write_lock:
        current = copy.deepcopy(_read_rules_json())
        for key in ("bucket_rules", "sector_rules", "exclusion_rules"):
            current[key] = copy.deepcopy(rules[key])

        RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=RULES_FILE.parent,
                delete=False,
                newline="\n",
            ) as temporary:
                json.dump(current, temporary, ensure_ascii=False, indent=2)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, RULES_FILE)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
    clear_rules_cache()

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
