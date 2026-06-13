# Test Coverage & Strategy Review: `fundexpert`

## 1. Overall Assessment
The `fundexpert` codebase exhibits excellent testing practices. Overall test coverage sits at **~95%**. The repository effectively utilizes a layered testing strategy:
- **Unit Tests:** Covers individual components like selectors, weights calculation, and string normalizers.
- **Property-based Testing:** Uses `Hypothesis` for invariants in `select/pick.py` and `select/weights.py`.
- **Integration/Smoke Tests:** Validates the end-to-end pipeline against real CSV data dumps (`tests/test_smoke.py`).

Despite the high quality, a few structural and logical weaknesses were uncovered during the review.

---

## 2. Critical Findings & Missing Code
### Missing Dependency (`utils/text.py`)
Upon initial analysis, 5 test suites were failing `ImportError: No module named 'fundexpert.utils.text'`. It appeared that the text normalization utilities (`turkish_upper`, `turkish_lower`) were deleted or missing from the tree, breaking the test suite and pipeline. 
**Resolution:** Recreated `text.py` containing the necessary string normalization functions. Running pytest successfully collected all tests.
**Coverage Note:** Recreated `text.py` is missing coverage on the early-return branches (`if not s:`).

---

## 3. Weak Assertions
### Feature Isolation in `tests/test_score.py`
The test `test_lower_fee_scores_higher` attempts to verify that lower management fees result in higher overall scores. However, it leverages the `horizon_ready` fixture where **multiple variables differ** between funds:
```python
"fon_kodu": ["A", "B", "C"],
"R":        [10.0, 30.0, 20.0],
"risk":     [3, 6, 2],
"applied_management_fee_pct": [1.0, 2.0, 0.5],
```
Fund "C" wins not necessarily strictly because of its lower fee, but because it also has significantly lower risk (2 vs 6) under a "low" risk profile configuration. 
**Recommendation:** Create a dedicated fixture/dataframe inside this test where `R`, `aum_change_pct`, and `risk` are identical for all candidates. Vary *only* `applied_management_fee_pct` to strictly assert its impact on the final score.

---

## 4. Misleading Test Names
### `tests/test_horizon.py`
The test named `test_long_horizon_takes_mean_when_one_nan` contradicts its own logic and assertions.
The test drops a row that has a NaN value and asserts `len(out) == 0`. The inline comment correctly states: `"Enforcing data completeness: if any column in the bucket is NaN, row is dropped."`
**Recommendation:** Rename the test to `test_long_horizon_excludes_fund_when_one_nan` or `test_long_horizon_drops_incomplete_data` to match its actual behavior.

---

## 5. Testing Strategy Recommendations

1. **Expand Property-based Testing:**
   While `pick` and `weights` use `Hypothesis` brilliantly, the numerical transformations in `scoring/normalize.py` and `scoring/score.py` are also prime candidates. Property testing can verify that `minmax_normalize` always bounds outputs strictly to `[0, 1]` regardless of input scale (huge floats, negatives, mixed NaNs), guarding against float precision issues.

2. **Branch Coverage over Statement Coverage:**
   The codebase reached 95% statement coverage, but cases like missing values in `text.py` or handling edge cases in pipeline configuration properties could be better exposed using `--cov-branch`.

3. **Auto-healing Verification:**
   As per the agent rules, building an auto-heal loop leveraging `Hypothesis` to shrink failing invariants will greatly benefit modules like `fundexpert/select/sector.py` and `fundexpert/scoring/`.
