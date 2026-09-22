"""Persist portfolio run records for drift tracking."""

import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

_save_locks_guard = threading.Lock()
_save_locks: dict[tuple[str, str], threading.Lock] = {}


def _save_lock(history_dir: Path, universe: str) -> threading.Lock:
    key = (str(history_dir), universe)
    with _save_locks_guard:
        lock = _save_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _save_locks[key] = lock
        return lock


def _archive_path(history_dir: Path, ts: datetime, universe: str) -> Path:
    stem = ts.strftime("%Y-%m-%d_%H-%M-%S-%f")
    path = history_dir / f"{stem}_{universe}.json"
    duplicate = 2
    while path.exists():
        path = history_dir / f"{stem}_{duplicate}_{universe}.json"
        duplicate += 1
    return path


def _existing_latest_is_newer(latest_path: Path, ts: datetime) -> bool:
    if not latest_path.exists():
        return False
    try:
        existing = json.loads(latest_path.read_text(encoding="utf-8"))
        existing_ts = datetime.fromisoformat(existing["timestamp"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return False
    return existing_ts > ts


def save_run(
    selected: pd.DataFrame,
    header: dict[str, Any],
    history_dir: Path,
) -> Path:
    """Save the current run to <history_dir>/YYYY-MM-DD_HH-MM-SS-ffffff_<universe>.json.

    Returns the path written. May raise on serialization or disk errors; caller should wrap in try/except.
    A slower save with an older timestamp does not replace latest_<universe>.json.
    """
    history_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    ts = header["timestamp"]
    universe = header["universe"]
    with _save_lock(history_dir, universe):
        return _write_run(selected, header, history_dir, ts, universe)


def _write_run(
    selected: pd.DataFrame,
    header: dict[str, Any],
    history_dir: Path,
    ts: datetime,
    universe: str,
) -> Path:
    record: dict[str, Any] = {
        "timestamp": ts.isoformat(),
        "universe": header["universe"],
        "risk_level": header["risk_level"],
        "horizon": header["horizon"],
        "volume_priority": header["volume_priority"],
        "fee_priority": header["fee_priority"],
        "n": header["n"],
    }
    for key in (
        "founder",
        "momentum_priority",
        "max_per_type",
        "max_per_sector",
        "data_snapshot",
    ):
        if key in header:
            record[key] = header[key]
    record["picks"] = [
        {
            "fon_kodu": str(r["fon_kodu"]),
            "fon_adi": str(r["fon_adi"]),
            "score": float(r["score"]),
            "weight_pct": int(r["display_weight_pct"]),
            "risk": int(r["risk"]) if pd.notna(r["risk"]) else None,
            "strategy": str(r.get("strategy", "")),
            "sector": str(r.get("sector", "")),
        }
        for _, r in selected.iterrows()
    ]
    path = _archive_path(history_dir, ts, universe)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=history_dir, delete=False) as tmp:
        tmp.write(json.dumps(record, ensure_ascii=False, indent=2))
        tmp_name = tmp.name
    os.chmod(tmp_name, 0o600)
    os.replace(tmp_name, path)

    latest_path = history_dir / f"latest_{universe}.json"
    if not _existing_latest_is_newer(latest_path, ts):
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=history_dir, delete=False) as tmp:
                tmp.write(json.dumps(record, ensure_ascii=False, indent=2))
                tmp_name = tmp.name
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, latest_path)
        except OSError:
            pass

    return path


def load_last_run(universe: str, history_dir: Path) -> dict[str, Any] | None:
    """Return the most recent saved run record for *universe*, or None."""
    if not history_dir.exists():
        return None

    latest_path = history_dir / f"latest_{universe}.json"
    if latest_path.exists():
        try:
            return json.loads(latest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Fallback to globbing
    candidates = [p for p in history_dir.glob(f"*_{universe}.json") if not p.name.startswith("latest_")]
    candidates.sort(reverse=True)
    if not candidates:
        return None
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
