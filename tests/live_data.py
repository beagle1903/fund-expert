from pathlib import Path

import pytest

from fundexpert.config import DATA_ROOT

LIVE_BUNDLE_FILES = ("getiri.csv", "buyukluk.csv", "yonetim ucreti.csv")


def live_bundle_present(universe: str) -> bool:
    root = Path(DATA_ROOT) / universe
    return all((root / name).is_file() for name in LIVE_BUNDLE_FILES)


LIVE_DATA_AVAILABLE = live_bundle_present("tefas") and live_bundle_present("befas")

requires_live_data = pytest.mark.skipif(
    not LIVE_DATA_AVAILABLE,
    reason="Live TEFAS/BEFAS CSVs are not in this checkout",
)
