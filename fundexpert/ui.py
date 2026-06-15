import json
import os
import sys
from typing import Any

from fundexpert.config import LAST_RUN_FILE

UNIVERSE_CHOICES = ["tefas", "befas", "both"]
PRIORITY_CHOICES = ["low", "medium", "high"]
HORIZON_CHOICES = ["short", "medium", "long"]


def load_last_run_state() -> dict[str, Any]:
    if not LAST_RUN_FILE.exists():
        return {}
    try:
        return json.loads(LAST_RUN_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_last_run_state(answers: dict[str, Any]) -> None:
    import tempfile
    try:
        LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=LAST_RUN_FILE.parent, delete=False) as tmp:
            tmp.write(json.dumps(answers, ensure_ascii=False))
            tmp_name = tmp.name
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, LAST_RUN_FILE)
    except OSError:
        pass  # quality-of-life only — never fail the run on cache write errors


def prompt_user(last: dict[str, Any]) -> dict[str, Any] | None:
    """Run interactive prompts. Returns None if the user cancelled (Ctrl+C / Esc)."""
    import questionary

    universe = questionary.select(
        "Fon evreni:", choices=UNIVERSE_CHOICES,
        default=last.get("universe", "tefas"),
    ).ask()
    if universe is None:
        return None

    risk_level = questionary.select(
        "Risk seviyesi (yüksek = yüksek risk tolere edilir):",
        choices=PRIORITY_CHOICES, default=last.get("risk_level", "medium"),
    ).ask()
    if risk_level is None:
        return None

    horizon = questionary.select(
        "Yatırım vadesi:",
        choices=HORIZON_CHOICES, default=last.get("horizon", "medium"),
    ).ask()
    if horizon is None:
        return None

    volume_priority = questionary.select(
        "Hacim değişimi önceliği:",
        choices=PRIORITY_CHOICES, default=last.get("volume_priority", "medium"),
    ).ask()
    if volume_priority is None:
        return None

    fee_priority = questionary.select(
        "Yönetim ücreti önceliği:",
        choices=PRIORITY_CHOICES, default=last.get("fee_priority", "medium"),
    ).ask()
    if fee_priority is None:
        return None

    momentum_priority = questionary.select(
        "Fon akışı (momentum) önceliği:",
        choices=PRIORITY_CHOICES, default=last.get("momentum_priority", "medium"),
    ).ask()
    if momentum_priority is None:
        return None

    n_raw = questionary.text(
        "Kaç fon istiyorsun (1-20)?",
        default=str(last.get("n", 5)),
        validate=lambda v: v.isdigit() and 1 <= int(v) <= 20,
    ).ask()
    if n_raw is None:
        return None

    return {
        "universe": universe,
        "risk_level": risk_level,
        "horizon": horizon,
        "volume_priority": volume_priority,
        "fee_priority": fee_priority,
        "momentum_priority": momentum_priority,
        "n": int(n_raw),
    }


def ensure_utf8_stdio() -> None:
    """Force UTF-8 on stdout/stderr so Turkish characters render on any terminal."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass
