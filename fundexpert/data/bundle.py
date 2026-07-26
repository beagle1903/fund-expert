"""Validate, describe, resolve, and atomically publish TEFAS/BEFAS bundles."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from fundexpert.config import MAX_CSV_SIZE_BYTES
from fundexpert.data import loader as loader_module

BUNDLE_SCHEMA_VERSION = 1
BUNDLE_FILENAMES = ("getiri.csv", "buyukluk.csv", "yonetim ucreti.csv")
MAX_EXPORT_TIME_SKEW = timedelta(minutes=30)

_RENAME_BY_FILENAME = {
    "getiri.csv": loader_module.GETIRI_RENAME,
    "buyukluk.csv": loader_module.BUYUKLUK_RENAME,
    "yonetim ucreti.csv": loader_module.YONETIM_RENAME,
}

_NUMERIC_COLUMNS_BY_FILENAME = {
    filename: tuple(
        internal_name
        for internal_name in rename.values()
        if internal_name not in {"fon_kodu", "fon_adi", "umbrella_type"}
    )
    for filename, rename in _RENAME_BY_FILENAME.items()
}


class BundleValidationError(ValueError):
    """Raised when a candidate data bundle is incomplete or inconsistent."""


@dataclass(frozen=True)
class DataFileMetadata:
    filename: str
    exported_at: datetime
    reported_rows: int
    actual_rows: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "exported_at": self.exported_at.isoformat(),
            "reported_rows": self.reported_rows,
            "actual_rows": self.actual_rows,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DataFileMetadata:
        return cls(
            filename=str(value["filename"]),
            exported_at=datetime.fromisoformat(str(value["exported_at"])),
            reported_rows=int(value["reported_rows"]),
            actual_rows=int(value["actual_rows"]),
            sha256=str(value["sha256"]),
        )


@dataclass(frozen=True)
class DataBundleManifest:
    schema_version: int
    universe: str
    bundle_id: str
    source: str
    imported_at: datetime | None
    exported_at: datetime
    row_count: int
    files: tuple[DataFileMetadata, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "universe": self.universe,
            "bundle_id": self.bundle_id,
            "source": self.source,
            "imported_at": self.imported_at.isoformat() if self.imported_at else None,
            "exported_at": self.exported_at.isoformat(),
            "row_count": self.row_count,
            "files": [item.to_dict() for item in self.files],
        }

    def to_snapshot_dict(self) -> dict[str, Any]:
        return {
            "universe": self.universe,
            "bundle_id": self.bundle_id,
            "source": self.source,
            "exported_at": self.exported_at.isoformat(),
            "imported_at": self.imported_at.isoformat() if self.imported_at else None,
            "row_count": self.row_count,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> DataBundleManifest:
        imported_at = value.get("imported_at")
        return cls(
            schema_version=int(value["schema_version"]),
            universe=str(value["universe"]),
            bundle_id=str(value["bundle_id"]),
            source=str(value["source"]),
            imported_at=datetime.fromisoformat(str(imported_at)) if imported_at else None,
            exported_at=datetime.fromisoformat(str(value["exported_at"])),
            row_count=int(value["row_count"]),
            files=tuple(DataFileMetadata.from_dict(item) for item in value["files"]),
        )


@dataclass(frozen=True)
class ActiveDataBundle:
    path: Path
    manifest: DataBundleManifest

    @property
    def fingerprint(self) -> str:
        return self.manifest.bundle_id


def _validate_universe(universe: str) -> None:
    if universe not in {"tefas", "befas"}:
        raise BundleValidationError(f"Unsupported universe: {universe!r}.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_preamble(path: Path) -> tuple[datetime, int]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            first = next(csv.reader([handle.readline()]))
            second = next(csv.reader([handle.readline()]))
    except (OSError, UnicodeError, StopIteration) as exc:
        raise BundleValidationError(f"{path.name}: preamble could not be read.") from exc

    if len(first) < 2 or first[0].strip() != "Dışa Aktarım Tarihi:":
        raise BundleValidationError(f"{path.name}: export timestamp is missing.")
    if len(second) < 2 or second[0].strip() != "Toplam Kayıt Sayısı:":
        raise BundleValidationError(f"{path.name}: reported row count is missing.")

    try:
        exported_at = datetime.strptime(first[1].strip(), "%d.%m.%Y %H:%M:%S")
        reported_rows = int(second[1].strip())
    except ValueError as exc:
        raise BundleValidationError(f"{path.name}: invalid preamble values.") from exc

    if reported_rows < 0:
        raise BundleValidationError(f"{path.name}: reported row count cannot be negative.")
    return exported_at, reported_rows


def _validate_frame(filename: str, frame: pd.DataFrame) -> set[str]:
    codes = frame["fon_kodu"].astype("string").str.strip()
    if codes.isna().any() or (codes == "").any():
        raise BundleValidationError(f"{filename}: fund codes must be non-empty.")
    duplicates = codes[codes.duplicated()].dropna().unique().tolist()
    if duplicates:
        sample = ", ".join(str(code) for code in duplicates[:3])
        raise BundleValidationError(f"{filename}: duplicate fund codes: {sample}.")

    for column in _NUMERIC_COLUMNS_BY_FILENAME[filename]:
        values = frame[column]
        converted = pd.to_numeric(values, errors="coerce")
        invalid = values.notna() & converted.isna()
        if invalid.any():
            raise BundleValidationError(f"{filename}: column {column!r} contains invalid numeric values.")

    if filename == "getiri.csv":
        risk = pd.to_numeric(frame["risk"], errors="coerce").dropna()
        if not risk.between(1, 7).all():
            raise BundleValidationError("getiri.csv: risk values must be between 1 and 7.")

    return set(codes.astype(str))


def validate_bundle(
    bundle_dir: Path,
    universe: str,
    *,
    source: str = "manual",
    imported_at: datetime | None = None,
) -> DataBundleManifest:
    """Validate a three-file export bundle and return its immutable manifest."""
    _validate_universe(universe)
    bundle_dir = Path(bundle_dir)
    paths = {filename: bundle_dir / filename for filename in BUNDLE_FILENAMES}

    for filename, path in paths.items():
        if not path.is_file():
            raise BundleValidationError(f"Required file is missing: {filename}.")
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise BundleValidationError(f"{filename}: file metadata could not be read.") from exc
        if size > MAX_CSV_SIZE_BYTES:
            raise BundleValidationError(
                f"{filename}: exceeds the {MAX_CSV_SIZE_BYTES}-byte size limit."
            )

    try:
        frames = loader_module.load_universe(
            getiri_path=paths["getiri.csv"],
            buyukluk_path=paths["buyukluk.csv"],
            yonetim_path=paths["yonetim ucreti.csv"],
        )
    except (OSError, UnicodeError, ValueError, pd.errors.ParserError) as exc:
        raise BundleValidationError(f"CSV parsing failed: {exc}") from exc

    frames_by_filename: dict[str, pd.DataFrame] = {
        "getiri.csv": frames.getiri,
        "buyukluk.csv": frames.buyukluk,
        "yonetim ucreti.csv": frames.yonetim_ucreti,
    }
    metadata: list[DataFileMetadata] = []
    code_sets: dict[str, set[str]] = {}

    for filename in BUNDLE_FILENAMES:
        path = paths[filename]
        exported_at, reported_rows = _parse_preamble(path)
        frame = frames_by_filename[filename]
        actual_rows = len(frame)
        if reported_rows != actual_rows:
            raise BundleValidationError(
                f"{filename}: reports {reported_rows} rows but contains {actual_rows}."
            )
        code_sets[filename] = _validate_frame(filename, frame)
        metadata.append(
            DataFileMetadata(
                filename=filename,
                exported_at=exported_at,
                reported_rows=reported_rows,
                actual_rows=actual_rows,
                sha256=_sha256(path),
            )
        )

    reference_codes = code_sets[BUNDLE_FILENAMES[0]]
    for filename in BUNDLE_FILENAMES[1:]:
        if code_sets[filename] != reference_codes:
            raise BundleValidationError(
                f"{filename}: fund-code set does not match {BUNDLE_FILENAMES[0]}."
            )

    export_times = [item.exported_at for item in metadata]
    if max(export_times) - min(export_times) > MAX_EXPORT_TIME_SKEW:
        raise BundleValidationError("Export timestamps span more than 30 minutes.")

    digest_material = universe + "".join(item.sha256 for item in metadata)
    bundle_hash = hashlib.sha256(digest_material.encode("ascii")).hexdigest()
    exported_at = max(export_times)
    bundle_id = f"{exported_at:%Y%m%dT%H%M%S}-{bundle_hash[:12]}"

    return DataBundleManifest(
        schema_version=BUNDLE_SCHEMA_VERSION,
        universe=universe,
        bundle_id=bundle_id,
        source=source,
        imported_at=imported_at,
        exported_at=exported_at,
        row_count=len(reference_codes),
        files=tuple(metadata),
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BundleValidationError(f"{path.name}: invalid JSON.") from exc
    if not isinstance(value, dict):
        raise BundleValidationError(f"{path.name}: expected a JSON object.")
    return value


def resolve_active_bundle(universe: str, data_root: Path) -> ActiveDataBundle:
    """Resolve and validate the active versioned bundle or legacy flat files."""
    _validate_universe(universe)
    universe_dir = Path(data_root) / universe
    pointer_path = universe_dir / "current.json"

    if not pointer_path.exists():
        manifest = validate_bundle(universe_dir, universe, source="legacy")
        return ActiveDataBundle(path=universe_dir, manifest=manifest)

    pointer = _read_json(pointer_path)
    if pointer.get("schema_version") != BUNDLE_SCHEMA_VERSION:
        raise BundleValidationError("current.json: unsupported schema version.")
    bundle_id = pointer.get("bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise BundleValidationError("current.json: bundle_id is missing.")

    bundle_dir = universe_dir / "bundles" / bundle_id
    manifest_path = bundle_dir / "manifest.json"
    persisted = DataBundleManifest.from_dict(_read_json(manifest_path))
    if persisted.universe != universe or persisted.bundle_id != bundle_id:
        raise BundleValidationError("Active manifest does not match current.json.")

    validated = validate_bundle(
        bundle_dir,
        universe,
        source=persisted.source,
        imported_at=persisted.imported_at,
    )
    if validated.bundle_id != bundle_id:
        raise BundleValidationError("Active bundle contents do not match its immutable ID.")
    if validated.to_dict() != persisted.to_dict():
        raise BundleValidationError("Active manifest does not match bundle contents.")
    return ActiveDataBundle(path=bundle_dir, manifest=persisted)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def publish_bundle(
    staged_dir: Path,
    universe: str,
    data_root: Path,
    *,
    source: str = "manual",
    now: datetime | None = None,
) -> DataBundleManifest:
    """Validate and atomically activate an immutable bundle.

    Validation finishes before ``current.json`` changes. The caller's staging
    directory is never modified.
    """
    imported_at = now or datetime.now()
    source_manifest = validate_bundle(
        Path(staged_dir),
        universe,
        source=source,
        imported_at=imported_at,
    )

    universe_dir = Path(data_root) / universe
    bundles_dir = universe_dir / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    destination = bundles_dir / source_manifest.bundle_id

    if destination.exists():
        existing = resolve_bundle_directory(destination, universe)
        source_manifest = existing
    else:
        temp_dir = Path(tempfile.mkdtemp(prefix=".bundle-", dir=bundles_dir))
        try:
            for filename in BUNDLE_FILENAMES:
                shutil.copy2(Path(staged_dir) / filename, temp_dir / filename)
            copied_manifest = validate_bundle(
                temp_dir,
                universe,
                source=source,
                imported_at=imported_at,
            )
            if copied_manifest.to_dict() != source_manifest.to_dict():
                raise BundleValidationError("Staged bundle changed while it was being published.")
            _write_json(temp_dir / "manifest.json", copied_manifest.to_dict())
            os.replace(temp_dir, destination)
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    pointer = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_id": source_manifest.bundle_id,
    }
    universe_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=universe_dir,
        delete=False,
        suffix=".json",
    ) as handle:
        json.dump(pointer, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        pointer_temp = Path(handle.name)
    try:
        os.replace(pointer_temp, universe_dir / "current.json")
    finally:
        pointer_temp.unlink(missing_ok=True)
    return source_manifest


def resolve_bundle_directory(bundle_dir: Path, universe: str) -> DataBundleManifest:
    """Validate an already-published immutable bundle directory."""
    persisted = DataBundleManifest.from_dict(_read_json(Path(bundle_dir) / "manifest.json"))
    validated = validate_bundle(
        Path(bundle_dir),
        universe,
        source=persisted.source,
        imported_at=persisted.imported_at,
    )
    if validated.to_dict() != persisted.to_dict():
        raise BundleValidationError("Published manifest does not match bundle contents.")
    return persisted


def load_bundle_frames(bundle: ActiveDataBundle) -> loader_module.UniverseData:
    """Load the three parsed frames for an already-resolved bundle."""
    return loader_module.load_universe(
        getiri_path=bundle.path / "getiri.csv",
        buyukluk_path=bundle.path / "buyukluk.csv",
        yonetim_path=bundle.path / "yonetim ucreti.csv",
    )
