import pytest

from fundexpert import config


def test_priority_weights_match_spec():
    assert config.DEFAULT_SCORING_CONFIG.priority_weights == {"low": 0.10, "medium": 0.30, "high": 0.60}


def test_risk_level_lambdas_match_spec():
    # Keyed by desired risk level: "low" → big penalty (wants safe funds),
    # "high" → tiny penalty (wants risky funds).
    assert config.DEFAULT_SCORING_CONFIG.risk_level_lambdas == {"low": 0.60, "medium": 0.25, "high": 0.05}


def test_horizon_buckets_match_spec():
    assert config.DEFAULT_SCORING_CONFIG.horizon_buckets == {
        "short":  ("ret_1m", "ret_3m"),
        "medium": ("ret_6m", "ret_1y"),
        "long":   ("ret_3y", "ret_5y"),
    }


def test_default_max_per_type():
    assert config.DEFAULT_MAX_PER_TYPE == 2


def test_weight_epsilon():
    assert config.DEFAULT_SELECTION_CONFIG.weight_epsilon == 0.01


@pytest.mark.parametrize(
    ("mode", "n", "expected"),
    [
        ("strict", 1, 2),
        ("strict", 11, 2),
        ("strict", 12, 2),
        ("strict", 15, 2),
        ("strict", 16, 2),
        ("strict", 20, 2),
        ("balanced", 1, 2),
        ("balanced", 11, 2),
        ("balanced", 12, 3),
        ("balanced", 15, 3),
        ("balanced", 16, 4),
        ("balanced", 20, 4),
        ("relaxed", 1, 3),
        ("relaxed", 11, 3),
        ("relaxed", 12, 4),
        ("relaxed", 15, 4),
        ("relaxed", 16, 5),
        ("relaxed", 20, 5),
    ],
)
def test_resolve_diversification_caps_schedule(mode, n, expected):
    assert config.resolve_diversification_caps(n, mode) == (expected, expected)


def test_resolve_diversification_caps_applies_independent_overrides():
    assert config.resolve_diversification_caps(
        16,
        "balanced",
        max_per_type=7,
    ) == (7, 4)
    assert config.resolve_diversification_caps(
        12,
        "relaxed",
        max_per_sector=6,
    ) == (4, 6)


@pytest.mark.parametrize(
    ("n", "mode", "max_per_type", "max_per_sector"),
    [
        (0, "balanced", None, None),
        (21, "balanced", None, None),
        (8, "unknown", None, None),
        (8, "balanced", 0, None),
        (8, "balanced", None, 21),
    ],
)
def test_resolve_diversification_caps_rejects_invalid_inputs(
    n, mode, max_per_type, max_per_sector
):
    with pytest.raises(ValueError):
        config.resolve_diversification_caps(
            n,
            mode,
            max_per_type=max_per_type,
            max_per_sector=max_per_sector,
        )
