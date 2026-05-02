from fundexpert import config


def test_priority_weights_match_spec():
    assert config.PRIORITY_WEIGHTS == {"low": 0.10, "medium": 0.30, "high": 0.60}


def test_risk_lambdas_match_spec():
    assert config.RISK_LAMBDAS == {"low": 0.05, "medium": 0.25, "high": 0.60}


def test_horizon_buckets_match_spec():
    assert config.HORIZON_BUCKETS == {
        "short":  ("ret_1m", "ret_3m"),
        "medium": ("ret_6m", "ret_ytd", "ret_1y"),
        "long":   ("ret_3y", "ret_5y"),
    }


def test_default_max_per_type():
    assert config.DEFAULT_MAX_PER_TYPE == 2


def test_weight_epsilon():
    assert config.WEIGHT_EPSILON == 0.01
