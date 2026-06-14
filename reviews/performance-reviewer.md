# Performance Review: `fundexpert`

## Overview
The `fundexpert` pipeline has been reviewed for performance bottlenecks, algorithmic complexity, inefficient `pandas` dataframe usage, and memory leaks. The recent vectorization efforts have already yielded excellent results (a 10-iteration pipeline run executes in ~335ms natively). The findings below highlight the remaining optimizations, mostly focusing on dataframe copying, memory footprint reduction, and regex efficiency.

---

### P0: Critical Bottlenecks
*(No critical P0 bottlenecks found. The pipeline currently runs well within acceptable constraints and exhibits no major memory leaks or blocking loops.)*

---

### P1: Significant Optimizations

**1. Redundant Regex Evaluations (`data/merge.py`)**
- **Location:** `clean_candidates`
- **Issue:** The pipeline evaluates `df["fon_adi"].str.contains` and `df["umbrella_type"].str.contains` separately for the `OKS` and `SERBEST` restrictions using `case=False` and `regex=True`. This results in 4 full passes over string arrays using Python's slow regex engine.
- **Actionable Fix:** Combine the patterns into a single compiled regex: `r"\b(?:OKS|SERBEST)\b"`. This halves the number of dataframe passes:
  ```python
  pattern = r"\b(?:OKS|SERBEST)\b"
  bad_name = df["fon_adi"].str.contains(pattern, case=False, na=False, regex=True)
  bad_umbrella = df["umbrella_type"].str.contains(pattern, case=False, na=False, regex=True)
  mask = mask & ~bad_name & ~bad_umbrella
  ```

**2. Double Iteration on Missing Values (`scoring/score.py`)**
- **Location:** `score_candidates`
- **Issue:** The check `risk_missing = df["risk"].isna()` is followed by `if risk_missing.any(): missing_count = risk_missing.sum()`. Both `.any()` and `.sum()` trigger complete scans of the boolean series.
- **Actionable Fix:** Compute `.sum()` directly. Since `True` evaluates to 1, you can simply do:
  ```python
  missing_count = risk_missing.sum()
  if missing_count > 0:
      logger.warning(...)
  ```

---

### P2: Memory Footprint & Minor Inefficiencies

**1. Object String Memory Footprint (`data/loader.py`)**
- **Location:** `_read_one`
- **Issue:** Strings are loaded using `dtype={"Fon Kodu": str, "Fon Adı": str, "Şemsiye Fon Türü": str}`. This falls back to Pandas' default `object` dtype, which allocates standard Python string objects with significant memory overhead. 
- **Actionable Fix:** Switch to PyArrow string representation by using `dtype="string[pyarrow]"` for string columns. Furthermore, `Şemsiye Fon Türü` (`umbrella_type`) has low cardinality and should be cast to `"category"` to heavily minimize memory usage and accelerate subsequent operations.

**2. Unnecessary Series Copies during Clamping (`scoring/score.py`)**
- **Location:** `score_candidates`
- **Issue:** `np.log1p(df["aum_last"].fillna(0).clip(lower=0))` chains `.fillna(0)` and `.clip(lower=0)`. Each method allocates a new Series object.
- **Actionable Fix:** It is usually more memory-efficient to clip first (which inherently propagates NaNs) and then fill, or to apply `np.maximum(df["aum_last"].fillna(0), 0)` directly to bypass the Pandas `clip` dataframe overhead.

**3. Dataframe Copies during Deduplication (`data/merge.py`)**
- **Location:** `merge_universe`
- **Issue:** `.drop_duplicates(subset=["fon_kodu"])` allocates fully disconnected copies of the `getiri`, `buyukluk`, and `yonetim_ucreti` dataframes. 
- **Actionable Fix:** No strict fix required since dataset sizes are small, but if scaled, this could become a memory leak. Doing slicing and duplicated drops efficiently `df = df[~df.duplicated(...)]` can sometimes prevent excessive memory blocks.

**4. Sector Regex Iterative Reassignments (`select/sector.py`)**
- **Location:** `_clean_names`
- **Issue:** Consecutive `.str.replace(..., regex=True)` calls create 3 intermediate Series copies.
- **Actionable Fix:** If PyArrow string backend is adopted, these can remain. Otherwise, a single `.replace(regex_dict)` can perform the substitutions in one pass.
