"""Render the selected portfolio as a rich table on stdout."""

from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table

from fundexpert.config import NEGATIVE_NEWS_PENALTY


def render_portfolio(
    selected: pd.DataFrame,
    header: dict[str, Any],
    news: dict[str, list[dict[str, Any]]] | None,
    news_meta: dict[str, Any] | None = None,
) -> None:
    """Print header block + table + (optional) news footer to stdout.

    `news` maps fon_kodu → list of {title, url, source, published?}. If empty
    or None, the news footer is omitted.

    `news_meta` carries info about the news pass (enabled flag, top-K size,
    total hits, displaced funds). When None, news-pass-specific output (header
    line, row markers, displaced footer) is suppressed — used by the
    programmatic snippet that doesn't compute news_meta.
    """
    console = Console()

    ts = header["timestamp"].strftime("%Y-%m-%d %H:%M")
    console.print(f"[bold]Fund Expert — {ts}[/bold]")
    console.print(
        f"Evren: {header['universe']} ({header['candidate_total']} fon)  •  "
        f"Vade: {header['horizon']}  •  Risk sev.: {header['risk_level']}"
    )
    console.print(
        f"Hacim önc.: {header['volume_priority']}  •  "
        f"Ücret önc.: {header['fee_priority']}  •  N={header['n']}"
    )
    console.print(
        f"Aday havuzu: {header['candidate_total']} → {header['candidate_kept']} "
        f"(NaN filtreleri sonrası)"
    )

    if news_meta and news_meta.get("enabled"):
        if not news_meta.get("key_present"):
            console.print("Haber taraması: atlandı (TAVILY_API_KEY tanımsız)")
        else:
            parts = [
                "Haber taraması: aktif",
                f"top-K={news_meta['top_k']}",
                f"{news_meta['total_hits']} fonda olumsuz haber",
            ]
            displaced_count = len(news_meta.get("displaced", []))
            if news_meta["total_hits"] > 0:
                if displaced_count == 0:
                    parts.append("portföy değişmedi")
                else:
                    parts.append(f"{displaced_count} pick değişti")
            console.print("  •  ".join(parts), soft_wrap=True)

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

    show_news_marker = bool(news_meta and news_meta.get("enabled") and news)
    for _, r in selected.iterrows():
        is_penalized = show_news_marker and str(r["fon_kodu"]) in (news or {})
        fon_kodu_cell = f"{r['fon_kodu']} 📰" if is_penalized else str(r["fon_kodu"])
        score_cell = (
            f"{r['score']:.2f} (−{NEGATIVE_NEWS_PENALTY:.2f})"
            if is_penalized
            else f"{r['score']:.2f}"
        )
        row = [
            fon_kodu_cell,
            str(r["fon_adi"]),
            str(r["umbrella_type"]),
        ]
        if show_sector:
            row.append(str(r["sector"]))
        row.extend([
            str(int(r["risk"])),
            f"{int(r['display_weight_pct'])}",
            score_cell,
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
        console.print(
            "\n[bold red]📰 Olumsuz haberle penalize edilen fonlar "
            "(portföyde kaldı):[/bold red]"
        )
        for code, items in news.items():
            for item in items:
                published = f", {item['published']:%Y-%m-%d}" if item.get("published") else ""
                console.print(f"  {code} — \"{item['title']}\"  ({item['source']}{published})")
                console.print(f"        {item['url']}")

    if news_meta and news_meta.get("displaced"):
        console.print(
            "\n[bold red]⛔ Habere takılıp portföyden düşen fonlar:[/bold red]"
        )
        for entry in news_meta["displaced"]:
            console.print(
                f"  {entry['fon_kodu']} — habersiz skor {entry['score_pre']:.2f} "
                f"→ penalize edince {entry['score_post']:.2f}"
            )
            for hit in entry["hits"]:
                published = f", {hit['published']:%Y-%m-%d}" if hit.get("published") else ""
                console.print(f"        ↳ \"{hit['title']}\"  ({hit['source']}{published})")
                console.print(f"        ↳ {hit['url']}")
