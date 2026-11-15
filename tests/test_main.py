import runpy
import sys
from unittest.mock import patch
import pytest

from fundexpert.cli import main

def test_main_runs_without_crashing():
    with patch.object(sys, "argv", ["fundexpert", "--help"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0


@pytest.mark.parametrize("return_code", [0, 2, 130])
def test_python_m_fundexpert_exits_with_cli_main_return_code(return_code):
    with patch("fundexpert.cli.main", return_value=return_code) as mocked_main:
        with pytest.raises(SystemExit) as exit_info:
            runpy.run_module("fundexpert.__main__", run_name="__main__")

    mocked_main.assert_called_once_with()
    assert exit_info.value.code == return_code
