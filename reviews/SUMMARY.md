# Codebase Review Summary: `fundexpert`

This document synthesizes the findings from 5 parallel subagents (Security, Architecture, Test Coverage, Performance, and Business Logic) that reviewed the `fundexpert` codebase.

The overall health of the codebase is excellent. The architecture is stateless and testable, security practices are strict, and test coverage is at 97.25% with robust property-based testing. However, a few P1 separation-of-concerns and logical inconsistencies were found. 

Below are the prioritized findings and their actionable agent prompts.

---

## 🔴 P0 (Critical Issues)
*None. No critical bottlenecks, logic failures, or security vulnerabilities were found.*

---

## 🟠 P1 (High Priority / Significant Fixes)

### 1. Inconsistent Keyword Matching Priority (Vectorized vs Scalar) [Business Logic]
The pipeline's vectorized classification extracts keywords based on textual appearance (left-to-right), whereas the scalar functions correctly enforce the priority defined in `rules.json`.
* **Agent Prompt:** "Refactor the vectorized functions in `select/strategy.py` and `select/sector.py` (`bucket_from_names`, `sector_from_names`). Replace the current `str.extract(pattern)` approach with `np.select()` using an ordered list of boolean masks so that they perfectly enforce the JSON array priority matching the scalar versions."

### 2. Hardcoded Domain Rules & Cleanup Constants [Architecture]
Business exclusion rules (like "OKS" and "SERBEST") and company-specific cleanups (like "QNB SAĞLIK HAYAT") are hardcoded directly inside `data/merge.py` and `select/sector.py`.
* **Agent Prompt:** "Extract the hardcoded filter rules (OKS/SERBEST) from `data/merge.py` and the cleanup substitutions from `select/sector.py` into `rules.json`. Then, refactor the pipeline to read these exclusions from the configuration rather than hardcoding them in the pipeline data logic."

### 3. Duplicate Rule Loading Logic [Architecture]
Both `select/strategy.py` and `select/sector.py` contain identical routines to load and parse `rules.json` into regex mappings.
* **Agent Prompt:** "Create a new centralized module `fundexpert/utils/rules.py` to parse `rules.json`. Refactor `select/strategy.py` and `select/sector.py` to import and utilize this centralized parser to eliminate the DRY violation."

### 4. Incomplete Test Coverage Invariants (Sector Exhaustiveness & News Monotonicity) [Test Coverage]
Critical invariants are missing for the sector cap limits and the negative news penalties.
* **Agent Prompt:** "Update `test_pick.py` and `test_news_penalty.py` to add two new Hypothesis invariants: 1) Sector Count Exhaustiveness: Ensure that if the portfolio is exactly N and the sector cap is C, there are at least `ceil(N/C)` distinct sectors. 2) News Penalty Monotonicity: Ensure that a negative penalty applied to $F_1$ correctly inverts rank ordering with $F_2$ given their score differential."

### 5. Redundant Regex Evaluations & Missing Value Iterations [Performance]
The pipeline does unnecessary multi-pass string and boolean scans during candidate cleaning and scoring.
* **Agent Prompt:** "Optimize `data/merge.py` and `scoring/score.py`: In `clean_candidates`, combine the 'OKS' and 'SERBEST' checks into a single compiled regex `r'\b(?:OKS|SERBEST)\b'` to halve dataframe passes. In `score_candidates`, remove `risk_missing.any()` and just compute and check `risk_missing.sum() > 0`."

---

## 🟡 P2 (Medium / Low Priority / Tech Debt)

### Architecture & Style
* **Agent Prompt:** "Move the `DATA_ROOT` definition from `cli.py` to `config.py` to maintain a single source of truth for paths."
* **Agent Prompt:** "Abstract the manual Turkish string uppercase normalization (`str.maketrans("iı", "İI")`) from `pipeline.py` into `utils/text.py`."
* **Agent Prompt:** "Add a `HorizonCandidatesSchema` in `schemas.py` and enforce it before scoring in `scoring/score.py` to explicitly declare the required 'R' column dependency."
* **Agent Prompt:** "Remove the duplicate `clean_candidates` import in `pipeline.py` and move the dynamic `concurrent.futures` import in `news/penalty.py` to the top of the file."

### Performance
* **Agent Prompt:** "In `data/loader.py`, switch string loading to PyArrow representations (`dtype='string[pyarrow]'`) and cast `Şemsiye Fon Türü` to `'category'` to reduce memory overhead."
* **Agent Prompt:** "Optimize series copies in `scoring/score.py` by applying `np.maximum(df['aum_last'].fillna(0), 0)` directly instead of chaining `.fillna(0).clip(lower=0)`."

### Test Coverage & Edge Cases
* **Agent Prompt:** "Add a smoke test covering `__main__.py` to catch entry point regressions, and add tests for network exception branches in `tavily.py`."
* **Agent Prompt:** "Add tests for all-NaN columns (e.g., missing `aum_last` for an entire dataset) and zero valid candidates to harden edge case handling."

### Business Logic
* **Agent Prompt:** "Ensure deterministic tie-breaking in `fundexpert/news/penalty.py` by sorting `scored` by `['score', 'fon_kodu']` descending before extracting `.head(top_k)`."
* **Agent Prompt:** "Update the pandas NA casting semantics in `score_candidates`: Replace `df['risk'].to_numpy(dtype=np.float32, na_value=7.0)` with `df['risk'].fillna(7.0).to_numpy(dtype=np.float32)` for clarity and robustness."
* **Agent Prompt:** "Review the 'other' strategy bucket to see if it should receive the same diversity cap exemption as the 'diversified' sector."
