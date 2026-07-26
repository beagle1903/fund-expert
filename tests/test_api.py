import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import fundexpert.api as api


def _copy_universe(fixtures_dir: Path, data_root: Path, universe: str) -> Path:
    destination = data_root / universe
    destination.mkdir(parents=True)
    source_names = {
        "getiri.csv": "getiri_small.csv",
        "buyukluk.csv": "buyukluk_small.csv",
        "yonetim ucreti.csv": "yonetim_small.csv",
    }
    for target_name, source_name in source_names.items():
        shutil.copy2(fixtures_dir / source_name, destination / target_name)
    return destination


@pytest.fixture
def client(fixtures_dir, tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    _copy_universe(fixtures_dir, data_root, "tefas")
    _copy_universe(fixtures_dir, data_root, "befas")
    monkeypatch.setattr(api, "DATA_ROOT", data_root)
    api.clear_candidate_cache()
    with TestClient(api.app) as test_client:
        yield test_client
    api.clear_candidate_cache()


def test_generate_returns_projected_contract_and_snapshot(client):
    response = client.post("/api/generate", json={"universe": "tefas"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "weighted",
        "header",
        "hits_for_render",
        "news_meta",
        "data_snapshot",
    }
    assert len(body["weighted"]) == 3
    assert sum(item["display_weight_pct"] for item in body["weighted"]) == 100
    assert set(body["weighted"][0]) == {
        "fon_kodu",
        "fon_adi",
        "strategy",
        "sector",
        "display_weight_pct",
        "score",
        "risk",
    }
    assert body["data_snapshot"]["source"] == "legacy"
    assert body["data_snapshot"]["row_count"] == 3
    assert body["data_snapshot"]["exported_at"] == "2026-05-02T11:02:13"
    assert body["header"]["candidate_total"] == 3


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("universe", "invalid"),
        ("risk_level", "extreme"),
        ("horizon", "annual"),
        ("volume_priority", "urgent"),
        ("fee_priority", "urgent"),
        ("momentum_priority", "urgent"),
        ("n", 0),
        ("n", 21),
        ("n", "8"),
        ("n", True),
        ("max_per_type", 0),
        ("max_per_type", 21),
        ("max_per_sector", 0),
        ("max_per_sector", 21),
    ],
)
def test_generate_rejects_invalid_fields(client, field, value):
    payload = {"universe": "tefas", field: value}

    response = client.post("/api/generate", json=payload)

    assert response.status_code == 422


def test_generate_rejects_extra_fields(client):
    response = client.post(
        "/api/generate",
        json={"universe": "tefas", "unexpected": "value"},
    )

    assert response.status_code == 422


def test_generate_returns_safe_503_for_missing_data(client, monkeypatch, tmp_path):
    monkeypatch.setattr(api, "DATA_ROOT", tmp_path / "missing")
    api.clear_candidate_cache()

    response = client.post("/api/generate", json={"universe": "tefas"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "DATA_UNAVAILABLE",
            "message": "Data for TEFAS is unavailable or invalid.",
        }
    }


def test_generate_returns_safe_500_for_unexpected_pipeline_error(client, monkeypatch):
    def fail_pipeline(*args, **kwargs):
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(api, "run_pipeline", fail_pipeline)

    response = client.post("/api/generate", json={"universe": "tefas"})

    assert response.status_code == 500
    assert response.json() == {
        "detail": {
            "code": "INTERNAL_ERROR",
            "message": "Portfolio generation failed unexpectedly.",
        }
    }
    assert "sensitive" not in response.text


def test_data_status_reports_availability_and_file_provenance(client):
    response = client.get("/api/data-status")

    assert response.status_code == 200
    statuses = {item["universe"]: item for item in response.json()["universes"]}
    assert statuses["tefas"]["available"] is True
    assert statuses["befas"]["available"] is True
    assert statuses["tefas"]["snapshot"]["row_count"] == 3
    assert len(statuses["tefas"]["files"]) == 3
    assert all(len(item["sha256"]) == 64 for item in statuses["tefas"]["files"])


def test_data_status_keeps_other_universe_available(client, monkeypatch, tmp_path, fixtures_dir):
    data_root = tmp_path / "partial"
    _copy_universe(fixtures_dir, data_root, "tefas")
    monkeypatch.setattr(api, "DATA_ROOT", data_root)

    response = client.get("/api/data-status")

    statuses = {item["universe"]: item for item in response.json()["universes"]}
    assert statuses["tefas"]["available"] is True
    assert statuses["befas"] == {
        "universe": "befas",
        "available": False,
        "snapshot": None,
        "files": [],
        "error": {
            "code": "DATA_UNAVAILABLE",
            "message": "Data for BEFAS is unavailable or invalid.",
        },
    }


def test_deleted_file_invalidates_cache_instead_of_serving_stale_data(
    client, monkeypatch
):
    first = client.post("/api/generate", json={"universe": "tefas"})
    assert first.status_code == 200
    data_root = api.DATA_ROOT
    (data_root / "tefas" / "getiri.csv").unlink()

    second = client.post("/api/generate", json={"universe": "tefas"})

    assert second.status_code == 503


def test_changed_bundle_fingerprint_refreshes_cached_candidates(client):
    payload = {
        "universe": "tefas",
        "n": 3,
        "max_per_type": 20,
        "max_per_sector": 20,
    }
    first = client.post("/api/generate", json=payload)
    assert first.status_code == 200
    first_id = first.json()["data_snapshot"]["bundle_id"]

    path = api.DATA_ROOT / "tefas" / "getiri.csv"
    path.write_text(
        path.read_text(encoding="utf-8").replace("ALPHA FON", "OMEGA FON", 1),
        encoding="utf-8",
    )
    second = client.post("/api/generate", json=payload)

    assert second.status_code == 200
    assert second.json()["data_snapshot"]["bundle_id"] != first_id
    names = {item["fon_adi"] for item in second.json()["weighted"]}
    assert "OMEGA FON" in names
