import timeit
from pathlib import Path
from fundexpert.data.loader import load_candidates_for_universe

root = Path("data")
def test_load():
    _ = load_candidates_for_universe("tefas", root)

print("Load:", timeit.timeit(test_load, number=10))
