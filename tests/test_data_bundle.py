import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from fundexpert.data.bundle import (
    BUNDLE_FILENAMES,
    BundleValidationError,
    publish_bundle,
    resolve_active_bundle,
    validate_bundle,
)


def _copy_bundle(fixtures_dir: Path, destination: Path) -> Path:
    destination.mkdir(parents=True)
    source_names = {
        "getiri.csv": "getiri_small.csv",
        "buyukluk.csv": "buyukluk_small.csv",
        "yonetim ucreti.csv": "yonetim_small.csv",
    }
    for target_name, source_name in source_names.items():
        shutil.copy2(fixtures_dir / source_name, destination / target_name)
    return destination


def _replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_validate_bundle_builds_manifest(fixtures_dir, tmp_path):
    bundle_dir = _copy_bundle(fixtures_dir, tmp_path / "candidate")

    manifest = validate_bundle(bundle_dir, "tefas")

    assert manifest.universe == "tefas"
    assert manifest.source == "manual"
    assert manifest.row_count == 3
    assert manifest.exported_at == datetime(2026, 5, 2, 11, 2, 13)
    assert manifest.bundle_id.startswith("20260502T110213-")
    assert {item.filename for item in manifest.files} == set(BUNDLE_FILENAMES)
    assert all(len(item.sha256) == 64 for item in manifest.files)


def test_validate_bundle_rejects_missing_file(fixtures_dir, tmp_path):
    bundle_dir = _copy_bundle(fixtures_dir, tmp_path / "candidate")
    (bundle_dir / "buyukluk.csv").unlink()

    with pytest.raises(BundleValidationError, match="Required file is missing"):
        validate_bundle(bundle_dir, "tefas")


def test_validate_bundle_rejects_reported_count_mismatch(fixtures_dir, tmp_path):
    bundle_dir = _copy_bundle(fixtures_dir, tmp_path / "candidate")
    _replace(bundle_dir / "getiri.csv", "Toplam Kayıt Sayısı:,3", "Toplam Kayıt Sayısı:,4")

    with pytest.raises(BundleValidationError, match="reports 4 rows but contains 3"):
        validate_bundle(bundle_dir, "tefas")


def test_validate_bundle_rejects_code_set_mismatch(fixtures_dir, tmp_path):
    bundle_dir = _copy_bundle(fixtures_dir, tmp_path / "candidate")
    _replace(bundle_dir / "buyukluk.csv", "AAA,ALPHA", "ZZZ,ALPHA")

    with pytest.raises(BundleValidationError, match="fund-code set does not match"):
        validate_bundle(bundle_dir, "tefas")


def test_validate_bundle_rejects_duplicate_codes(fixtures_dir, tmp_path):
    bundle_dir = _copy_bundle(fixtures_dir, tmp_path / "candidate")
    _replace(bundle_dir / "getiri.csv", "BBB,BETA", "AAA,BETA")

    with pytest.raises(BundleValidationError, match="duplicate fund codes"):
        validate_bundle(bundle_dir, "tefas")


def test_validate_bundle_rejects_timestamp_skew(fixtures_dir, tmp_path):
    bundle_dir = _copy_bundle(fixtures_dir, tmp_path / "candidate")
    _replace(
        bundle_dir / "getiri.csv",
        "02.05.2026 11:01:58",
        "02.05.2026 10:01:58",
    )

    with pytest.raises(BundleValidationError, match="more than 30 minutes"):
        validate_bundle(bundle_dir, "tefas")


def test_validate_bundle_rejects_invalid_numeric_value(fixtures_dir, tmp_path):
    bundle_dir = _copy_bundle(fixtures_dir, tmp_path / "candidate")
    _replace(bundle_dir / "getiri.csv", '"4,50"', "not-a-number")

    with pytest.raises(BundleValidationError, match="invalid numeric values"):
        validate_bundle(bundle_dir, "tefas")


def test_resolve_active_bundle_supports_legacy_layout(fixtures_dir, tmp_path):
    _copy_bundle(fixtures_dir, tmp_path / "data" / "tefas")

    active = resolve_active_bundle("tefas", tmp_path / "data")

    assert active.path == tmp_path / "data" / "tefas"
    assert active.manifest.source == "legacy"
    assert active.manifest.imported_at is None


def test_publish_bundle_activates_immutable_version(fixtures_dir, tmp_path):
    staged = _copy_bundle(fixtures_dir, tmp_path / "candidate")
    imported_at = datetime(2026, 7, 26, 12, 30)

    manifest = publish_bundle(
        staged,
        "tefas",
        tmp_path / "data",
        source="browser",
        now=imported_at,
    )
    active = resolve_active_bundle("tefas", tmp_path / "data")

    pointer = json.loads(
        (tmp_path / "data" / "tefas" / "current.json").read_text(encoding="utf-8")
    )
    assert pointer["bundle_id"] == manifest.bundle_id
    assert active.path.name == manifest.bundle_id
    assert active.manifest.source == "browser"
    assert active.manifest.imported_at == imported_at
    assert staged.is_dir()


def test_failed_publication_keeps_current_pointer(fixtures_dir, tmp_path):
    valid = _copy_bundle(fixtures_dir, tmp_path / "valid")
    first = publish_bundle(valid, "tefas", tmp_path / "data")
    pointer_path = tmp_path / "data" / "tefas" / "current.json"
    pointer_before = pointer_path.read_bytes()

    invalid = _copy_bundle(fixtures_dir, tmp_path / "invalid")
    (invalid / "getiri.csv").unlink()
    with pytest.raises(BundleValidationError):
        publish_bundle(invalid, "tefas", tmp_path / "data")

    assert pointer_path.read_bytes() == pointer_before
    assert resolve_active_bundle("tefas", tmp_path / "data").manifest.bundle_id == first.bundle_id


def test_tampered_active_bundle_is_rejected(fixtures_dir, tmp_path):
    staged = _copy_bundle(fixtures_dir, tmp_path / "candidate")
    manifest = publish_bundle(staged, "tefas", tmp_path / "data")
    active_file = (
        tmp_path
        / "data"
        / "tefas"
        / "bundles"
        / manifest.bundle_id
        / "getiri.csv"
    )
    active_file.write_text(
        active_file.read_text(encoding="utf-8").replace("ALPHA", "ALTERED", 1),
        encoding="utf-8",
    )

    with pytest.raises(BundleValidationError, match="immutable ID"):
        resolve_active_bundle("tefas", tmp_path / "data")
