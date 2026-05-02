import pandas as pd
import pytest

from fundexpert.scoring.normalize import minmax_normalize


def test_minmax_scales_to_zero_one():
    s = pd.Series([10.0, 20.0, 30.0, 40.0])
    out = minmax_normalize(s)
    assert out.iloc[0] == 0.0
    assert out.iloc[-1] == 1.0
    assert out.iloc[1] == pytest.approx(1 / 3)


def test_minmax_constant_column_returns_neutral_half():
    s = pd.Series([5.0, 5.0, 5.0])
    out = minmax_normalize(s)
    assert (out == 0.5).all()


def test_minmax_handles_nan_as_neutral_half():
    s = pd.Series([10.0, float("nan"), 30.0])
    out = minmax_normalize(s)
    assert out.iloc[0] == 0.0
    assert out.iloc[1] == 0.5
    assert out.iloc[2] == 1.0


def test_minmax_single_value():
    s = pd.Series([7.5])
    out = minmax_normalize(s)
    assert out.iloc[0] == 0.5
