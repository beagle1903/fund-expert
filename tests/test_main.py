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


def test_python_m_fundexpert_delegates_to_cli_main():
    with patch("fundexpert.cli.main", return_value=0) as mocked_main:
        runpy.run_module("fundexpert.__main__", run_name="__main__")

    mocked_main.assert_called_once_with()
