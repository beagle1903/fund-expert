"""Render portfolio drift between the current run and a previously saved run."""

from datetime import datetime
from typing import Any

import pandas as pd
from rich.console import Console


def render_diff(
    selected: pd.DataFrame,
    previous: dict[str, Any],
    console: Console | None = None,
) -> None:
    """Print a drift summary comparing *selected* against a *previous* run record.

    *previous* is the dict returned by `history.store.load_last_run`.
    *console* is injectable for tests; defaults to stdout Console.
    """
    if console is None:
        console = Console()

    prev_ts = datetime.fromisoformat(previous["timestamp"])
    console.print(
        f"\n[bold]Önceki run ile karşılaştırma[/bold] "
        f"({prev_ts.strftime('%Y-%m-%d %H:%M')})"
    )

    prev_by_code: dict[str, dict] = {p["fon_kodu"]: p for p in previous["picks"]}
    curr_picks = [
        {
            "fon_kodu": str(r["fon_kodu"]),
            "fon_adi": str(r["fon_adi"]),
            "weight_pct": int(r["display_weight_pct"]),
            "score": float(r["score"]),
        }
        for _, r in selected.iterrows()
    ]
    curr_by_code: dict[str, dict] = {p["fon_kodu"]: p for p in curr_picks}

    entered = [p for code, p in curr_by_code.items() if code not in prev_by_code]
    dropped = [p for code, p in prev_by_code.items() if code not in curr_by_code]
    persisting = [
        (prev_by_code[code], p)
        for code, p in curr_by_code.items()
        if code in prev_by_code
    ]
    changed = [
        (prev, curr)
        for prev, curr in persisting
        if prev["weight_pct"] != curr["weight_pct"]
        or abs(prev["score"] - curr["score"]) >= 0.005
    ]

    if not entered and not dropped and not changed:
        console.print("  Değişiklik yok — portföy aynı kaldı.")
        return

    if entered:
        console.print("  [green]+ Portföye girenler:[/green]")
        for p in entered:
            console.print(
                f"    {p['fon_kodu']}  {p['fon_adi']}  "
                f"ağırlık={p['weight_pct']}%  skor={p['score']:.2f}"
            )

    if dropped:
        console.print("  [red]− Portföyden çıkanlar:[/red]")
        for p in dropped:
            console.print(
                f"    {p['fon_kodu']}  {p['fon_adi']}  "
                f"ağırlık={p['weight_pct']}%  skor={p['score']:.2f}"
            )

    if changed:
        console.print("  [yellow]~ Değişen ağırlık / skor:[/yellow]")
        for prev, curr in changed:
            weight_str = (
                f"ağırlık {prev['weight_pct']}→{curr['weight_pct']}%"
                if prev["weight_pct"] != curr["weight_pct"]
                else f"ağırlık {curr['weight_pct']}%"
            )
            score_diff = curr["score"] - prev["score"]
            sign = "+" if score_diff >= 0 else ""
            console.print(
                f"    {curr['fon_kodu']}  {weight_str}  "
                f"skor {prev['score']:.2f}→{curr['score']:.2f} ({sign}{score_diff:.2f})"
            )
