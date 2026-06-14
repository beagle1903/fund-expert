"""Read TEFAS/BEFAS CSV exports and rename columns to internal snake_case names."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from fundexpert.config import MAX_CSV_SIZE_BYTES

GETIRI_RENAME: dict[str, str] = {
    "Fon Kodu": "fon_kodu",
    "Fon Adı": "fon_adi",
    "Şemsiye Fon Türü": "umbrella_type",
    "Fonun Risk Değeri": "risk",
    "1 Ay (%)": "ret_1m",
    "3 Ay (%)": "ret_3m",
    "6 Ay (%)": "ret_6m",
    "Yılbaşından İtibaren (%)": "ret_ytd",
    "1 Yıl (%)": "ret_1y",
    "3 Yıl (%)": "ret_3y",
    "5 Yıl (%)": "ret_5y",
}

BUYUKLUK_RENAME: dict[str, str] = {
    "Fon Kodu": "fon_kodu",
    "Fon Adı": "fon_adi",
    "Şemsiye Fon Türü": "umbrella_type",
    "İlk Portföy Büyüklüğü": "aum_first",
    "Son Portföy Büyüklüğü": "aum_last",
    "Portföy Büyüklüğü Değişimi (%)": "aum_change_pct",
    "Tedavüldeki İlk Pay Adedi": "units_first",
    "Tedavüldeki Son Pay Adedi": "units_last",
    "Pay Adedi Değişimi (%)": "units_change_pct",
    # "Getiri Oranı (%)" intentionally dropped — redundant with getiri.csv
}

YONETIM_RENAME: dict[str, str] = {
    "Fon Kodu": "fon_kodu",
    "Fon Adı": "fon_adi",
    "Şemsiye Fon Türü": "umbrella_type",
    "Uygulanan Yönetim Ücreti Yıllık (%)": "applied_management_fee_pct",
    "Fon İç Tüzüğünde Yer Alan Yönetim Ücreti Yıllık (%)": "bylaw_management_fee_pct",
    # "Yıllık Getiri Oranı (%)" intentionally dropped — redundant with getiri.csv
}

@dataclass
class UniverseData:
    getiri: pd.DataFrame
    buyukluk: pd.DataFrame
    yonetim_ucreti: pd.DataFrame


def _read_one(path: Path, rename: dict[str, str]) -> pd.DataFrame:
    if path.stat().st_size > MAX_CSV_SIZE_BYTES:
        raise ValueError(f"File {path.name} exceeds size limit of {MAX_CSV_SIZE_BYTES} bytes.")
    df = pd.read_csv(
        path,
        skiprows=3,        # rows 0-2: export metadata; row 3: header
        encoding="utf-8",
        decimal=",",
        usecols=list(rename.keys()),
        dtype={"Fon Kodu": str, "Fon Adı": str, "Şemsiye Fon Türü": str},
    )
    return df.rename(columns=rename)


def load_universe(
    getiri_path: Path,
    buyukluk_path: Path,
    yonetim_path: Path,
) -> UniverseData:
    """Load the three CSVs for a single universe (tefas or befas)."""
    return UniverseData(
        getiri=_read_one(getiri_path,  GETIRI_RENAME),
        buyukluk=_read_one(buyukluk_path, BUYUKLUK_RENAME),
        yonetim_ucreti=_read_one(yonetim_path,  YONETIM_RENAME),
    )

def load_candidates_for_universe(universe: str, data_root: Path) -> pd.DataFrame:
    """Helper to load and merge a single universe (tefas or befas) into a candidate frame."""
    from fundexpert.data.merge import merge_universe
    folder = data_root / universe
    frames = load_universe(
        getiri_path=folder / "getiri.csv",
        buyukluk_path=folder / "buyukluk.csv",
        yonetim_path=folder / "yonetim ucreti.csv",
    )
    return merge_universe(frames, universe=universe)
