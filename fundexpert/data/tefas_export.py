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

from fundexpert.data.loader import OPEN_CODES_FILENAME


TEFAS_EXPORT_URL = "https://www.tefas.gov.tr/api/fund-returns/export"
FUND_TYPE_BY_UNIVERSE = {"tefas": "YAT", "befas": "EMK"}
# Measured 2026-11-02: işlem gören / aligned Tümü is 1071 / 2099 for TEFAS and
# 311 / 400 for BEFAS. The Tümü floors sit between them, so a server that ignores
# islem null fails closed.
MIN_ROWS_BY_UNIVERSE = {"tefas": 1500, "befas": 350}
MIN_OPEN_ROWS_BY_UNIVERSE = {"tefas": 500, "befas": 250}
# Measured 2026-11-02: 38 TEFAS and 2 BEFAS codes, all closed funds. TEFAS closed
# funds often have no fee row, and clean_candidates would drop them anyway.
MAX_IGNORED_CODE_SET_DIFFERENCES = {"tefas": 60, "befas": 5}
MAX_IGNORED_OPEN_CODE_DIFFERENCES = 5


@dataclass(frozen=True)
class ExportDefinition:
    filename: str
    listing_type: str
    columns: tuple[tuple[str, str], ...]
    # null is Fon Getirileri İşlem Durumu = Tümü; 1 is işlem gören.
    islem: int | None = None


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

OPEN_CODES_EXPORT = ExportDefinition(
    filename=OPEN_CODES_FILENAME,
    listing_type="return",
    columns=(("fonKodu", "Fon Kodu"),),
    islem=1,
)

ResponseOpener = Callable[..., Any]


class WebExportError(RuntimeError):
    """Raised when TEFAS's web-export transport returns unusable data."""


def _one_month_before(value: date) -> date:
    year = value.year if value.month > 1 else value.year - 1
    month = value.month - 1 if value.month > 1 else 12
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _filters_for(
    definition: ExportDefinition,
    acquired_at: datetime,
) -> dict[str, Any]:
    filters: dict[str, Any] = {
        "kurucuKodu": None,
        "fonTurKod": None,
        "fonGrubu": None,
        "fonTurAciklama": None,
        "sfonTurKod": None,
        "islem": definition.islem,
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


def _align_code_sets(
    datasets: list[tuple[ExportDefinition, list[dict[str, Any]]]],
    *,
    universe: str,
    maximum_tolerated: int,
) -> list[tuple[ExportDefinition, list[dict[str, Any]]]]:
    """Drop a bounded number of codes not shared by every export view."""
    code_sets = [
        {str(row.get("fonKodu", "")) for row in rows}
        for _, rows in datasets
    ]
    common_codes = set.intersection(*code_sets)
    mismatched_codes = set.union(*code_sets) - common_codes
    if len(mismatched_codes) > maximum_tolerated:
        sample = ", ".join(sorted(mismatched_codes)[:6])
        raise WebExportError(
            f"{universe.upper()} fund-code coverage differs by "
            f"{len(mismatched_codes)} codes across exports; maximum tolerated "
            f"is {maximum_tolerated}. Codes: {sample}."
        )
    if not mismatched_codes:
        return datasets
    return [
        (
            definition,
            [
                row
                for row in rows
                if str(row.get("fonKodu", "")) in common_codes
            ],
        )
        for definition, rows in datasets
    ]


def _align_open_rows(
    open_rows: list[dict[str, Any]],
    aligned_codes: set[str],
    *,
    universe: str,
) -> list[dict[str, Any]]:
    """Keep open codes that survived alignment, failing closed on any drift."""
    minimum = MIN_OPEN_ROWS_BY_UNIVERSE[universe]
    if len(open_rows) < minimum:
        raise WebExportError(
            f"TEFAS returned only {len(open_rows)} open {universe.upper()} rows; "
            f"expected at least {minimum}."
        )
    kept = [row for row in open_rows if str(row.get("fonKodu", "")) in aligned_codes]
    missing = len(open_rows) - len(kept)
    if missing > MAX_IGNORED_OPEN_CODE_DIFFERENCES:
        raise WebExportError(
            f"{missing} open {universe.upper()} fund codes are missing from the "
            f"aligned exports; maximum tolerated is "
            f"{MAX_IGNORED_OPEN_CODE_DIFFERENCES}."
        )
    # Equal counts mean the server ignored islem 1, so nothing marks a closed fund.
    if len(kept) >= len(aligned_codes):
        raise WebExportError(
            f"TEFAS returned every {universe.upper()} fund as open; "
            "the transaction filter was not applied."
        )
    return kept


def _is_missing_risk_sentinel(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, str):
        value = value.strip()
        if value == "-":
            return True
    try:
        return float(value) == 0
    except (TypeError, ValueError):
        return False


def _blank_closed_fund_risk(
    rows: list[dict[str, Any]],
    open_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Blank the "-" and 0 risk some closed funds report; scoring treats blank as 7.

    Open funds and any other value stay as sent, so validation can still reject them.
    """
    open_codes = {str(row.get("fonKodu", "")) for row in open_rows}
    return [
        {**row, "riskDegeri": None}
        if str(row.get("fonKodu", "")) not in open_codes
        and _is_missing_risk_sentinel(row.get("riskDegeri"))
        else row
        for row in rows
    ]


def download_web_export_bundle(
    universe: str,
    staged_dir: Path,
    *,
    now: datetime | None = None,
    opener: ResponseOpener = urlopen,
    timeout_seconds: float = 30,
) -> None:
    """Acquire exactly four web exports and render the canonical CSV bundle."""
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
    open_rows = _request_rows(
        fund_type,
        OPEN_CODES_EXPORT,
        acquired_at,
        opener=opener,
        timeout_seconds=timeout_seconds,
    )

    datasets = _align_code_sets(
        datasets,
        universe=universe,
        maximum_tolerated=MAX_IGNORED_CODE_SET_DIFFERENCES[universe],
    )
    minimum = MIN_ROWS_BY_UNIVERSE[universe]
    for definition, rows in datasets:
        if len(rows) < minimum:
            raise WebExportError(
                f"TEFAS returned only {len(rows)} aligned {universe.upper()} "
                f"rows for {definition.listing_type}; expected at least {minimum}."
            )
    aligned_codes = {str(row.get("fonKodu", "")) for row in datasets[0][1]}
    open_rows = _align_open_rows(open_rows, aligned_codes, universe=universe)

    datasets = [
        (
            definition,
            _blank_closed_fund_risk(rows, open_rows)
            if definition.listing_type == "return"
            else rows,
        )
        for definition, rows in datasets
    ]

    for definition, rows in [*datasets, (OPEN_CODES_EXPORT, open_rows)]:
        _write_csv(
            staged_dir / definition.filename,
            definition,
            rows,
            acquired_at,
        )
