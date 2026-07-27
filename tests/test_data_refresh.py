import shutil
from datetime import datetime
from pathlib import Path

import pytest

from fundexpert.data.bundle import publish_bundle, resolve_active_bundle
from fundexpert.data.refresh import (
    DataRefreshBusyError,
    DataRefreshError,
    refresh_universe,
)
from fundexpert.data.tefas_export import WebExportError


SOURCE_NAMES = {
    "getiri.csv": "getiri_small.csv",
    "buyukluk.csv": "buyukluk_small.csv",
    "yonetim ucreti.csv": "yonetim_small.csv",
}


def _copy_bundle(fixtures_dir: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for target, source in SOURCE_NAMES.items():
        shutil.copy2(fixtures_dir / source, destination / target)


def test_refresh_skips_download_when_active_bundle_is_fresh(fixtures_dir, tmp_path):
    data_root = tmp_path / "data"
    _copy_bundle(fixtures_dir, data_root / "tefas")
    calls = []

    result = refresh_universe(
        "tefas",
        data_root,
        now=datetime(2026, 5, 2, 18, 0),
        downloader=lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert result.refreshed is False
    assert result.manifest.source == "legacy"
    assert calls == []


def test_refresh_downloads_validates_and_publishes_stale_bundle(fixtures_dir, tmp_path):
    data_root = tmp_path / "data"
    _copy_bundle(fixtures_dir, data_root / "tefas")

    def downloader(universe, staged_dir, *, now):
        assert universe == "tefas"
        assert now == datetime(2026, 7, 27, 16, 0)
        _copy_bundle(fixtures_dir, staged_dir)

    result = refresh_universe(
        "tefas",
        data_root,
        now=datetime(2026, 7, 27, 16, 0),
        downloader=downloader,
    )
    active = resolve_active_bundle("tefas", data_root)

    assert result.refreshed is True
    assert result.manifest.source == "tefas-web-export"
    assert active.manifest.bundle_id == result.manifest.bundle_id
    assert active.manifest.imported_at == datetime(2026, 7, 27, 16, 0)


def test_force_refreshes_even_when_bundle_is_fresh(fixtures_dir, tmp_path):
    data_root = tmp_path / "data"
    _copy_bundle(fixtures_dir, data_root / "tefas")
    calls = []

    def downloader(universe, staged_dir, *, now):
        calls.append(universe)
        _copy_bundle(fixtures_dir, staged_dir)

    result = refresh_universe(
        "tefas",
        data_root,
        force=True,
        now=datetime(2026, 5, 2, 18, 0),
        downloader=downloader,
    )

    assert result.refreshed is True
    assert calls == ["tefas"]


def test_failed_download_keeps_existing_pointer(fixtures_dir, tmp_path):
    data_root = tmp_path / "data"
    staged = tmp_path / "first"
    _copy_bundle(fixtures_dir, staged)
    publish_bundle(staged, "tefas", data_root)
    pointer = data_root / "tefas" / "current.json"
    pointer_before = pointer.read_bytes()

    def fail(*args, **kwargs):
        raise WebExportError("export unavailable")

    with pytest.raises(DataRefreshError, match="export unavailable"):
        refresh_universe(
            "tefas",
            data_root,
            force=True,
            downloader=fail,
        )

    assert pointer.read_bytes() == pointer_before


def test_invalid_download_never_creates_active_pointer(fixtures_dir, tmp_path):
    data_root = tmp_path / "data"

    def incomplete(universe, staged_dir, *, now):
        shutil.copy2(fixtures_dir / "getiri_small.csv", staged_dir / "getiri.csv")

    with pytest.raises(DataRefreshError, match="failed bundle validation"):
        refresh_universe(
            "befas",
            data_root,
            force=True,
            downloader=incomplete,
        )

    assert not (data_root / "befas" / "current.json").exists()


def test_refresh_rejects_unknown_universe(tmp_path):
    with pytest.raises(ValueError, match="Unsupported universe"):
        refresh_universe("both", tmp_path)


def test_refresh_reports_busy_lock(monkeypatch, tmp_path):
    class BusyLock:
        def acquire(self, *, blocking):
            assert blocking is False
            return False

    monkeypatch.setattr("fundexpert.data.refresh._REFRESH_LOCK", BusyLock())

    with pytest.raises(DataRefreshBusyError, match="already running"):
        refresh_universe("tefas", tmp_path, force=True)
