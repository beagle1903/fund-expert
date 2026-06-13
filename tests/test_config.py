from fundexpert import config


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
        "medium": ("ret_6m", "ret_ytd", "ret_1y"),
        "long":   ("ret_3y", "ret_5y"),
    }


def test_default_max_per_type():
    assert config.DEFAULT_MAX_PER_TYPE == 2


def test_weight_epsilon():
    assert config.DEFAULT_SELECTION_CONFIG.weight_epsilon == 0.01
