# Performance Review: FundExpert

## Executive Summary
Overall, the `fundexpert` codebase is well-structured and handles small tabular datasets appropriately. However, there are a few Pandas performance anti-patterns and one critical concurrency issue that must be addressed. Additionally, a missing file `fundexpert/utils/text.py` currently prevents `tavily.py` from executing successfully.

---

## P0: Critical Issues (Correctness & Concurrency)

### 1. Concurrent Pandas DataFrame Mutation (`news/penalty.py`)
**Location:** `news/penalty.py` around line 100-103
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    # ...
    for idx, row in prefix_to_indices[prefix]:
        adjusted.at[idx, "score"] = float(row["score"]) - penalty
```
**Issue:** Modifying a Pandas DataFrame from multiple threads concurrently is thread-unsafe and can lead to silent memory corruption, race conditions, or segmentation faults depending on the underlying C/Cython extensions.
**Fix:** Collect the results inside the thread pool, then apply the updates in the main thread sequentially or in a vectorized manner.

### 2. Missing `utils/text.py` File Breaks Imports
**Location:** `news/tavily.py` line 33 (`from fundexpert.utils.text import turkish_lower`)
**Issue:** The file `fundexpert/utils/text.py` is missing from the repository. Attempting to run the news penalty module causes a `ModuleNotFoundError`.
**Fix:** Restore `text.py` or implement the `turkish_lower` function directly inside `news/tavily.py` or `__init__.py`.

---

## P1: Performance Bottlenecks & Redundancies

### 1. Repeated Masking Creates Intermediate DataFrames
**Location:** `data/merge.py` -> `clean_candidates`
```python
def clean_candidates(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df["applied_management_fee_pct"].notna()]
    df = df[df["ret_3m"].notna()]
    return df
```
**Issue:** Filtering sequentially creates intermediate dataframe copies, increasing memory allocation overhead.
**Fix:** Combine the boolean masks using the `&` operator to filter in a single pass.
```python
mask = df["applied_management_fee_pct"].notna() & df["ret_3m"].notna()
return df[mask]
```

### 2. Chained `.str` Operations Create Intermediate Series
**Location:** `pipeline.py` line 78
```python
scored_fon_adi_upper = scored["fon_adi"].fillna("").str.replace("i", "İ").str.replace("ı", "I").str.upper()
```
**Issue:** Each `.str` method iterates over the entire series and allocates a new array of strings. Chaining three of them is O(3N) and allocates heavily.
**Fix:** For a dataset of this size, a single list comprehension passing through pure Python string methods is faster and allocates less memory:
```python
scored_fon_adi_upper = pd.Series(
    [s.replace("i", "İ").replace("ı", "I").upper() for s in scored["fon_adi"].fillna("")],
    index=scored.index
)
```

### 3. Iterative Pandas `.loc` Assignments inside Loops
**Location:** `select/weights.py` line 27 and 48
```python
for idx in out["score"].astype(float).nlargest(leftover).index:
    display.loc[idx] += WEIGHT_STEP_PCT
# and
for idx in winners:
    units.loc[idx] += 1
```
**Issue:** Single-row assignments inside a `for` loop are a known Pandas anti-pattern. While `N` is small (~20), this breaks vectorization.
**Fix:** Pass the list of indices directly to `.loc` for vectorized assignments.
```python
winners_idx = out["score"].astype(float).nlargest(leftover).index
display.loc[winners_idx] += WEIGHT_STEP_PCT
# and
units.loc[winners] += 1
```

### 4. Double Quantile Sorting
**Location:** `scoring/normalize.py` line 17
```python
lo, hi = finite.quantile(0.01), finite.quantile(0.99)
```
**Issue:** Computing quantiles separately forces Pandas to sort or partition the array twice. 
**Fix:** Compute both quantiles in one pass.
```python
quantiles = finite.quantile([0.01, 0.99])
lo, hi = quantiles[0.01], quantiles[0.99]
```

---

## P2: Minor Optimizations

### 1. Redundant Dataframe Sorting in `pick_top`
**Location:** `select/pick.py` and `pipeline.py`
**Issue:** When computing the `displaced` funds, `pipeline.py` calls `pick_top` a second time with `scored_pre`. `pick_top` internally runs `scored.sort_values(["score", "fon_kodu"])`. The original dataframe `scored` is sorted on the exact same columns. This leads to double-sorting the same dataset.
**Fix:** Sort `scored_pre` once in `pipeline.py`, and pass an optional `is_sorted=True` flag to `pick_top` to bypass redundant sorting.

### 2. Inefficient Globs for History
**Location:** `history/store.py` -> `load_last_run`
```python
candidates = sorted(history_dir.glob(f"*_{universe}.json"), reverse=True)
```
**Issue:** `history_dir.glob` reads all entries and `sorted` loads them into memory. If the history folder grows to thousands of runs, this slows down startup. 
**Fix:** Consider limiting the depth or storing a symlink/pointer `latest_tefas.json` that is updated on each run to skip the directory read.
