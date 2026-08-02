import copy
import json
from pathlib import Path

import pytest

from fundexpert.build_profile import (
    DEFAULT_BUILD_PROFILE,
    BuildProfileError,
    get_build_profile_path,
    load_build_profile,
    save_build_profile,
)


def test_profile_path_uses_plugin_state_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("FUND_EXPERT_STATE_DIR", str(tmp_path))

    assert get_build_profile_path() == (tmp_path / "profiles" / "default.json").resolve()


def test_load_returns_validated_template_when_saved_profile_is_missing(tmp_path):
    path = tmp_path / "profiles" / "default.json"

    profile, loaded_path, source = load_build_profile(path)

    assert loaded_path == path
    assert source == "default_template"
    assert profile.fund_count == 6
    assert profile.allowed_risk_values == [4, 5, 6]
    assert not path.exists()


def test_save_atomically_publishes_profile_that_can_be_loaded(tmp_path):
    path = tmp_path / "profiles" / "default.json"
    payload = copy.deepcopy(DEFAULT_BUILD_PROFILE)
    payload["fund_count"] = 8

    saved, saved_path = save_build_profile(payload, path)
    loaded, loaded_path, source = load_build_profile(path)

    assert saved.fund_count == 8
    assert saved_path == path
    assert loaded_path == path
    assert source == "saved"
    assert loaded == saved
    assert json.loads(path.read_text(encoding="utf-8"))["fund_count"] == 8
    assert list(path.parent.glob("*.tmp")) == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda profile: profile["metric_weights"].update(
            {key: 0 for key in profile["metric_weights"]}
        ),
        lambda profile: profile["growth_winsorization"].update(
            {"lower_quantile": 0.9, "upper_quantile": 0.1}
        ),
        lambda profile: profile["audit"].update(
            {"target_weighted_risk_range": [6, 4]}
        ),
        lambda profile: profile.update({"fund_count": 3}),
    ],
)
def test_save_rejects_profiles_the_plugin_cannot_consume(tmp_path, mutate):
    payload = copy.deepcopy(DEFAULT_BUILD_PROFILE)
    mutate(payload)

    with pytest.raises(BuildProfileError):
        save_build_profile(payload, tmp_path / "default.json")


def test_load_rejects_invalid_saved_json(tmp_path):
    path = tmp_path / "default.json"
    path.write_text('{"schema_version": "1.0"}', encoding="utf-8")

    with pytest.raises(BuildProfileError):
        load_build_profile(path)
