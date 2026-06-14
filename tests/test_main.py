import sys
from unittest.mock import patch
import pytest

from fundexpert.cli import main

def test_main_runs_without_crashing():
    with patch.object(sys, "argv", ["fundexpert", "--help"]):
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 0
