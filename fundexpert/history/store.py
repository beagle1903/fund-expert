"""Persist portfolio run records for drift tracking."""

import json
from pathlib import Path
from typing import Any

import pandas as pd


def save_run(
    selected: pd.DataFrame,
    header: dict[str, Any],
    history_dir: Path,
) -> Path:
    """Save the current run to <history_dir>/YYYY-MM-DD_HH-MM-SS_<universe>.json.

    Returns the path written. May raise on serialization or disk errors; caller should wrap in try/except.
    """
    history_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    ts = header["timestamp"]
    filename = f"{ts.strftime('%Y-%m-%d_%H-%M-%S')}_{header['universe']}.json"
    record: dict[str, Any] = {
        "timestamp": ts.isoformat(),
        "universe": header["universe"],
        "risk_level": header["risk_level"],
        "horizon": header["horizon"],
        "volume_priority": header["volume_priority"],
        "fee_priority": header["fee_priority"],
        "n": header["n"],
        "picks": [
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
        ],
    }
    path = history_dir / filename
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=history_dir, delete=False) as tmp:
        tmp.write(json.dumps(record, ensure_ascii=False, indent=2))
        tmp_name = tmp.name
    os.chmod(tmp_name, 0o600)
    os.replace(tmp_name, path)
    
    import shutil
    latest_path = history_dir / f"latest_{header['universe']}.json"
    try:
        shutil.copy2(path, latest_path)
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
