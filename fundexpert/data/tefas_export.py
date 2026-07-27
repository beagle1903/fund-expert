"""Acquire TEFAS/BEFAS datasets through TEFAS's web-export transport."""

from __future__ import annotations

import calendar
import csv
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TEFAS_EXPORT_URL = "https://www.tefas.gov.tr/api/fund-returns/export"
FUND_TYPE_BY_UNIVERSE = {"tefas": "YAT", "befas": "EMK"}
MIN_ROWS_BY_UNIVERSE = {"tefas": 500, "befas": 100}


@dataclass(frozen=True)
class ExportDefinition:
    filename: str
    listing_type: str
    columns: tuple[tuple[str, str], ...]


EXPORTS = (
    ExportDefinition(
        filename="getiri.csv",
        listing_type="return",
        columns=(
            ("fonKodu", "Fon Kodu"),
            ("fonUnvan", "Fon Adı"),
            ("fonTurAciklama", "Şemsiye Fon Türü"),
            ("riskDegeri", "Fonun Risk Değeri"),
            ("getiri1a", "1 Ay (%)"),
            ("getiri3a", "3 Ay (%)"),
            ("getiri6a", "6 Ay (%)"),
            ("getiriyb", "Yılbaşından İtibaren (%)"),
            ("getiri1y", "1 Yıl (%)"),
            ("getiri3y", "3 Yıl (%)"),
            ("getiri5y", "5 Yıl (%)"),
        ),
    ),
    ExportDefinition(
        filename="yonetim ucreti.csv",
        listing_type="management",
        columns=(
            ("fonKodu", "Fon Kodu"),
            ("fonUnvan", "Fon Adı"),
            ("fonTurAciklama", "Şemsiye Fon Türü"),
            ("uygulananYu1Y", "Uygulanan Yönetim Ücreti Yıllık (%)"),
            (
                "fonIcTuzukYu1G",
                "Fon İç Tüzüğünde Yer Alan Yönetim Ücreti Yıllık (%)",
            ),
            ("yillikGetiri", "Yıllık Getiri Oranı (%)"),
            ("fonTopGiderKesoran", "Yıllık Azami Fon Toplam Gider Oranı (%)"),
        ),
    ),
    ExportDefinition(
        filename="buyukluk.csv",
        listing_type="size",
        columns=(
            ("fonKodu", "Fon Kodu"),
            ("fonUnvan", "Fon Adı"),
            ("fonTurAciklama", "Şemsiye Fon Türü"),
            ("ilkPortfoyDegeri", "İlk Portföy Büyüklüğü"),
            ("sonPortfoyDegeri", "Son Portföy Büyüklüğü"),
            ("portBuyuklukDegisim", "Portföy Büyüklüğü Değişimi (%)"),
            ("ilkPayAdedi", "Tedavüldeki İlk Pay Adedi"),
            ("sonPayAdedi", "Tedavüldeki Son Pay Adedi"),
            ("payAdetDegisim", "Pay Adedi Değişimi (%)"),
            ("netGetiriOrani", "Getiri Oranı (%)"),
        ),
    ),
)

ResponseOpener = Callable[..., Any]


class WebExportError(RuntimeError):
    """Raised when TEFAS's web-export transport returns unusable data."""


def _one_month_before(value: date) -> date:
    year = value.year if value.month > 1 else value.year - 1
    month = value.month - 1 if value.month > 1 else 12
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _filters_for(definition: ExportDefinition, acquired_at: datetime) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "kurucuKodu": None,
        "fonTurKod": None,
        "fonGrubu": None,
        "fonTurAciklama": None,
        "sfonTurKod": None,
        "islem": 1,
        "calismaTipi": 2,
    }
    if definition.listing_type == "return":
        filters.update(
            {
                "donemGetiri1a": "1",
                "donemGetiri3a": "1",
                "donemGetiri6a": "1",
                "donemGetiriyb": "1",
                "donemGetiri1y": "1",
                "donemGetiri3y": "1",
                "donemGetiri5y": "1",
                "getiriOrani": "1",
            }
        )
    elif definition.listing_type == "size":
        end = acquired_at.date()
        filters.update(
            {
                "calismaTipi": 1,
                "basTarih": _one_month_before(end).isoformat(),
                "bitTarih": end.isoformat(),
            }
        )
    return filters


def _request_rows(
    fund_type: str,
    definition: ExportDefinition,
    acquired_at: datetime,
    *,
    opener: ResponseOpener,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    payload = {
        "format": "json",
        "listingType": definition.listing_type,
        "fundType": fund_type,
        "locale": "tr",
        "filters": _filters_for(definition, acquired_at),
        "columns": [key for key, _ in definition.columns],
    }
    request = Request(
        TEFAS_EXPORT_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "fundexpert/0.1 local-data-refresh",
        },
        method="POST",
    )
    try:
        with opener(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except HTTPError as exc:
        raise WebExportError(
            f"TEFAS web export returned HTTP {exc.code} for "
            f"{definition.listing_type}."
        ) from exc
    except (OSError, URLError) as exc:
        raise WebExportError(
            f"TEFAS web export could not be reached for {definition.listing_type}."
        ) from exc

    try:
        parsed = json.loads(raw.decode("utf-8"), parse_float=Decimal)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise WebExportError(
            f"TEFAS returned invalid JSON for {definition.listing_type}."
        ) from exc
    if not isinstance(parsed, list) or not all(isinstance(row, dict) for row in parsed):
        raise WebExportError(
            f"TEFAS returned an unexpected response for {definition.listing_type}."
        )
    return parsed


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return format(value, "f").replace(".", ",")
    if isinstance(value, float):
        return format(value, ".15g").replace(".", ",")
    return str(value)


def _write_csv(
    path: Path,
    definition: ExportDefinition,
    rows: list[dict[str, Any]],
    acquired_at: datetime,
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\r\n")
        writer.writerow(["Dışa Aktarım Tarihi:", acquired_at.strftime("%d.%m.%Y %H:%M:%S")])
        writer.writerow(["Toplam Kayıt Sayısı:", len(rows)])
        writer.writerow([])
        writer.writerow([header for _, header in definition.columns])
        for row in rows:
            writer.writerow(
                [_format_value(row.get(key)) for key, _ in definition.columns]
            )


def download_web_export_bundle(
    universe: str,
    staged_dir: Path,
    *,
    now: datetime | None = None,
    opener: ResponseOpener = urlopen,
    timeout_seconds: float = 30,
) -> None:
    """Acquire exactly three web exports and render the canonical CSV bundle."""
    fund_type = FUND_TYPE_BY_UNIVERSE.get(universe)
    if fund_type is None:
        raise ValueError(f"Unsupported universe: {universe!r}.")
    acquired_at = now or datetime.now()
    staged_dir = Path(staged_dir)
    staged_dir.mkdir(parents=True, exist_ok=True)

    datasets: list[tuple[ExportDefinition, list[dict[str, Any]]]] = []
    for definition in EXPORTS:
        rows = _request_rows(
            fund_type,
            definition,
            acquired_at,
            opener=opener,
            timeout_seconds=timeout_seconds,
        )
        minimum = MIN_ROWS_BY_UNIVERSE[universe]
        if len(rows) < minimum:
            raise WebExportError(
                f"TEFAS returned only {len(rows)} {universe.upper()} rows for "
                f"{definition.listing_type}; expected at least {minimum}."
            )
        datasets.append((definition, rows))

    reference_codes = {str(row.get("fonKodu", "")) for row in datasets[0][1]}
    for definition, rows in datasets[1:]:
        codes = {str(row.get("fonKodu", "")) for row in rows}
        if codes != reference_codes:
            raise WebExportError(
                f"TEFAS {definition.listing_type} fund-code coverage does not "
                "match the return export."
            )

    for definition, rows in datasets:
        _write_csv(
            staged_dir / definition.filename,
            definition,
            rows,
            acquired_at,
        )
