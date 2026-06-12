import pandas as pd
import pytest

from fundexpert.scoring.normalize import minmax_normalize


def test_minmax_scales_robustly():
    s = pd.Series([0.0, 50.0, 100.0])
    out = minmax_normalize(s)
    # pd.Series([0, 50, 100]).quantile(0.01) == 1.0
    # pd.Series([0, 50, 100]).quantile(0.99) == 99.0
    # clipping ensures we bound it to [0, 1]
    assert out.iloc[0] == 0.0
    assert out.iloc[-1] == 1.0
    assert out.iloc[1] == 0.5


def test_minmax_constant_column_returns_neutral_half():
    s = pd.Series([5.0, 5.0, 5.0])
    out = minmax_normalize(s)
    assert (out == 0.5).all()


def test_minmax_handles_nan_as_neutral_half():
    s = pd.Series([0.0, float("nan"), 100.0])
    out = minmax_normalize(s)
    assert out.iloc[0] == 0.0
    assert out.iloc[1] == 0.5
    assert out.iloc[2] == 1.0


def test_minmax_single_value():
    s = pd.Series([7.5])
    out = minmax_normalize(s)
    assert out.iloc[0] == 0.5

def test_minmax_handles_all_nan():
    s = pd.Series([float("nan"), float("nan")])
    out = minmax_normalize(s)
    assert (out == 0.5).all()


def test_minmax_handles_empty_dataframe():
    from fundexpert.scoring.normalize import minmax_normalize
    import pandas as pd
    s = pd.Series([], dtype=float)
    res = minmax_normalize(s)
    assert res.empty
