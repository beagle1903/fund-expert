"""Render the selected portfolio as a rich table on stdout."""

from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table


def render_portfolio(
    selected: pd.DataFrame,
    header: dict[str, Any],
    news: dict[str, list[dict[str, Any]]] | None,
) -> None:
    """Print header block + table + (optional) news footer to stdout.

    `news` maps fon_kodu → list of {title, url, source, published?}. If empty
    or None, the news footer is omitted.
    """
    console = Console()

    ts = header["timestamp"].strftime("%Y-%m-%d %H:%M")
    console.print(f"[bold]Fund Expert — {ts}[/bold]")
    console.print(
        f"Evren: {header['universe']} ({header['candidate_total']} fon)  •  "
        f"Vade: {header['horizon']}  •  Risk önc.: {header['risk_priority']}"
    )
    console.print(
        f"Hacim önc.: {header['volume_priority']}  •  "
        f"Ücret önc.: {header['fee_priority']}  •  N={header['n']}"
    )
    console.print(
        f"Aday havuzu: {header['candidate_total']} → {header['candidate_kept']} "
        f"(NaN filtreleri sonrası)"
    )

    show_sector = (
        "sector" in selected.columns
        and (selected["sector"] != "diversified").any()
    )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Fon Kodu")
    table.add_column("Fon Adı")
    table.add_column("Şemsiye")
    if show_sector:
        table.add_column("Sektör")
    table.add_column("Risk", justify="right")
    table.add_column("Ağırlık %", justify="right")
    table.add_column("Skor", justify="right")

    for _, r in selected.iterrows():
        row = [
            str(r["fon_kodu"]),
            str(r["fon_adi"]),
            str(r["umbrella_type"]),
        ]
        if show_sector:
            row.append(str(r["sector"]))
        row.extend([
            str(int(r["risk"])),
            f"{int(r['display_weight_pct'])}",
            f"{r['score']:.2f}",
        ])
        table.add_row(*row)
    total_weight = selected["display_weight_pct"].sum() if len(selected) else 0.0
    footer = ["", "", ""]
    if show_sector:
        footer.append("")
    footer.extend(["[bold]Toplam[/bold]", f"[bold]{int(total_weight)}[/bold]", ""])
    table.add_row(*footer)
    console.print(table)

    if news:
        console.print("\n[bold]Haberler:[/bold]")
        for code, items in news.items():
            for item in items:
                published = f", {item['published']:%Y-%m-%d}" if item.get("published") else ""
                console.print(f"  {code} — \"{item['title']}\"  ({item['source']}{published})")
                console.print(f"        {item['url']}")
