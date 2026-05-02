# Fund Expert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI (`fundexpert`) that recommends a Turkish investment-fund portfolio (TEFAS regular + BEFAS retirement) from local CSVs, using interactive Turkish prompts, a weighted-sum scoring engine with a soft SRRI risk penalty, score-proportional weights with an umbrella-type diversification cap, and an optional RSS news annotation pass.

**Architecture:** Single Python package with linear pipeline modules: `data` (load + merge) → `scoring` (horizon + normalize + score) → `select` (pick + weights) → `render` (rich table). `cli.py` orchestrates; `config.py` holds tunable constants. `news/rss.py` is loaded only when `--news` is set. Pure cores get unit tests; loaders get fixtures; one end-to-end smoke test runs against the real CSVs in `data/`.

**Tech Stack:** Python 3.11+, pandas, rich, questionary, feedparser, pytest.

---

## File Structure

```
fund expert/
├── data/                            # source CSVs (already exists, untouched)
│   ├── tefas/{getiri,buyukluk,yonetim ucreti}.csv
│   └── befas/{getiri,buyukluk,yonetim ucreti}.csv
├── docs/                            # design + this plan (already exists)
├── fundexpert/
│   ├── __init__.py                  # version
│   ├── __main__.py                  # `python -m fundexpert` entry
│   ├── cli.py                       # prompts + pipeline orchestration
│   ├── config.py                    # constants: priority weights, λ, max_per_type, RSS list, paths
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py                # read 3 CSVs, skip metadata, parse TR decimals, rename
│   │   └── merge.py                 # inner-join 3 frames, add universe column, concat tefas+befas
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── horizon.py               # Short/Medium/Long → mean of return columns
│   │   ├── normalize.py             # min-max scaling per column with constant-range guard
│   │   └── score.py                 # base_score − risk_penalty + per-fund explainability dict
│   ├── select/
│   │   ├── __init__.py
│   │   ├── pick.py                  # top-N respecting umbrella cap, up-to-N semantics
│   │   └── weights.py               # ε-shifted score-proportional weights, rounding reconcile
│   ├── news/
│   │   ├── __init__.py
│   │   └── rss.py                   # feedparser + 1h disk cache + match + annotate
│   └── render/
│       ├── __init__.py
│       └── table.py                 # rich Table with header block + footer (news)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # shared fixtures
│   ├── fixtures/
│   │   ├── getiri_small.csv
│   │   ├── buyukluk_small.csv
│   │   ├── yonetim_small.csv
│   │   └── rss_sample.xml
│   ├── test_loader.py
│   ├── test_merge.py
│   ├── test_horizon.py
│   ├── test_normalize.py
│   ├── test_score.py
│   ├── test_pick.py
│   ├── test_weights.py
│   ├── test_rss.py
│   └── test_smoke.py
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Task 0: Project Bootstrap

> **Already done before this plan starts executing:** the repo is already initialized (`main` branch on GitHub at `beagle1903/fund-expert`), `.gitignore` and `README.md` already exist, and `docs/` is committed. The steps below skip those.

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Verify (already exists): `.gitignore`
- Verify (already exists): `README.md`
- Create: `fundexpert/__init__.py`
- Create: `fundexpert/__main__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 0.1: Verify git is initialized**

```bash
cd "C:/Users/burha/Documents/dev-cc/fund expert"
git rev-parse --is-inside-work-tree   # expect: true
git remote -v                         # expect: origin → https://github.com/beagle1903/fund-expert
```

If for any reason the repo is not initialized, run `git init -b main` and add the remote, but otherwise skip.

- [ ] **Step 0.2: Verify `.gitignore` excludes the right things (do NOT overwrite)**

The committed `.gitignore` already excludes `__pycache__/`, `*.py[cod]`, `*.egg-info/`, `.pytest_cache/`, `.venv/`, `.fundexpert/`, `data/`, `.claude/`, OS noise, and IDE folders. Confirm by inspecting the file; if anything is missing, append (do not replace) the missing entries.

- [ ] **Step 0.3: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "fundexpert"
version = "0.1.0"
description = "CLI that recommends a Turkish investment-fund portfolio from TEFAS/BEFAS CSVs."
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.2",
    "rich>=13.7",
    "questionary>=2.0",
    "feedparser>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[project.scripts]
fundexpert = "fundexpert.cli:main"

[tool.setuptools.packages.find]
include = ["fundexpert*"]
exclude = ["tests*", "docs*", "data*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

- [ ] **Step 0.4: Create `requirements.txt`**

```
pandas>=2.2
rich>=13.7
questionary>=2.0
feedparser>=6.0
pytest>=8.0
```

- [ ] **Step 0.5: Create `fundexpert/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 0.6: Create `fundexpert/__main__.py`**

```python
from fundexpert.cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 0.7: Create `tests/__init__.py`** (empty file)

- [ ] **Step 0.8: Create `tests/conftest.py`**

```python
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES
```

- [ ] **Step 0.9: Verify `README.md` exists (do NOT overwrite)**

The committed `README.md` at the repo root already explains the project, points at the design docs, and describes how to bring your own CSVs into `data/`. If it is missing, recreate it from the prior commit on `main`. Otherwise leave it alone — adding setup details after the package exists is a later edit, not part of bootstrap.

- [ ] **Step 0.10: Create venv, install, verify pytest collects 0 tests**

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/pytest --collect-only
```

Expected: `0 tests collected` — confirms package imports cleanly and pytest finds the `tests/` directory.

- [ ] **Step 0.11: Stage and commit the bootstrap (NOT a first commit — `main` already has the docs commit)**

```bash
git add pyproject.toml requirements.txt fundexpert/ tests/
git commit -m "chore: bootstrap fundexpert package and test harness"
```

Push if the user wants progress visible on GitHub:

```bash
git push origin main
```

---

## Task 1: `config.py` Constants

**Files:**
- Create: `fundexpert/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1.1: Write the failing test**

Create `tests/test_config.py`:

```python
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


def test_rss_feeds_listed():
    assert isinstance(config.RSS_FEEDS, tuple)
    assert len(config.RSS_FEEDS) >= 1
    assert all(url.startswith("https://") for url in config.RSS_FEEDS)
```

- [ ] **Step 1.2: Run the test, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_config.py -v
```

Expected: ImportError or `AttributeError: module 'fundexpert' has no attribute 'config'`.

- [ ] **Step 1.3: Implement `fundexpert/config.py`**

```python
"""Tunable constants for fundexpert. One file changes calibrate everything."""

from pathlib import Path

# --- Scoring constants --------------------------------------------------------

# Low/Med/High user priorities map to scalar weights, then re-normalized in score.py
PRIORITY_WEIGHTS: dict[str, float] = {
    "low": 0.10,
    "medium": 0.30,
    "high": 0.60,
}

# λ multiplier for the SRRI risk penalty: penalty = λ · ((risk - 1)/6)²
RISK_LAMBDAS: dict[str, float] = {
    "low": 0.05,
    "medium": 0.25,
    "high": 0.60,
}

# Horizon → return columns averaged for the primary return signal
HORIZON_BUCKETS: dict[str, tuple[str, ...]] = {
    "short":  ("ret_1m", "ret_3m"),
    "medium": ("ret_6m", "ret_ytd", "ret_1y"),
    "long":   ("ret_3y", "ret_5y"),
}

# --- Selection constants ------------------------------------------------------

DEFAULT_MAX_PER_TYPE: int = 2

WEIGHT_EPSILON: float = 0.01  # shift used by select/weights.py to avoid zero weights

# --- News pass ---------------------------------------------------------------

# RSS feed URLs are NOT YET LIVE-VERIFIED. Implementer must check each at coding time.
RSS_FEEDS: tuple[str, ...] = (
    "https://bigpara.hurriyet.com.tr/rss/borsa-haberleri.xml",
    "https://www.bloomberght.com/rss",
    "https://www.dunya.com/rss?dunya=fon",
)

NEWS_CACHE_DIR: Path = Path.home() / ".fundexpert" / "news_cache"
NEWS_CACHE_TTL_SECONDS: int = 3600

# --- Paths -------------------------------------------------------------------

LAST_RUN_FILE: Path = Path.home() / ".fundexpert" / "last.json"
```

- [ ] **Step 1.4: Run the test, expect PASS**

```bash
.venv/Scripts/pytest tests/test_config.py -v
```

Expected: 6 passed.

- [ ] **Step 1.5: Commit**

```bash
git add fundexpert/config.py tests/test_config.py
git commit -m "feat(config): add tunable constants module"
```

---

## Task 2: `data/loader.py` — CSV Loading

**Files:**
- Create: `tests/fixtures/getiri_small.csv`
- Create: `tests/fixtures/buyukluk_small.csv`
- Create: `tests/fixtures/yonetim_small.csv`
- Create: `fundexpert/data/__init__.py`
- Create: `fundexpert/data/loader.py`
- Test: `tests/test_loader.py`

- [ ] **Step 2.1: Create the three fixture CSVs**

Create `tests/fixtures/getiri_small.csv` (note: 3 metadata rows, then header on row 4, then 3 data rows; one row has NaN in `5 Yıl (%)`):

```
Dışa Aktarım Tarihi:,02.05.2026 11:01:58
Toplam Kayıt Sayısı:,3

Fon Kodu,Fon Adı,Şemsiye Fon Türü,Fonun Risk Değeri,1 Ay (%),3 Ay (%),6 Ay (%),Yılbaşından İtibaren (%),1 Yıl (%),3 Yıl (%),5 Yıl (%)
AAA,ALPHA FON,Değişken Şemsiye Fonu,4,"4,50","2,30","16,20","14,10","40,20","255,60","692,75"
BBB,BETA FON,Hisse Senedi Şemsiye Fonu,6,"7,10","5,40","22,80","18,50","55,30","320,40",
CCC,GAMMA FON,Borçlanma Araçları Şemsiye Fonu,2,"1,20","0,80","4,50","3,90","12,40","60,10","180,20"
```

Create `tests/fixtures/buyukluk_small.csv`:

```
Dışa Aktarım Tarihi:,02.05.2026 11:02:13
Toplam Kayıt Sayısı:,3

Fon Kodu,Fon Adı,Şemsiye Fon Türü,İlk Portföy Büyüklüğü,Son Portföy Büyüklüğü,Portföy Büyüklüğü Değişimi (%),Tedavüldeki İlk Pay Adedi,Tedavüldeki Son Pay Adedi,Pay Adedi Değişimi (%),Getiri Oranı (%)
AAA,ALPHA FON,Değişken Fon,"36093030,50","34848271,36","-3,45","1057059,00","989575,00","-6,38","3,14"
BBB,BETA FON,Hisse Senedi Fonu,"50000000,00","60000000,00","20,00","2000000,00","2200000,00","10,00","9,09"
CCC,GAMMA FON,Borçlanma Aracı Fonu,"15000000,00","15500000,00","3,33","800000,00","810000,00","1,25","2,30"
```

Create `tests/fixtures/yonetim_small.csv`:

```
Dışa Aktarım Tarihi:,02.05.2026 11:02:04
Toplam Kayıt Sayısı:,3

Fon Kodu,Fon Adı,Şemsiye Fon Türü,Uygulanan Yönetim Ücreti Yıllık (%),Fon İç Tüzüğünde Yer Alan Yönetim Ücreti Yıllık (%),Yıllık Getiri Oranı (%),Yıllık Azami Fon Toplam Gider Oranı (%)
AAA,ALPHA FON,Değişken Şemsiye Fonu,"1,5","1,5","40,20","3,65"
BBB,BETA FON,Hisse Senedi Şemsiye Fonu,"2,0","2,0","55,30","4,50"
CCC,GAMMA FON,Borçlanma Araçları Şemsiye Fonu,"0,8","0,8","12,40","1,20"
```

- [ ] **Step 2.2: Write the failing test**

Create `tests/test_loader.py`:

```python
import math

import pandas as pd

from fundexpert.data.loader import load_universe


def test_load_universe_returns_three_frames(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    assert set(frames.keys()) == {"getiri", "buyukluk", "yonetim_ucreti"}


def test_loader_skips_metadata_rows(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    # 3 data rows, NOT the metadata header
    assert len(frames["getiri"]) == 3
    assert "fon_kodu" in frames["getiri"].columns


def test_loader_parses_turkish_decimals(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    aaa = frames["getiri"][frames["getiri"]["fon_kodu"] == "AAA"].iloc[0]
    assert aaa["ret_1m"] == 4.50
    assert aaa["risk"] == 4
    fee = frames["yonetim_ucreti"][frames["yonetim_ucreti"]["fon_kodu"] == "AAA"].iloc[0]
    assert fee["applied_management_fee_pct"] == 1.5


def test_loader_preserves_nan_in_long_returns(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    bbb = frames["getiri"][frames["getiri"]["fon_kodu"] == "BBB"].iloc[0]
    assert math.isnan(bbb["ret_5y"])
    assert bbb["ret_3y"] == 320.40


def test_loader_renames_columns_to_internal_names(fixtures_dir):
    frames = load_universe(
        getiri_path=fixtures_dir / "getiri_small.csv",
        buyukluk_path=fixtures_dir / "buyukluk_small.csv",
        yonetim_path=fixtures_dir / "yonetim_small.csv",
    )
    expected_getiri = {"fon_kodu", "fon_adi", "umbrella_type", "risk",
                       "ret_1m", "ret_3m", "ret_6m", "ret_ytd",
                       "ret_1y", "ret_3y", "ret_5y"}
    assert expected_getiri.issubset(set(frames["getiri"].columns))

    expected_buyukluk = {"fon_kodu", "aum_first", "aum_last", "aum_change_pct",
                         "units_first", "units_last", "units_change_pct"}
    assert expected_buyukluk.issubset(set(frames["buyukluk"].columns))

    expected_yonetim = {"fon_kodu", "applied_management_fee_pct",
                        "bylaw_management_fee_pct", "max_total_expense_pct"}
    assert expected_yonetim.issubset(set(frames["yonetim_ucreti"].columns))
```

- [ ] **Step 2.3: Create empty `fundexpert/data/__init__.py`**

(empty file)

- [ ] **Step 2.4: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_loader.py -v
```

Expected: ImportError on `fundexpert.data.loader`.

- [ ] **Step 2.5: Implement `fundexpert/data/loader.py`**

```python
"""Read TEFAS/BEFAS CSV exports and rename columns to internal snake_case names."""

from pathlib import Path

import pandas as pd

GETIRI_RENAME: dict[str, str] = {
    "Fon Kodu": "fon_kodu",
    "Fon Adı": "fon_adi",
    "Şemsiye Fon Türü": "umbrella_type",
    "Fonun Risk Değeri": "risk",
    "1 Ay (%)": "ret_1m",
    "3 Ay (%)": "ret_3m",
    "6 Ay (%)": "ret_6m",
    "Yılbaşından İtibaren (%)": "ret_ytd",
    "1 Yıl (%)": "ret_1y",
    "3 Yıl (%)": "ret_3y",
    "5 Yıl (%)": "ret_5y",
}

BUYUKLUK_RENAME: dict[str, str] = {
    "Fon Kodu": "fon_kodu",
    "Fon Adı": "fon_adi",
    "Şemsiye Fon Türü": "umbrella_type",
    "İlk Portföy Büyüklüğü": "aum_first",
    "Son Portföy Büyüklüğü": "aum_last",
    "Portföy Büyüklüğü Değişimi (%)": "aum_change_pct",
    "Tedavüldeki İlk Pay Adedi": "units_first",
    "Tedavüldeki Son Pay Adedi": "units_last",
    "Pay Adedi Değişimi (%)": "units_change_pct",
    # "Getiri Oranı (%)" intentionally dropped — redundant with getiri.csv
}

YONETIM_RENAME: dict[str, str] = {
    "Fon Kodu": "fon_kodu",
    "Fon Adı": "fon_adi",
    "Şemsiye Fon Türü": "umbrella_type",
    "Uygulanan Yönetim Ücreti Yıllık (%)": "applied_management_fee_pct",
    "Fon İç Tüzüğünde Yer Alan Yönetim Ücreti Yıllık (%)": "bylaw_management_fee_pct",
    # "Yıllık Getiri Oranı (%)" intentionally dropped — redundant with getiri.csv
    "Yıllık Azami Fon Toplam Gider Oranı (%)": "max_total_expense_pct",
}


def _read_one(path: Path, rename: dict[str, str]) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        skiprows=3,        # rows 0-2: export metadata; row 3: header
        encoding="utf-8",
        decimal=",",
        thousands=None,
    )
    df = df.rename(columns=rename)
    keep = [c for c in df.columns if c in rename.values()]
    return df[keep]


def load_universe(
    getiri_path: Path,
    buyukluk_path: Path,
    yonetim_path: Path,
) -> dict[str, pd.DataFrame]:
    """Load the three CSVs for a single universe (tefas or befas)."""
    return {
        "getiri":         _read_one(getiri_path,  GETIRI_RENAME),
        "buyukluk":       _read_one(buyukluk_path, BUYUKLUK_RENAME),
        "yonetim_ucreti": _read_one(yonetim_path,  YONETIM_RENAME),
    }
```

- [ ] **Step 2.6: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_loader.py -v
```

Expected: 5 passed.

- [ ] **Step 2.7: Commit**

```bash
git add fundexpert/data/__init__.py fundexpert/data/loader.py tests/test_loader.py tests/fixtures/
git commit -m "feat(data): load TEFAS/BEFAS CSVs with TR locale handling"
```

---

## Task 3: `data/merge.py` — Inner Join + Universe

**Files:**
- Create: `fundexpert/data/merge.py`
- Test: `tests/test_merge.py`

- [ ] **Step 3.1: Write the failing test**

Create `tests/test_merge.py`:

```python
import pandas as pd
import pytest

from fundexpert.data.merge import merge_universe, merge_universes


@pytest.fixture
def small_frames():
    getiri = pd.DataFrame({
        "fon_kodu": ["AAA", "BBB", "CCC"],
        "fon_adi":  ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borç"],
        "risk":   [4, 6, 2],
        "ret_1m": [4.5, 7.1, 1.2],
        "ret_3m": [2.3, 5.4, 0.8],
        "ret_6m": [16.2, 22.8, 4.5],
        "ret_ytd":[14.1, 18.5, 3.9],
        "ret_1y": [40.2, 55.3, 12.4],
        "ret_3y": [255.6, 320.4, 60.1],
        "ret_5y": [692.75, float("nan"), 180.20],
    })
    buyukluk = pd.DataFrame({
        "fon_kodu": ["AAA", "BBB", "CCC"],
        "fon_adi":  ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borç"],
        "aum_first":  [36e6, 50e6, 15e6],
        "aum_last":   [34.8e6, 60e6, 15.5e6],
        "aum_change_pct":   [-3.45, 20.0, 3.33],
        "units_first":      [1057059, 2e6, 8e5],
        "units_last":       [989575, 2.2e6, 8.1e5],
        "units_change_pct": [-6.38, 10.0, 1.25],
    })
    yonetim = pd.DataFrame({
        "fon_kodu": ["AAA", "BBB", "CCC"],
        "fon_adi":  ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borç"],
        "applied_management_fee_pct": [1.5, 2.0, 0.8],
        "bylaw_management_fee_pct":   [1.5, 2.0, 0.8],
        "max_total_expense_pct":      [3.65, 4.50, 1.20],
    })
    return {"getiri": getiri, "buyukluk": buyukluk, "yonetim_ucreti": yonetim}


def test_merge_universe_inner_joins_on_fon_kodu(small_frames):
    df = merge_universe(small_frames, universe="tefas")
    assert len(df) == 3
    assert set(df["fon_kodu"]) == {"AAA", "BBB", "CCC"}


def test_merge_universe_adds_universe_column(small_frames):
    df = merge_universe(small_frames, universe="tefas")
    assert (df["universe"] == "tefas").all()


def test_merge_universe_includes_all_internal_columns(small_frames):
    df = merge_universe(small_frames, universe="tefas")
    expected = {"fon_kodu", "fon_adi", "umbrella_type", "risk",
                "ret_1m", "ret_3m", "ret_6m", "ret_ytd", "ret_1y", "ret_3y", "ret_5y",
                "aum_change_pct", "applied_management_fee_pct",
                "max_total_expense_pct", "universe"}
    assert expected.issubset(set(df.columns))


def test_merge_universe_drops_funds_missing_in_one_file(small_frames):
    # Remove BBB from yonetim
    small_frames["yonetim_ucreti"] = small_frames["yonetim_ucreti"][
        small_frames["yonetim_ucreti"]["fon_kodu"] != "BBB"
    ]
    df = merge_universe(small_frames, universe="tefas")
    assert set(df["fon_kodu"]) == {"AAA", "CCC"}


def test_merge_universes_concatenates_disjoint_universes(small_frames):
    tefas = merge_universe(small_frames, universe="tefas")

    befas_frames = {
        k: v.assign(fon_kodu=v["fon_kodu"] + "X")
        for k, v in small_frames.items()
    }
    befas = merge_universe(befas_frames, universe="befas")

    combined = merge_universes([tefas, befas])
    assert len(combined) == 6
    assert set(combined["universe"]) == {"tefas", "befas"}
```

- [ ] **Step 3.2: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_merge.py -v
```

Expected: ImportError on `fundexpert.data.merge`.

- [ ] **Step 3.3: Implement `fundexpert/data/merge.py`**

```python
"""Join the three loaded frames per universe into one fund-per-row DataFrame."""

import pandas as pd


def merge_universe(frames: dict[str, pd.DataFrame], universe: str) -> pd.DataFrame:
    """Inner-join getiri + buyukluk + yonetim_ucreti on fon_kodu."""
    getiri = frames["getiri"]
    buyukluk = frames["buyukluk"]
    yonetim = frames["yonetim_ucreti"]

    # Drop duplicated identity columns from buyukluk and yonetim before merge
    buyukluk_keep = buyukluk.drop(columns=[c for c in ("fon_adi", "umbrella_type") if c in buyukluk.columns])
    yonetim_keep = yonetim.drop(columns=[c for c in ("fon_adi", "umbrella_type") if c in yonetim.columns])

    df = getiri.merge(buyukluk_keep, on="fon_kodu", how="inner")
    df = df.merge(yonetim_keep, on="fon_kodu", how="inner")
    df["universe"] = universe
    return df


def merge_universes(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Concatenate already-merged universe frames (TEFAS + BEFAS codes are disjoint)."""
    return pd.concat(frames, ignore_index=True)
```

- [ ] **Step 3.4: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_merge.py -v
```

Expected: 5 passed.

- [ ] **Step 3.5: Commit**

```bash
git add fundexpert/data/merge.py tests/test_merge.py
git commit -m "feat(data): merge three frames per universe and concat universes"
```

---

## Task 4: `scoring/horizon.py` — Bucket Mapping

**Files:**
- Create: `fundexpert/scoring/__init__.py`
- Create: `fundexpert/scoring/horizon.py`
- Test: `tests/test_horizon.py`

- [ ] **Step 4.1: Write the failing test**

Create `tests/test_horizon.py`:

```python
import math

import pandas as pd
import pytest

from fundexpert.scoring.horizon import apply_horizon


@pytest.fixture
def candidates():
    return pd.DataFrame({
        "fon_kodu": ["A", "B", "C", "D"],
        "ret_1m":  [4.0,  6.0, 2.0,  float("nan")],
        "ret_3m":  [2.0,  4.0, 1.0,  float("nan")],
        "ret_6m":  [10.0, 12.0, 5.0, 8.0],
        "ret_ytd": [14.0, 16.0, 7.0, 9.0],
        "ret_1y":  [40.0, 50.0, 15.0, 20.0],
        "ret_3y":  [200.0, 300.0, float("nan"), 100.0],
        "ret_5y":  [600.0, float("nan"), float("nan"), 200.0],
    })


def test_short_horizon_uses_1m_and_3m(candidates):
    out = apply_horizon(candidates, "short")
    assert out.loc[out["fon_kodu"] == "A", "R"].iloc[0] == 3.0  # mean(4,2)


def test_medium_horizon_uses_6m_ytd_1y(candidates):
    out = apply_horizon(candidates, "medium")
    expected_b = (12.0 + 16.0 + 50.0) / 3
    assert out.loc[out["fon_kodu"] == "B", "R"].iloc[0] == pytest.approx(expected_b)


def test_long_horizon_takes_mean_when_one_nan(candidates):
    # B has 3y=300, 5y=NaN → bucket mean = 300
    out = apply_horizon(candidates, "long")
    assert out.loc[out["fon_kodu"] == "B", "R"].iloc[0] == 300.0


def test_long_horizon_excludes_fund_with_all_bucket_nans(candidates):
    # C has 3y=NaN, 5y=NaN → excluded
    out = apply_horizon(candidates, "long")
    assert "C" not in out["fon_kodu"].values


def test_short_horizon_excludes_fund_with_all_bucket_nans(candidates):
    # D has 1m=NaN, 3m=NaN → excluded
    out = apply_horizon(candidates, "short")
    assert "D" not in out["fon_kodu"].values


def test_excluded_count_returned():
    df = pd.DataFrame({
        "fon_kodu": ["X", "Y"],
        "ret_3y": [float("nan"), 10.0],
        "ret_5y": [float("nan"), 20.0],
    })
    out = apply_horizon(df, "long")
    assert out.attrs["excluded_count"] == 1
```

- [ ] **Step 4.2: Create empty `fundexpert/scoring/__init__.py`**

(empty file)

- [ ] **Step 4.3: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_horizon.py -v
```

Expected: ImportError on `fundexpert.scoring.horizon`.

- [ ] **Step 4.4: Implement `fundexpert/scoring/horizon.py`**

```python
"""Map user-chosen horizon to a single mean-return signal column R."""

import pandas as pd

from fundexpert.config import HORIZON_BUCKETS


def apply_horizon(df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    """Add column `R` = mean of horizon-bucket return columns; drop all-NaN rows.

    `df.attrs["excluded_count"]` is set to the number of rows dropped.
    """
    cols = list(HORIZON_BUCKETS[horizon])
    R = df[cols].mean(axis=1, skipna=True)
    keep_mask = R.notna()
    out = df.loc[keep_mask].copy()
    out["R"] = R[keep_mask]
    out.attrs["excluded_count"] = int((~keep_mask).sum())
    return out
```

- [ ] **Step 4.5: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_horizon.py -v
```

Expected: 6 passed.

- [ ] **Step 4.6: Commit**

```bash
git add fundexpert/scoring/__init__.py fundexpert/scoring/horizon.py tests/test_horizon.py
git commit -m "feat(scoring): map horizon to mean return signal R"
```

---

## Task 5: `scoring/normalize.py` — Min-Max Scaling

**Files:**
- Create: `fundexpert/scoring/normalize.py`
- Test: `tests/test_normalize.py`

- [ ] **Step 5.1: Write the failing test**

Create `tests/test_normalize.py`:

```python
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
```

- [ ] **Step 5.2: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_normalize.py -v
```

Expected: ImportError on `fundexpert.scoring.normalize`.

- [ ] **Step 5.3: Implement `fundexpert/scoring/normalize.py`**

```python
"""Per-column min-max scaling with constant-range and NaN guards."""

import pandas as pd


def minmax_normalize(series: pd.Series) -> pd.Series:
    """Scale a numeric series to [0, 1].

    - Constant columns (max == min) return 0.5 everywhere (neutral).
    - NaN values become 0.5 (neutral contribution).
    """
    s = series.astype(float)
    finite = s.dropna()
    if len(finite) == 0:
        return pd.Series([0.5] * len(s), index=s.index)

    lo, hi = finite.min(), finite.max()
    if hi == lo:
        return pd.Series([0.5] * len(s), index=s.index)

    out = (s - lo) / (hi - lo)
    return out.fillna(0.5)
```

- [ ] **Step 5.4: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_normalize.py -v
```

Expected: 4 passed.

- [ ] **Step 5.5: Commit**

```bash
git add fundexpert/scoring/normalize.py tests/test_normalize.py
git commit -m "feat(scoring): min-max normalize with constant and NaN guards"
```

---

## Task 6: `scoring/score.py` — Weighted Sum + Risk Penalty

**Files:**
- Create: `fundexpert/scoring/score.py`
- Test: `tests/test_score.py`

- [ ] **Step 6.1: Write the failing test**

Create `tests/test_score.py`:

```python
import pandas as pd
import pytest

from fundexpert.scoring.score import score_candidates


@pytest.fixture
def horizon_ready():
    # 3 funds, R already applied; aum/fee/risk varied
    return pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "umbrella_type": ["X", "Y", "Z"],
        "R":                          [10.0, 30.0, 20.0],
        "aum_change_pct":             [5.0, -2.0, 8.0],
        "applied_management_fee_pct": [1.0, 2.0, 0.5],
        "risk":                       [3, 6, 2],
    })


def test_score_returns_score_column(horizon_ready):
    out = score_candidates(horizon_ready,
                           volume_priority="medium",
                           fee_priority="medium",
                           risk_priority="medium")
    assert "score" in out.columns
    assert len(out) == 3


def test_higher_R_with_equal_other_features_scores_higher():
    df = pd.DataFrame({
        "fon_kodu": ["LO", "HI"],
        "umbrella_type": ["X", "X"],
        "R":                          [10.0, 50.0],
        "aum_change_pct":             [0.0, 0.0],
        "applied_management_fee_pct": [1.0, 1.0],
        "risk":                       [3, 3],
    })
    out = score_candidates(df, "medium", "medium", "medium")
    hi = out.loc[out["fon_kodu"] == "HI", "score"].iloc[0]
    lo = out.loc[out["fon_kodu"] == "LO", "score"].iloc[0]
    assert hi > lo


def test_higher_risk_loses_score_under_high_risk_priority():
    df = pd.DataFrame({
        "fon_kodu": ["L", "H"],
        "umbrella_type": ["X", "X"],
        "R":                          [10.0, 10.0],
        "aum_change_pct":             [0.0, 0.0],
        "applied_management_fee_pct": [1.0, 1.0],
        "risk":                       [1, 7],
    })
    out = score_candidates(df, "medium", "medium", risk_priority="high")
    low_risk = out.loc[out["fon_kodu"] == "L", "score"].iloc[0]
    high_risk = out.loc[out["fon_kodu"] == "H", "score"].iloc[0]
    # SRRI 1 → penalty=0; SRRI 7 → penalty=0.60
    assert low_risk > high_risk
    assert pytest.approx(low_risk - high_risk, abs=1e-6) == 0.60


def test_lower_fee_scores_higher(horizon_ready):
    out = score_candidates(horizon_ready, "medium", "high", "low")
    out_sorted = out.sort_values("score", ascending=False)
    # C has lowest fee, highest R/AUM → should rank first
    assert out_sorted.iloc[0]["fon_kodu"] == "C"


def test_breakdown_dict_per_fund(horizon_ready):
    out = score_candidates(horizon_ready, "medium", "medium", "medium")
    assert "_breakdown" in out.columns
    bd = out.iloc[0]["_breakdown"]
    assert set(bd.keys()) == {"base_score", "R_contrib", "V_contrib",
                              "F_contrib", "risk_penalty", "score"}
```

- [ ] **Step 6.2: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_score.py -v
```

Expected: ImportError on `fundexpert.scoring.score`.

- [ ] **Step 6.3: Implement `fundexpert/scoring/score.py`**

```python
"""Compute per-fund score = base_score (weighted, normalized) − risk_penalty (SRRI λ)."""

import pandas as pd

from fundexpert.config import PRIORITY_WEIGHTS, RISK_LAMBDAS
from fundexpert.scoring.normalize import minmax_normalize


def score_candidates(
    df: pd.DataFrame,
    volume_priority: str,
    fee_priority: str,
    risk_priority: str,
) -> pd.DataFrame:
    """Add `score` and `_breakdown` columns. Input must already have `R` (from horizon)."""
    out = df.copy()

    # Normalize the three signals
    R_hat = minmax_normalize(out["R"])
    V_hat = minmax_normalize(out["aum_change_pct"])
    F_hat = minmax_normalize(out["applied_management_fee_pct"])

    # Priority → renormalized weights summing to 1.0
    w_return = 1.0
    w_volume = PRIORITY_WEIGHTS[volume_priority]
    w_fee    = PRIORITY_WEIGHTS[fee_priority]
    total = w_return + w_volume + w_fee
    w_return /= total
    w_volume /= total
    w_fee    /= total

    R_contrib = w_return * R_hat
    V_contrib = w_volume * V_hat
    F_contrib = w_fee * (1 - F_hat)
    base_score = R_contrib + V_contrib + F_contrib

    lam = RISK_LAMBDAS[risk_priority]
    risk_norm = (out["risk"].astype(float) - 1.0) / 6.0
    risk_penalty = lam * (risk_norm ** 2)

    score = base_score - risk_penalty
    out["score"] = score

    out["_breakdown"] = [
        {
            "base_score":   float(b),
            "R_contrib":    float(r),
            "V_contrib":    float(v),
            "F_contrib":    float(f),
            "risk_penalty": float(p),
            "score":        float(s),
        }
        for b, r, v, f, p, s in zip(base_score, R_contrib, V_contrib, F_contrib, risk_penalty, score)
    ]
    return out
```

- [ ] **Step 6.4: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_score.py -v
```

Expected: 5 passed.

- [ ] **Step 6.5: Commit**

```bash
git add fundexpert/scoring/score.py tests/test_score.py
git commit -m "feat(scoring): weighted-sum score with SRRI soft penalty"
```

---

## Task 7: `select/pick.py` — Top-N with Umbrella Cap

**Files:**
- Create: `fundexpert/select/__init__.py`
- Create: `fundexpert/select/pick.py`
- Test: `tests/test_pick.py`

- [ ] **Step 7.1: Write the failing test**

Create `tests/test_pick.py`:

```python
import pandas as pd
import pytest

from fundexpert.select.pick import pick_top


@pytest.fixture
def scored():
    return pd.DataFrame({
        "fon_kodu":      ["A", "B", "C", "D", "E", "F"],
        "umbrella_type": ["X", "X", "X", "Y", "Y", "Z"],
        "score":         [0.9, 0.85, 0.8, 0.7, 0.6, 0.5],
    })


def test_pick_top_returns_n_when_cap_allows(scored):
    out, warning = pick_top(scored, n=3, max_per_type=2)
    assert list(out["fon_kodu"]) == ["A", "B", "D"]
    assert warning is None


def test_pick_top_respects_cap_and_skips_capped_types(scored):
    out, warning = pick_top(scored, n=4, max_per_type=2)
    assert list(out["fon_kodu"]) == ["A", "B", "D", "E"]
    assert warning is None


def test_pick_top_returns_partial_with_warning_when_cap_blocks(scored):
    # max_per_type=1 → can pick at most 3 (one each X, Y, Z)
    out, warning = pick_top(scored, n=5, max_per_type=1)
    assert list(out["fon_kodu"]) == ["A", "D", "F"]
    assert warning is not None
    assert "3 of requested 5" in warning


def test_pick_top_returns_empty_when_pool_empty():
    empty = pd.DataFrame(columns=["fon_kodu", "umbrella_type", "score"])
    out, warning = pick_top(empty, n=3, max_per_type=2)
    assert len(out) == 0
    assert warning is not None
```

- [ ] **Step 7.2: Create empty `fundexpert/select/__init__.py`**

(empty file)

- [ ] **Step 7.3: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_pick.py -v
```

Expected: ImportError on `fundexpert.select.pick`.

- [ ] **Step 7.4: Implement `fundexpert/select/pick.py`**

```python
"""Top-N selection with a per-umbrella-type cap, never silently relaxed."""

import pandas as pd


def pick_top(
    scored: pd.DataFrame,
    n: int,
    max_per_type: int,
) -> tuple[pd.DataFrame, str | None]:
    """Return (selected_rows, warning_or_None).

    Walks scored rows in descending score order, skipping any whose umbrella_type
    is already at the cap. Stops at N picks or when the pool is exhausted.
    """
    sorted_df = scored.sort_values("score", ascending=False)
    counts: dict[str, int] = {}
    selected_indices: list = []

    for idx, row in sorted_df.iterrows():
        if len(selected_indices) >= n:
            break
        utype = row["umbrella_type"]
        if counts.get(utype, 0) >= max_per_type:
            continue
        selected_indices.append(idx)
        counts[utype] = counts.get(utype, 0) + 1

    out = sorted_df.loc[selected_indices].reset_index(drop=True)

    if len(out) < n:
        if len(out) == 0:
            warning = "Aday havuzu boş — portföy oluşturulamadı."
        else:
            warning = (
                f"Picked {len(out)} of requested {n} — "
                f"no further fund of a different umbrella type qualified."
            )
        return out, warning
    return out, None
```

- [ ] **Step 7.5: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_pick.py -v
```

Expected: 4 passed.

- [ ] **Step 7.6: Commit**

```bash
git add fundexpert/select/__init__.py fundexpert/select/pick.py tests/test_pick.py
git commit -m "feat(select): top-N picker with umbrella-type cap and up-to-N semantics"
```

---

## Task 8: `select/weights.py` — ε-Shifted Score-Proportional Weights

**Files:**
- Create: `fundexpert/select/weights.py`
- Test: `tests/test_weights.py`

- [ ] **Step 8.1: Write the failing test**

Create `tests/test_weights.py`:

```python
import pandas as pd
import pytest

from fundexpert.select.weights import compute_weights


def test_positive_scores_proportional():
    df = pd.DataFrame({"fon_kodu": ["A", "B", "C"], "score": [0.9, 0.6, 0.3]})
    out = compute_weights(df)
    weights = out["display_weight_pct"].tolist()
    assert sum(weights) == pytest.approx(100.0)
    # Highest score gets the highest weight
    assert weights[0] > weights[1] > weights[2]


def test_negative_score_still_gets_nonzero_weight():
    df = pd.DataFrame({"fon_kodu": ["A", "B"], "score": [0.5, -0.2]})
    out = compute_weights(df)
    assert (out["display_weight_pct"] > 0).all()
    assert sum(out["display_weight_pct"]) == pytest.approx(100.0)


def test_equal_scores_yield_equal_weights():
    df = pd.DataFrame({"fon_kodu": ["A", "B", "C"], "score": [0.5, 0.5, 0.5]})
    out = compute_weights(df)
    assert out["display_weight_pct"].tolist() == [pytest.approx(33.3), pytest.approx(33.3), pytest.approx(33.4)]
    assert sum(out["display_weight_pct"]) == pytest.approx(100.0)


def test_single_fund_gets_full_weight():
    df = pd.DataFrame({"fon_kodu": ["A"], "score": [0.7]})
    out = compute_weights(df)
    assert out["display_weight_pct"].iloc[0] == 100.0
```

- [ ] **Step 8.2: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_weights.py -v
```

Expected: ImportError on `fundexpert.select.weights`.

- [ ] **Step 8.3: Implement `fundexpert/select/weights.py`**

```python
"""ε-shifted score-proportional weights, with rounding reconciliation to sum=100.0."""

import pandas as pd

from fundexpert.config import WEIGHT_EPSILON


def compute_weights(selected: pd.DataFrame) -> pd.DataFrame:
    """Add `display_weight_pct` column. Sum is exactly 100.0 after rounding."""
    out = selected.copy()
    if len(out) == 0:
        out["display_weight_pct"] = pd.Series(dtype=float)
        return out

    scores = out["score"].astype(float)
    shifted = scores - scores.min() + WEIGHT_EPSILON
    raw_weight = shifted / shifted.sum()
    display = (raw_weight * 100).round(1)

    delta = round(100.0 - display.sum(), 1)
    if delta != 0.0:
        # Add the delta to the largest weight so the displayed total is exactly 100.0
        idx_max = display.idxmax()
        display.loc[idx_max] = round(display.loc[idx_max] + delta, 1)

    out["display_weight_pct"] = display
    return out
```

- [ ] **Step 8.4: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_weights.py -v
```

Expected: 4 passed.

- [ ] **Step 8.5: Commit**

```bash
git add fundexpert/select/weights.py tests/test_weights.py
git commit -m "feat(select): epsilon-shifted score-proportional weights summing to 100"
```

---

## Task 9: `render/table.py` — Pretty Table

**Files:**
- Create: `fundexpert/render/__init__.py`
- Create: `fundexpert/render/table.py`
- Test: `tests/test_render.py`

- [ ] **Step 9.1: Write the failing test**

Create `tests/test_render.py`:

```python
from datetime import datetime

import pandas as pd

from fundexpert.render.table import render_portfolio


def _selected():
    return pd.DataFrame({
        "fon_kodu": ["AAA", "BBB"],
        "fon_adi":  ["ATA PORTFÖY ÇOKLU VARLIK FON", "BETA PORTFÖY HİSSE FON"],
        "umbrella_type": ["Değişken", "Hisse Senedi"],
        "risk":          [4, 6],
        "display_weight_pct": [60.0, 40.0],
        "score":         [0.71, 0.55],
    })


def _header():
    return {
        "timestamp": datetime(2026, 5, 2, 11, 42),
        "universe":  "tefas+befas",
        "candidate_total": 1308,
        "candidate_kept":  1107,
        "horizon": "long",
        "risk_priority": "high",
        "volume_priority": "medium",
        "fee_priority": "high",
        "n": 5,
    }


def test_render_includes_fund_codes(capsys):
    render_portfolio(_selected(), _header(), news=None)
    captured = capsys.readouterr()
    assert "AAA" in captured.out
    assert "BBB" in captured.out


def test_render_includes_total_row(capsys):
    render_portfolio(_selected(), _header(), news=None)
    captured = capsys.readouterr()
    assert "Toplam" in captured.out
    assert "100.0" in captured.out


def test_render_includes_horizon_and_priorities(capsys):
    render_portfolio(_selected(), _header(), news=None)
    captured = capsys.readouterr()
    assert "long" in captured.out.lower() or "Long" in captured.out
    assert "1308" in captured.out
    assert "1107" in captured.out


def test_render_includes_news_footer_when_provided(capsys):
    news = {"AAA": [{"title": "Yeni fon ihracı", "url": "https://x", "source": "bigpara"}]}
    render_portfolio(_selected(), _header(), news=news)
    captured = capsys.readouterr()
    assert "Haberler" in captured.out
    assert "Yeni fon ihracı" in captured.out


def test_render_omits_news_section_when_no_hits(capsys):
    render_portfolio(_selected(), _header(), news={})
    captured = capsys.readouterr()
    assert "Haberler" not in captured.out
```

- [ ] **Step 9.2: Create empty `fundexpert/render/__init__.py`**

(empty file)

- [ ] **Step 9.3: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_render.py -v
```

Expected: ImportError on `fundexpert.render.table`.

- [ ] **Step 9.4: Implement `fundexpert/render/table.py`**

```python
"""Render the selected portfolio as a rich table on stdout."""

from datetime import datetime
from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table


def render_portfolio(
    selected: pd.DataFrame,
    header: dict[str, Any],
    news: dict[str, list[dict[str, Any]]] | None,
) -> None:
    """Print header block + table + (optional) news footer to stdout.

    `news` maps fon_kodu → list of {title, url, source, published?}. If empty
    or None, the news footer is omitted.
    """
    console = Console()

    ts = header["timestamp"].strftime("%Y-%m-%d %H:%M")
    console.print(f"[bold]Fund Expert — {ts}[/bold]")
    console.print(
        f"Evren: {header['universe']} ({header['candidate_total']} fon)  •  "
        f"Vade: {header['horizon']}  •  Risk önc.: {header['risk_priority']}"
    )
    console.print(
        f"Hacim önc.: {header['volume_priority']}  •  "
        f"Ücret önc.: {header['fee_priority']}  •  N={header['n']}"
    )
    console.print(
        f"Aday havuzu: {header['candidate_total']} → {header['candidate_kept']} "
        f"(NaN filtreleri sonrası)"
    )

    table = Table(show_header=True, header_style="bold")
    table.add_column("Fon Kodu")
    table.add_column("Fon Adı")
    table.add_column("Şemsiye")
    table.add_column("Risk", justify="right")
    table.add_column("Ağırlık %", justify="right")
    table.add_column("Skor", justify="right")

    for _, r in selected.iterrows():
        table.add_row(
            str(r["fon_kodu"]),
            str(r["fon_adi"]),
            str(r["umbrella_type"]),
            str(int(r["risk"])),
            f"{r['display_weight_pct']:.1f}",
            f"{r['score']:.2f}",
        )
    total_weight = selected["display_weight_pct"].sum() if len(selected) else 0.0
    table.add_row("", "", "", "[bold]Toplam[/bold]", f"[bold]{total_weight:.1f}[/bold]", "")
    console.print(table)

    if news:
        console.print("\n[bold]Haberler:[/bold]")
        for code, items in news.items():
            for item in items:
                published = f", {item['published']:%Y-%m-%d}" if item.get("published") else ""
                console.print(f"  {code} — \"{item['title']}\"  ({item['source']}{published})")
                console.print(f"        {item['url']}")
```

- [ ] **Step 9.5: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_render.py -v
```

Expected: 5 passed.

- [ ] **Step 9.6: Commit**

```bash
git add fundexpert/render/__init__.py fundexpert/render/table.py tests/test_render.py
git commit -m "feat(render): rich table with header block and optional news footer"
```

---

## Task 10: `cli.py` — Prompts + Pipeline (no `--news` yet)

**Files:**
- Create: `fundexpert/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 10.1: Write the failing test**

Create `tests/test_cli.py`:

```python
from datetime import datetime
from unittest.mock import patch

import pandas as pd
import pytest

from fundexpert.cli import run_pipeline


@pytest.fixture
def fake_universe_loader():
    """Patch loaders so cli.run_pipeline doesn't read the filesystem."""
    getiri = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "fon_adi":  ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borçlanma"],
        "risk": [3, 6, 2],
        "ret_1m": [4.0, 7.0, 1.0],
        "ret_3m": [2.0, 5.0, 0.5],
        "ret_6m": [10.0, 20.0, 4.0],
        "ret_ytd":[14.0, 18.0, 3.0],
        "ret_1y": [40.0, 55.0, 12.0],
        "ret_3y": [200.0, 300.0, 60.0],
        "ret_5y": [600.0, 700.0, 180.0],
    })
    buyukluk = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "fon_adi": ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borçlanma"],
        "aum_first": [1, 1, 1], "aum_last": [1, 1, 1],
        "aum_change_pct": [5.0, -2.0, 8.0],
        "units_first": [1, 1, 1], "units_last": [1, 1, 1],
        "units_change_pct": [0, 0, 0],
    })
    yonetim = pd.DataFrame({
        "fon_kodu": ["A", "B", "C"],
        "fon_adi": ["A FON", "B FON", "C FON"],
        "umbrella_type": ["Değişken", "Hisse", "Borçlanma"],
        "applied_management_fee_pct": [1.0, 2.0, 0.5],
        "bylaw_management_fee_pct": [1.0, 2.0, 0.5],
        "max_total_expense_pct": [3.0, 4.0, 1.5],
    })
    frames = {"getiri": getiri, "buyukluk": buyukluk, "yonetim_ucreti": yonetim}
    with patch("fundexpert.cli.load_universe", return_value=frames):
        yield


def test_run_pipeline_returns_selected_with_weights(fake_universe_loader):
    selected, header = run_pipeline(
        universe="tefas",
        risk_priority="medium",
        horizon="medium",
        volume_priority="medium",
        fee_priority="medium",
        n=2,
        max_per_type=2,
        now=datetime(2026, 5, 2, 11, 42),
    )
    assert len(selected) == 2
    assert "display_weight_pct" in selected.columns
    assert sum(selected["display_weight_pct"]) == pytest.approx(100.0)
    assert header["candidate_total"] == 3
```

- [ ] **Step 10.2: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_cli.py -v
```

Expected: ImportError on `fundexpert.cli` or attribute missing.

- [ ] **Step 10.3: Implement `fundexpert/cli.py`**

```python
"""Top-level CLI: prompts → run_pipeline → render."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from fundexpert.config import (
    DEFAULT_MAX_PER_TYPE,
    LAST_RUN_FILE,
)
from fundexpert.data.loader import load_universe
from fundexpert.data.merge import merge_universe, merge_universes
from fundexpert.render.table import render_portfolio
from fundexpert.scoring.horizon import apply_horizon
from fundexpert.scoring.score import score_candidates
from fundexpert.select.pick import pick_top
from fundexpert.select.weights import compute_weights

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"


def _load_combined(universe: str) -> pd.DataFrame:
    """Load and merge one or both universes into a single candidate frame."""
    parts: list[pd.DataFrame] = []
    universes = ["tefas", "befas"] if universe == "both" else [universe]
    for u in universes:
        folder = DATA_ROOT / u
        frames = load_universe(
            getiri_path=folder / "getiri.csv",
            buyukluk_path=folder / "buyukluk.csv",
            yonetim_path=folder / "yonetim ucreti.csv",
        )
        parts.append(merge_universe(frames, universe=u))
    return merge_universes(parts) if len(parts) > 1 else parts[0]


def run_pipeline(
    universe: str,
    risk_priority: str,
    horizon: str,
    volume_priority: str,
    fee_priority: str,
    n: int,
    max_per_type: int,
    now: datetime,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run the full data → score → select pipeline. Returns (selected, header)."""
    candidates = _load_combined(universe)
    total = len(candidates)

    # Filter out funds missing primary fee (per missing-value policy)
    candidates = candidates[candidates["applied_management_fee_pct"].notna()]

    horizoned = apply_horizon(candidates, horizon)
    excluded_horizon = horizoned.attrs.get("excluded_count", 0)

    scored = score_candidates(
        horizoned,
        volume_priority=volume_priority,
        fee_priority=fee_priority,
        risk_priority=risk_priority,
    )
    selected, warning = pick_top(scored, n=n, max_per_type=max_per_type)
    weighted = compute_weights(selected)

    header = {
        "timestamp": now,
        "universe":  universe,
        "candidate_total": total,
        "candidate_kept":  len(horizoned),
        "horizon":  horizon,
        "risk_priority": risk_priority,
        "volume_priority": volume_priority,
        "fee_priority": fee_priority,
        "n": n,
        "warning": warning,
        "excluded_horizon": excluded_horizon,
    }
    return weighted, header


# --- Prompt layer (Turkish) -------------------------------------------------

UNIVERSE_CHOICES = ["tefas", "befas", "both"]
PRIORITY_CHOICES = ["low", "medium", "high"]
HORIZON_CHOICES = ["short", "medium", "long"]


def _load_last_run() -> dict[str, Any]:
    if not LAST_RUN_FILE.exists():
        return {}
    try:
        return json.loads(LAST_RUN_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_last_run(answers: dict[str, Any]) -> None:
    try:
        LAST_RUN_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_RUN_FILE.write_text(json.dumps(answers, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass  # quality-of-life only — never fail the run on cache write errors


def _prompt(last: dict[str, Any]) -> dict[str, Any]:
    import questionary

    universe = questionary.select(
        "Fon evreni:", choices=UNIVERSE_CHOICES,
        default=last.get("universe", "tefas"),
    ).ask()

    risk_priority = questionary.select(
        "Risk önceliği (yüksek = riskten kaçınma):",
        choices=PRIORITY_CHOICES, default=last.get("risk_priority", "medium"),
    ).ask()

    horizon = questionary.select(
        "Yatırım vadesi:",
        choices=HORIZON_CHOICES, default=last.get("horizon", "medium"),
    ).ask()

    volume_priority = questionary.select(
        "Hacim değişimi önceliği:",
        choices=PRIORITY_CHOICES, default=last.get("volume_priority", "medium"),
    ).ask()

    fee_priority = questionary.select(
        "Yönetim ücreti önceliği:",
        choices=PRIORITY_CHOICES, default=last.get("fee_priority", "medium"),
    ).ask()

    n_raw = questionary.text(
        "Kaç fon istiyorsun (1-20)?",
        default=str(last.get("n", 5)),
        validate=lambda v: v.isdigit() and 1 <= int(v) <= 20,
    ).ask()

    return {
        "universe": universe,
        "risk_priority": risk_priority,
        "horizon": horizon,
        "volume_priority": volume_priority,
        "fee_priority": fee_priority,
        "n": int(n_raw),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="fundexpert")
    parser.add_argument("--news", action="store_true", help="Annotate picks with RSS headlines")
    parser.add_argument("--max-per-type", type=int, default=DEFAULT_MAX_PER_TYPE,
                        help="Max funds per Şemsiye Fon Türü")
    args = parser.parse_args()

    last = _load_last_run()
    answers = _prompt(last)
    _save_last_run(answers)

    selected, header = run_pipeline(
        universe=answers["universe"],
        risk_priority=answers["risk_priority"],
        horizon=answers["horizon"],
        volume_priority=answers["volume_priority"],
        fee_priority=answers["fee_priority"],
        n=answers["n"],
        max_per_type=args.max_per_type,
        now=datetime.now(),
    )

    if header.get("warning"):
        print(f"Uyarı: {header['warning']}", file=sys.stderr)

    render_portfolio(selected, header, news=None)
    return 0
```

- [ ] **Step 10.4: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_cli.py -v
```

Expected: 1 passed.

- [ ] **Step 10.5: Commit**

```bash
git add fundexpert/cli.py tests/test_cli.py
git commit -m "feat(cli): interactive prompts and pipeline orchestration (no news yet)"
```

---

## Task 11: `news/rss.py` — RSS Fetching, Caching, Matching

**Files:**
- Create: `tests/fixtures/rss_sample.xml`
- Create: `fundexpert/news/__init__.py`
- Create: `fundexpert/news/rss.py`
- Test: `tests/test_rss.py`

- [ ] **Step 11.1: Create the RSS fixture**

Create `tests/fixtures/rss_sample.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>BigPara Borsa Haberleri</title>
    <link>https://bigpara.hurriyet.com.tr/</link>
    <description>Borsa haberleri</description>
    <item>
      <title>ATA PORTFÖY yeni fon ihraç etti</title>
      <link>https://example.com/ata-portfoy-yeni-fon</link>
      <pubDate>Tue, 28 Apr 2026 10:00:00 +0300</pubDate>
      <description>ATA Portföy yeni bir değişken fon ihraç etti.</description>
    </item>
    <item>
      <title>Borsa İstanbul günü yükselişle kapattı</title>
      <link>https://example.com/borsa-yukselis</link>
      <pubDate>Mon, 27 Apr 2026 17:00:00 +0300</pubDate>
      <description>BIST 100 endeksi yüzde 1.5 yükselişle günü tamamladı.</description>
    </item>
    <item>
      <title>BETA PORTFÖY yönetim değişikliği</title>
      <link>https://example.com/beta-yonetim</link>
      <pubDate>Sun, 26 Apr 2026 09:00:00 +0300</pubDate>
      <description>Beta Portföy genel müdür ataması yaptı.</description>
    </item>
  </channel>
</rss>
```

- [ ] **Step 11.2: Write the failing test**

Create `tests/test_rss.py`:

```python
from datetime import datetime
from unittest.mock import patch

import pandas as pd

from fundexpert.news.rss import (
    extract_company_prefix,
    fetch_feed_text,
    match_news_to_funds,
    parse_feed,
)


def test_extract_company_prefix_uses_words_before_portfoy():
    assert extract_company_prefix("ATA PORTFÖY ÇOKLU VARLIK DEĞİŞKEN FON") == "ATA PORTFÖY"
    assert extract_company_prefix("İŞ PORTFÖY HİSSE FON") == "İŞ PORTFÖY"


def test_extract_company_prefix_falls_back_to_first_three_words():
    assert extract_company_prefix("AGESA HAYAT VE EMEKLİLİK OKS FONU") == "AGESA HAYAT VE"


def test_parse_feed_returns_items(fixtures_dir):
    text = (fixtures_dir / "rss_sample.xml").read_text(encoding="utf-8")
    items = parse_feed(text, source_name="bigpara")
    assert len(items) == 3
    assert items[0]["title"] == "ATA PORTFÖY yeni fon ihraç etti"
    assert items[0]["source"] == "bigpara"
    assert items[0]["url"] == "https://example.com/ata-portfoy-yeni-fon"
    assert isinstance(items[0]["published"], datetime)


def test_match_news_to_funds_filters_by_prefix(fixtures_dir):
    text = (fixtures_dir / "rss_sample.xml").read_text(encoding="utf-8")
    items = parse_feed(text, source_name="bigpara")
    selected = pd.DataFrame({
        "fon_kodu": ["AAA", "BBB"],
        "fon_adi":  ["ATA PORTFÖY ÇOKLU VARLIK FON", "BETA PORTFÖY HİSSE FON"],
    })
    matched = match_news_to_funds(items, selected, max_per_fund=3, max_age_days=365)
    assert "AAA" in matched
    assert len(matched["AAA"]) == 1
    assert "BBB" in matched
    assert len(matched["BBB"]) == 1


def test_match_skips_funds_with_zero_hits(fixtures_dir):
    text = (fixtures_dir / "rss_sample.xml").read_text(encoding="utf-8")
    items = parse_feed(text, source_name="bigpara")
    selected = pd.DataFrame({
        "fon_kodu": ["ZZZ"],
        "fon_adi":  ["ZINCONIA PORTFÖY FON"],
    })
    matched = match_news_to_funds(items, selected, max_per_fund=3, max_age_days=365)
    assert "ZZZ" not in matched


def test_fetch_feed_text_returns_none_on_error():
    with patch("fundexpert.news.rss.urlopen", side_effect=OSError("network down")):
        assert fetch_feed_text("https://nope") is None
```

- [ ] **Step 11.3: Create empty `fundexpert/news/__init__.py`**

(empty file)

- [ ] **Step 11.4: Run tests, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_rss.py -v
```

Expected: ImportError on `fundexpert.news.rss`.

- [ ] **Step 11.5: Implement `fundexpert/news/rss.py`**

```python
"""Optional RSS news annotation pass. Pure parsing + matching, with thin IO at the edge."""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import feedparser
import pandas as pd

from fundexpert.config import NEWS_CACHE_DIR, NEWS_CACHE_TTL_SECONDS

USER_AGENT = "fundexpert/0.1 (+local)"
HTTP_TIMEOUT_SECONDS = 5


def extract_company_prefix(fon_adi: str) -> str:
    """Return the words before 'PORTFÖY' (uppercase), or first 3 words as fallback."""
    upper = fon_adi.upper()
    m = re.search(r"\bPORTF[ÖO]Y\b", upper)
    if m:
        return upper[: m.end()].strip()
    return " ".join(upper.split()[:3])


def _cache_path(url: str) -> Path:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return NEWS_CACHE_DIR / f"{h}.xml"


def fetch_feed_text(url: str) -> str | None:
    """Fetch RSS XML with a 1-hour disk cache. Return None on any failure."""
    cache_file = _cache_path(url)
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < NEWS_CACHE_TTL_SECONDS:
            try:
                return cache_file.read_text(encoding="utf-8")
            except OSError:
                pass

    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except (URLError, OSError, TimeoutError):
        return None

    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(text, encoding="utf-8")
    except OSError:
        pass
    return text


def parse_feed(text: str, source_name: str) -> list[dict[str, Any]]:
    """Parse an RSS/Atom feed text into normalized item dicts."""
    parsed = feedparser.parse(text)
    items: list[dict[str, Any]] = []
    for entry in parsed.entries:
        published: datetime | None = None
        for key in ("published_parsed", "updated_parsed"):
            tt = entry.get(key)
            if tt:
                published = datetime(*tt[:6], tzinfo=timezone.utc)
                break
        items.append({
            "title":       entry.get("title", "").strip(),
            "url":         entry.get("link", "").strip(),
            "description": entry.get("description", "").strip(),
            "published":   published,
            "source":      source_name,
        })
    return items


def match_news_to_funds(
    items: list[dict[str, Any]],
    selected: pd.DataFrame,
    max_per_fund: int,
    max_age_days: int,
) -> dict[str, list[dict[str, Any]]]:
    """For each fund, return up to `max_per_fund` recent items containing its company prefix."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    matched: dict[str, list[dict[str, Any]]] = {}

    sorted_items = sorted(
        items,
        key=lambda it: it["published"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    for _, row in selected.iterrows():
        prefix = extract_company_prefix(row["fon_adi"])
        hits: list[dict[str, Any]] = []
        for it in sorted_items:
            if it["published"] and it["published"] < cutoff:
                continue
            haystack = (it["title"] + " " + it["description"]).upper()
            if prefix in haystack:
                hits.append(it)
                if len(hits) >= max_per_fund:
                    break
        if hits:
            matched[row["fon_kodu"]] = hits
    return matched
```

- [ ] **Step 11.6: Run tests, expect PASS**

```bash
.venv/Scripts/pytest tests/test_rss.py -v
```

Expected: 6 passed.

- [ ] **Step 11.7: Commit**

```bash
git add fundexpert/news/__init__.py fundexpert/news/rss.py tests/test_rss.py tests/fixtures/rss_sample.xml
git commit -m "feat(news): RSS fetch + parse + match with 1h disk cache"
```

---

## Task 12: Wire `--news` Into `cli.py`

**Files:**
- Modify: `fundexpert/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 12.1: Add the failing test for the news flow**

Append to `tests/test_cli.py`:

```python
def test_run_pipeline_with_news_attaches_matches(fake_universe_loader):
    fake_items = [{
        "title": "ATA PORTFÖY büyüme açıkladı",
        "url":   "https://example.com/x",
        "description": "ata portföy ...",
        "published": datetime(2026, 5, 1),
        "source": "bigpara",
    }]
    with patch("fundexpert.cli._gather_news", return_value=fake_items) as gather:
        selected, header, news = run_pipeline_with_news(
            universe="tefas",
            risk_priority="medium",
            horizon="medium",
            volume_priority="medium",
            fee_priority="medium",
            n=2,
            max_per_type=2,
            now=datetime(2026, 5, 2, 11, 42),
            do_news=True,
        )
        assert gather.called
        assert isinstance(news, dict)
```

Add the import at the top of `tests/test_cli.py`:

```python
from fundexpert.cli import run_pipeline, run_pipeline_with_news
```

- [ ] **Step 12.2: Run, expect FAIL**

```bash
.venv/Scripts/pytest tests/test_cli.py::test_run_pipeline_with_news_attaches_matches -v
```

Expected: ImportError on `run_pipeline_with_news`.

- [ ] **Step 12.3: Add `_gather_news` and `run_pipeline_with_news` to `fundexpert/cli.py`**

Append to `fundexpert/cli.py` (after `run_pipeline`):

```python
from fundexpert.config import RSS_FEEDS
from fundexpert.news.rss import fetch_feed_text, parse_feed, match_news_to_funds


def _gather_news() -> list[dict[str, Any]]:
    """Fetch and parse all configured RSS feeds. Per-feed failures are skipped silently."""
    items: list[dict[str, Any]] = []
    for url in RSS_FEEDS:
        text = fetch_feed_text(url)
        if text is None:
            continue
        # Use the host as a friendly source name
        source = url.split("//", 1)[-1].split("/", 1)[0]
        items.extend(parse_feed(text, source_name=source))
    return items


def run_pipeline_with_news(
    universe: str,
    risk_priority: str,
    horizon: str,
    volume_priority: str,
    fee_priority: str,
    n: int,
    max_per_type: int,
    now: datetime,
    do_news: bool,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Run the pipeline; if `do_news`, also collect RSS annotations."""
    selected, header = run_pipeline(
        universe=universe,
        risk_priority=risk_priority,
        horizon=horizon,
        volume_priority=volume_priority,
        fee_priority=fee_priority,
        n=n,
        max_per_type=max_per_type,
        now=now,
    )
    if not do_news or len(selected) == 0:
        return selected, header, {}

    items = _gather_news()
    if not items:
        return selected, header, {}

    matched = match_news_to_funds(items, selected, max_per_fund=3, max_age_days=30)
    return selected, header, matched
```

Now update the `main()` function so it uses the news-aware pipeline when `--news` is set. **Replace** the body of `main()` from after `_save_last_run(answers)` through the end of the function with:

```python
    selected, header, news = run_pipeline_with_news(
        universe=answers["universe"],
        risk_priority=answers["risk_priority"],
        horizon=answers["horizon"],
        volume_priority=answers["volume_priority"],
        fee_priority=answers["fee_priority"],
        n=answers["n"],
        max_per_type=args.max_per_type,
        now=datetime.now(),
        do_news=args.news,
    )

    if header.get("warning"):
        print(f"Uyarı: {header['warning']}", file=sys.stderr)

    render_portfolio(selected, header, news=news if news else None)
    return 0
```

- [ ] **Step 12.4: Run, expect PASS**

```bash
.venv/Scripts/pytest tests/test_cli.py -v
```

Expected: 2 passed (existing `test_run_pipeline_returns_selected_with_weights` plus the new news test).

- [ ] **Step 12.5: Commit**

```bash
git add fundexpert/cli.py tests/test_cli.py
git commit -m "feat(cli): wire --news flag through pipeline to render"
```

---

## Task 13: End-to-End Smoke Test

**Files:**
- Create: `tests/test_smoke.py`

- [ ] **Step 13.1: Write the smoke test**

Create `tests/test_smoke.py`:

```python
from datetime import datetime

import pytest

from fundexpert.cli import run_pipeline


@pytest.mark.parametrize("universe", ["tefas", "befas", "both"])
def test_pipeline_runs_against_real_csvs(universe):
    selected, header = run_pipeline(
        universe=universe,
        risk_priority="medium",
        horizon="medium",
        volume_priority="medium",
        fee_priority="medium",
        n=5,
        max_per_type=2,
        now=datetime(2026, 5, 2, 11, 42),
    )
    assert 0 < len(selected) <= 5
    assert sum(selected["display_weight_pct"]) == pytest.approx(100.0, abs=0.05)
    assert header["candidate_total"] > 0
    assert header["candidate_kept"] > 0
    assert (selected["risk"].between(1, 7)).all()


def test_pipeline_long_horizon_drops_funds_with_no_long_history():
    selected, header = run_pipeline(
        universe="tefas",
        risk_priority="high",
        horizon="long",
        volume_priority="low",
        fee_priority="high",
        n=5,
        max_per_type=2,
        now=datetime(2026, 5, 2, 11, 42),
    )
    # Newer funds have NaN ret_3y/ret_5y; horizon=long must exclude some
    assert header["excluded_horizon"] > 0
    assert len(selected) > 0
```

- [ ] **Step 13.2: Run the smoke test**

```bash
.venv/Scripts/pytest tests/test_smoke.py -v
```

Expected: 4 passed. (3 from parametrized universe + 1 long-horizon test.)

- [ ] **Step 13.3: Run the full suite**

```bash
.venv/Scripts/pytest -v
```

Expected: all tests pass (previous tasks + smoke).

- [ ] **Step 13.4: Manual sanity run**

```bash
.venv/Scripts/fundexpert
```

Expected: Turkish prompts appear; after answering, a `rich` table with selected funds, weights summing to 100.0, and a header block prints. No tracebacks.

```bash
.venv/Scripts/fundexpert --news
```

Expected: Same flow; if internet is reachable and any feed matches a fund's company prefix, a "Haberler:" footer prints below the table. If feeds 404 or no matches, the table still prints normally.

- [ ] **Step 13.5: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: end-to-end smoke against real TEFAS/BEFAS CSVs"
```

---

## Self-Review Checklist (post-write)

| Concern | Result |
|---|---|
| Spec coverage: every section in `docs/` has a task | All 7 sections covered: 01 → file layout (T0), 02 → T2/T3, 03 → T4/T5/T6, 04 → T7/T8, 05 → T10, 06 → T11/T12, 07 → T9/T13 |
| Placeholders (TBD/TODO/etc.) | None |
| Type/name consistency across tasks | `fon_kodu`, `umbrella_type`, `R`, `score`, `display_weight_pct`, `_breakdown` consistent throughout |
| Calibration constants flagged in spec are imported from one place | `config.py` is the only source for `PRIORITY_WEIGHTS`, `RISK_LAMBDAS`, `HORIZON_BUCKETS`, `DEFAULT_MAX_PER_TYPE`, `WEIGHT_EPSILON`, `RSS_FEEDS` |
| RSS verification gap (spec open item) | Acknowledged in `config.py` comment; news tests use a local fixture so verification gap doesn't block green CI |
| Pure-vs-IO module separation | Pure: `scoring/*`, `select/*`. IO at edges: `data/loader.py`, `news/rss.py`, `cli.py` |

---

## Out of Scope (tracked for v2)

- `--explain` flag printing per-fund `_breakdown` — column already produced and carried through.
- File output (JSON / CSV / MD reports).
- News-driven scoring impact (currently annotation-only).
- KAP / SPK regulator-bulletin scraping.
- English UI mode.
- `--max-per-type` exposed as a prompt (currently flag-only, default 2).
