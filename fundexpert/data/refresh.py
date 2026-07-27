"""Coordinate freshness checks, web-export acquisition, and atomic publication."""

from __future__ import annotations

import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from fundexpert.data.bundle import (
    BundleValidationError,
    DataBundleManifest,
    publish_bundle,
    resolve_active_bundle,
)
from fundexpert.data.tefas_export import WebExportError, download_web_export_bundle


class DataRefreshError(RuntimeError):
    """Raised when fresh data cannot be safely acquired and published."""


class DataRefreshBusyError(DataRefreshError):
    """Raised when another refresh already owns the acquisition lock."""


@dataclass(frozen=True)
class DataRefreshResult:
    universe: str
    refreshed: bool
    manifest: DataBundleManifest


BundleDownloader = Callable[..., None]
_REFRESH_LOCK = threading.Lock()


def _fresh_manifest(
    universe: str,
    data_root: Path,
    now: datetime,
) -> DataBundleManifest | None:
    try:
        manifest = resolve_active_bundle(universe, data_root).manifest
    except (BundleValidationError, OSError, UnicodeError, ValueError):
        return None
    return manifest if manifest.exported_at.date() == now.date() else None


def refresh_universe(
    universe: str,
    data_root: Path,
    *,
    force: bool = False,
    now: datetime | None = None,
    downloader: BundleDownloader = download_web_export_bundle,
) -> DataRefreshResult:
    """Refresh one universe once per local day unless ``force`` is true."""
    if universe not in {"tefas", "befas"}:
        raise ValueError(f"Unsupported universe: {universe!r}.")
    current_time = now or datetime.now()
    data_root = Path(data_root)

    if not force:
        fresh = _fresh_manifest(universe, data_root, current_time)
        if fresh is not None:
            return DataRefreshResult(universe, False, fresh)

    if not _REFRESH_LOCK.acquire(blocking=False):
        raise DataRefreshBusyError("Another data refresh is already running.")
    try:
        if not force:
            fresh = _fresh_manifest(universe, data_root, current_time)
            if fresh is not None:
                return DataRefreshResult(universe, False, fresh)

        with tempfile.TemporaryDirectory(prefix=f"fundexpert-{universe}-") as temp:
            staged_dir = Path(temp)
            try:
                downloader(universe, staged_dir, now=current_time)
                manifest = publish_bundle(
                    staged_dir,
                    universe,
                    data_root,
                    source="tefas-web-export",
                    now=current_time,
                )
            except WebExportError as exc:
                raise DataRefreshError(str(exc)) from exc
            except BundleValidationError as exc:
                raise DataRefreshError(
                    f"Downloaded {universe.upper()} data failed bundle validation."
                ) from exc
        return DataRefreshResult(universe, True, manifest)
    finally:
        _REFRESH_LOCK.release()
