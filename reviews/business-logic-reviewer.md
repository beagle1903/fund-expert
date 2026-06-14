# Business Logic Review

## Overview
A comprehensive review of the `fundexpert` codebase was conducted, focusing strictly on the correctness of business logic including mathematical scoring models, weight distribution algorithms, diversity capping semantics, and Turkish string handling. 

The core financial math—score weighting, risk penalties, top-N picking, diversity capping, and largest-remainder weight distribution—is mathematically sound, deterministic, and highly robust against edge cases (such as zero-division, track-record lengths, NAs, or ties).

The findings below highlight isolated inconsistencies and improvements.

## P1 (High)

**1. Inconsistent Keyword Matching Priority (Vectorized vs Scalar)**
The pipeline utilizes vectorized extraction (`bucket_from_names`, `sector_from_names`) which assigns categories based on the **first keyword found reading left-to-right** in the fund name. However, the scalar functions (`bucket_from_name`, `sector_from_name`) iterate over `rules.json`, enforcing a **strict JSON array priority**.
- **Impact:** For a fund named `"SAĞLIK VE TEKNOLOJİ FONU"`, the vectorized path extracts `"SAĞLIK"` (health) because it appears first in the text, whereas the scalar path correctly enforces priority and matches `"TEKNOLOJİ"` (tech) first because it appears earlier in `rules.json`. The scalar path is explicitly tested in `tests/`, but the pipeline relies entirely on the mismatched vectorized path.
- **Suggested Fix:** Replace `str.extract(pattern)` in the vectorized functions with `np.select()` using an ordered list comprehension of boolean masks. This will enforce exact rule priority from `rules.json` while maintaining vectorization speed.

## P2 (Medium / Low)

**1. Non-Deterministic Tie-Breaking in News Query Selection**
In `fundexpert/news/penalty.py`, the top-K funds to query are selected via `scored["score"].nlargest(top_k).index`. Pandas `.nlargest()` breaks ties based on insertion order. If two funds share the exact same float score at the Kth boundary, the inclusion is mathematically non-deterministic (though practically stable since insertion order is preserved from the data source).
- **Suggested Fix:** Sort by `["score", "fon_kodu"]` descending before taking the `.head(top_k)` indices, exactly as `pick_top` does, ensuring rigorous deterministic tie-breaking.

**2. Potential Uncapped "Other" Strategy Bucket**
While the `"diversified"` sector is explicitly exempt from the `max_per_sector` cap, the fallback strategy bucket `"other"` is still subject to the `max_per_type` cap. If a large number of valid funds fail to match any strategy keyword in `rules.json` due to naming anomalies, the pipeline will forcefully cap them at 2, potentially excluding viable candidates and triggering a "could not fill portfolio" warning prematurely.
- **Suggested Fix:** Evaluate whether `"other"` should be granted a cap exemption analogous to the `"diversified"` sector, or explicitly document that strategy classification is mandatory for portfolio inclusion beyond the cap.

**3. Ambiguous `np.float32` Casting on Pandas NA Values**
In `score_candidates`, `df["risk"].to_numpy(dtype=np.float32, na_value=7.0)` correctly replaces NAs with `7.0` for safe computation. While this perfectly exploits Pandas' nullable Series API, it heavily relies on specific `na_value` casting semantics under the hood. 
- **Suggested Fix:** For clarity and robustness across future Pandas versions, consider the more explicit `df["risk"].fillna(7.0).to_numpy(dtype=np.float32)`.

---
*Note: Turkish string operations (`str.maketrans("iı", "İI")` combined with `.upper()`) have been rigorously tested and confirmed to be 100% accurate without causing regressions on standard Latin uppercase operations.*
