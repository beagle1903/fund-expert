# Architecture Review: fundexpert

**Date:** 2026-06-14
**Reviewer:** Architecture-Reviewer Subagent

## Overview
Overall, the `fundexpert` codebase exhibits a solid, data-driven architecture. The core processing flow (`load -> merge -> clean -> score -> bucket -> pick -> weight`) is well-encapsulated inside `pipeline.py` using functional transformations and dataclasses. The explicit isolation of the external Tavily API (`news/tavily.py`) from domain application logic (`news/penalty.py`) and the use of `pandera` for intermediate state validation are excellent architectural decisions.

However, there are several Separation of Concerns (SoC) and DRY violations regarding where business rules, string manipulations, and file IO are managed. 

Below are the findings categorized by priority:

## P0 Findings (Critical Structural Issues)
*None. The foundational dataflow and pipeline architecture are sound, stateless, and highly testable.*

## P1 Findings (Significant DRY / Separation of Concerns Violations)

### 1. Hardcoded Domain Rules in Data Layer (`data/merge.py`)
The `clean_candidates` function in `data/merge.py` contains hardcoded string/regex exclusions for "OKS" and "SERBEST" funds. This mixes data-joining logic with business exclusion rules.
* **Recommendation:** Extract these exclusion patterns into `rules.json` or `config.py` and apply the filter inside the pipeline layer or a dedicated validation step.

### 2. Duplicate Rule Loading Logic (`select/strategy.py` & `select/sector.py`)
Both files implement completely identical `@lru_cache` routines to open `rules.json`, parse the JSON payload, and construct regex mapping dictionaries (`_get_bucket_rules` vs `_get_sector_rules`). This is a classic DRY violation.
* **Recommendation:** Create a centralized `fundexpert/utils/rules.py` module that parses `rules.json` and vends the rules/regex maps to the respective domain modules.

### 3. Hardcoded Cleanup Constants (`select/sector.py`)
`_clean_names` and `_clean_name` in `select/sector.py` hardcode company-specific false positive regexes (e.g., `QNB SAĞLIK HAYAT`, `TARIM KREDİ PORTFÖY`). 
* **Recommendation:** Just like strategy definitions, these string substitution rules should be decoupled from the code and housed in `rules.json`.

### 4. Mixed Abstraction Levels in Pipeline (`pipeline.py`)
The orchestration function `run_pipeline` dips into low-level string manipulation by manually constructing a `str.maketrans("iı", "İI")` map and running a list comprehension to uppercase fund names (Lines 88-93). The codebase already defines `turkish_upper` in `utils/text.py`.
* **Recommendation:** Abstract this normalization by implementing a vectorized pandas text utility in `utils/text.py`, or push the normalization logic down into `bucket_from_names`/`sector_from_names` where it is actually needed.

## P2 Findings (Minor Stylistic and Organizational Improvements)

### 1. `DATA_ROOT` Path Resolution (`cli.py`)
While constants like `HISTORY_DIR` and `LAST_RUN_FILE` are correctly managed in `config.py`, `DATA_ROOT` path resolution logic is housed in `cli.py`.
* **Recommendation:** Move `DATA_ROOT` definition to `config.py` to maintain a single source of truth for filesystem path layouts.

### 2. Implicit Column Coupling (`scoring/score.py`)
`score_candidates` strictly expects the `R` column injected by the prior `apply_horizon` step. 
* **Recommendation:** While acceptable in pandas pipelines, it would improve contract visibility if you added a `HorizonCandidatesSchema` in `schemas.py` and validated the dataframe shape prior to scoring.

### 3. Duplicate Imports (`pipeline.py`)
There is a minor organizational artifact in `pipeline.py` (lines 24-25) where `clean_candidates` is imported twice consecutively:
```python
from fundexpert.data.merge import clean_candidates
from fundexpert.data.merge import clean_candidates
```
* **Recommendation:** Remove the duplicate import.

### 4. Inline/Late Imports
`apply_negative_news_penalty` (`news/penalty.py`) imports `concurrent.futures` dynamically midway through the function block.
* **Recommendation:** Move this to the top of the file alongside standard library imports to comply with PEP-8.
