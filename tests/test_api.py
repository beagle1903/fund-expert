import shutil
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import fundexpert.api as api
from fundexpert.build_profile import DEFAULT_BUILD_PROFILE, BuildProfileError
from fundexpert.data.refresh import DataRefreshError, DataRefreshResult
from fundexpert.utils import rules as rules_module


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


@pytest.fixture
def isolated_rules_file(tmp_path, monkeypatch):
    path = tmp_path / "rules.json"
    path.write_text(
        rules_module.RULES_FILE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.setattr(rules_module, "RULES_FILE", path)
    rules_module.clear_rules_cache()
    yield path
    rules_module.clear_rules_cache()


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
    assert body["header"]["candidate_after_founder"] == 3
    assert body["header"]["founder"] is None


def test_generate_refreshes_selected_universe_when_requested(client, monkeypatch):
    manifest = api.resolve_active_bundle("tefas", api.DATA_ROOT).manifest
    calls = []

    def refresh(universe, data_root, *, force):
        calls.append((universe, data_root, force))
        return DataRefreshResult(universe, False, manifest)

    monkeypatch.setattr(api, "refresh_universe", refresh)

    response = client.post(
        "/api/generate",
        json={"universe": "tefas", "refresh_data": True},
    )

    assert response.status_code == 200
    assert calls == [("tefas", api.DATA_ROOT, False)]


def test_generate_returns_safe_refresh_error(client, monkeypatch):
    def fail(*args, **kwargs):
        raise DataRefreshError("TEFAS web export is temporarily unavailable.")

    monkeypatch.setattr(api, "refresh_universe", fail)

    response = client.post(
        "/api/generate",
        json={"universe": "tefas", "refresh_data": True},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "REFRESH_FAILED",
            "message": "TEFAS web export is temporarily unavailable.",
        }
    }


def test_data_refresh_endpoint_returns_snapshot(client, monkeypatch):
    manifest = api.resolve_active_bundle("befas", api.DATA_ROOT).manifest

    monkeypatch.setattr(
        api,
        "refresh_universe",
        lambda *args, **kwargs: DataRefreshResult("befas", True, manifest),
    )

    response = client.post(
        "/api/data-refresh",
        json={"universe": "befas", "force": True},
    )

    assert response.status_code == 200
    assert response.json()["universe"] == "befas"
    assert response.json()["refreshed"] is True
    assert response.json()["snapshot"]["row_count"] == 3


def test_selection_rules_endpoint_projects_editable_rules(
    client, isolated_rules_file
):
    response = client.get("/api/selection-rules")

    assert response.status_code == 200
    body = response.json()
    assert body["bucket_rules"][0] == {
        "keyword": "HİSSE SENEDİ",
        "category": "equity",
    }
    assert body["sector_rules"][0] == {
        "keyword": "TEKNOLOJİ",
        "category": "tech",
    }
    assert body["exclusion_rules"] == ["OKS"]
    assert "cleanup_rules" not in body


def test_build_profile_endpoint_reads_and_saves_plugin_profile(
    client, tmp_path, monkeypatch
):
    state_dir = tmp_path / "plugin-state"
    monkeypatch.setenv("FUND_EXPERT_STATE_DIR", str(state_dir))

    initial = client.get("/api/build-profile")

    assert initial.status_code == 200
    assert initial.json()["source"] == "default_template"
    assert initial.json()["profile"]["fund_count"] == 6
    assert initial.json()["profile_path"] == str(
        (state_dir / "profiles" / "default.json").resolve()
    )

    payload = initial.json()["profile"]
    payload["fund_count"] = 8
    saved = client.put("/api/build-profile", json=payload)

    assert saved.status_code == 200
    assert saved.json()["source"] == "saved"
    assert saved.json()["profile"]["fund_count"] == 8
    assert json.loads(
        (state_dir / "profiles" / "default.json").read_text(encoding="utf-8")
    )["fund_count"] == 8
    assert client.get("/api/build-profile").json()["source"] == "saved"


def test_build_profile_endpoint_rejects_invalid_contract(client):
    payload = json.loads(json.dumps(DEFAULT_BUILD_PROFILE))
    payload["fund_count"] = 21

    response = client.put("/api/build-profile", json=payload)

    assert response.status_code == 422


def test_build_profile_endpoint_returns_safe_read_error(
    client, tmp_path, monkeypatch
):
    state_dir = tmp_path / "plugin-state"
    profile_path = state_dir / "profiles" / "default.json"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text('{"private": "sensitive"}', encoding="utf-8")
    monkeypatch.setenv("FUND_EXPERT_STATE_DIR", str(state_dir))

    response = client.get("/api/build-profile")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "BUILD_PROFILE_UNAVAILABLE",
            "message": "Build-plugin profile is unavailable or invalid.",
        }
    }
    assert "sensitive" not in response.text


def test_build_profile_endpoint_returns_safe_write_error(client, monkeypatch):
    monkeypatch.setattr(
        api,
        "save_build_profile",
        lambda profile: (_ for _ in ()).throw(
            BuildProfileError("sensitive path")
        ),
    )

    response = client.put("/api/build-profile", json=DEFAULT_BUILD_PROFILE)

    assert response.status_code == 500
    assert response.json() == {
        "detail": {
            "code": "BUILD_PROFILE_SAVE_FAILED",
            "message": "Build-plugin profile could not be saved.",
        }
    }
    assert "sensitive path" not in response.text


def test_selection_rules_update_is_atomic_and_preserves_cleanup_rules(
    client, isolated_rules_file
):
    original = json.loads(isolated_rules_file.read_text(encoding="utf-8"))
    payload = {
        "bucket_rules": [
            {"keyword": "YENİ STRATEJİ", "category": "custom_strategy"},
        ],
        "sector_rules": [
            {"keyword": "UZAY", "category": "space"},
        ],
        "exclusion_rules": ["OKS", "KAPALI"],
    }

    response = client.put("/api/selection-rules", json=payload)

    assert response.status_code == 200
    assert response.json() == payload
    saved = json.loads(isolated_rules_file.read_text(encoding="utf-8"))
    assert saved["bucket_rules"] == [["YENİ STRATEJİ", "custom_strategy"]]
    assert saved["sector_rules"] == [["UZAY", "space"]]
    assert saved["exclusion_rules"] == ["OKS", "KAPALI"]
    assert saved["cleanup_rules"] == original["cleanup_rules"]
    assert rules_module.get_bucket_rules() == (
        ("YENİ STRATEJİ", "custom_strategy"),
    )


def test_selection_rules_update_rejects_duplicate_keywords(
    client, isolated_rules_file
):
    payload = {
        "bucket_rules": [
            {"keyword": "ALTIN", "category": "precious_metals"},
            {"keyword": "altın", "category": "other"},
        ],
        "sector_rules": [],
        "exclusion_rules": [],
    }

    response = client.put("/api/selection-rules", json=payload)

    assert response.status_code == 422
    assert "Duplicate strategy keywords" in response.text


def test_selection_rules_update_returns_safe_write_error(
    client, isolated_rules_file, monkeypatch
):
    monkeypatch.setattr(
        api,
        "save_editable_rules",
        lambda rules: (_ for _ in ()).throw(OSError("sensitive path")),
    )
    payload = client.get("/api/selection-rules").json()

    response = client.put("/api/selection-rules", json=payload)

    assert response.status_code == 500
    assert response.json() == {
        "detail": {
            "code": "RULES_SAVE_FAILED",
            "message": "Selection rules could not be saved.",
        }
    }
    assert "sensitive path" not in response.text


def test_founders_and_generate_use_active_universe_specific_options(
    client, monkeypatch
):
    candidates, manifest = api.get_cached_candidates("tefas")
    candidates = candidates.copy()
    ak = "AK PORTFÖY YÖNETİMİ A.Ş."
    ata = "ATA PORTFÖY YÖNETİMİ A.Ş."
    candidates["kurucu"] = [ak, ata, ak]
    monkeypatch.setattr(
        api, "get_cached_candidates", lambda universe: (candidates, manifest)
    )

    options_response = client.get("/api/founders?universe=tefas")
    generate_response = client.post(
        "/api/generate",
        json={"universe": "tefas", "founder": ak, "n": 2},
    )

    assert options_response.status_code == 200
    assert options_response.json()["founders"] == [
        {"name": ak, "fund_count": 2},
        {"name": ata, "fund_count": 1},
    ]
    assert generate_response.status_code == 200
    body = generate_response.json()
    assert body["header"]["candidate_total"] == 3
    assert body["header"]["candidate_after_founder"] == 2
    assert body["header"]["founder"] == ak


def test_generate_rejects_founder_outside_active_universe(client):
    response = client.post(
        "/api/generate",
        json={
            "universe": "befas",
            "founder": "AK PORTFÖY YÖNETİMİ A.Ş.",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_FOUNDER"


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
        ("diversification_mode", "unlimited"),
        ("max_per_type", 0),
        ("max_per_type", 21),
        ("max_per_type", "3"),
        ("max_per_sector", 0),
        ("max_per_sector", 21),
        ("max_per_sector", True),
    ],
)
def test_generate_rejects_invalid_fields(client, field, value):
    payload = {"universe": "tefas", field: value}

    response = client.post("/api/generate", json=payload)

    assert response.status_code == 422


def test_generate_passes_mode_and_optional_caps_to_pipeline(client, monkeypatch):
    captured = {}
    real_run_pipeline = api.run_pipeline

    def capture(candidates, config):
        captured["config"] = config
        return real_run_pipeline(candidates, config)

    monkeypatch.setattr(api, "run_pipeline", capture)
    response = client.post(
        "/api/generate",
        json={
            "universe": "tefas",
            "n": 12,
            "diversification_mode": "relaxed",
            "max_per_type": 6,
        },
    )

    assert response.status_code == 200
    assert captured["config"].diversification_mode == "relaxed"
    assert captured["config"].max_per_type == 6
    assert captured["config"].max_per_sector is None


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
