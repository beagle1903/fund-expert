# Performance Review

## Summary
The codebase is generally well-structured, but suffers from a few key performance bottlenecks, specifically relating to sequential network I/O and inefficient pandas idioms. 

## Findings

### 1. Sequential Network I/O in News Penalty Pass (P0 - Critical)
**Context:** `fundexpert/news/penalty.py` -> `apply_negative_news_penalty()`
**Description:** The function iterates over the top-K fund candidates and issues synchronous HTTP requests via `query_negative_news` (which calls `urllib.request.urlopen`) sequentially. When the cache is cold and `--news` is active, this can result in up to 40 sequential network calls, slowing down the CLI significantly (taking 20-40+ seconds).
**Suggested Fix:**
```text
Refactor `apply_negative_news_penalty` in `fundexpert/news/penalty.py` to use `concurrent.futures.ThreadPoolExecutor`. Instead of sequentially calling `query_negative_news` in a for-loop, submit the tasks to a thread pool and gather the results asynchronously. Ensure to associate the hits correctly with the fund indices.
```

### 2. Inefficient CSV Parsing (P1 - High)
**Context:** `fundexpert/data/loader.py` -> `_read_one()`
**Description:** `pd.read_csv` reads all columns from the TEFAS/BEFAS CSV exports before filtering them down using a dictionary (`rename`). This consumes unnecessary memory and CPU cycles during parsing, as TEFAS exports can be very wide.
**Suggested Fix:**
```text
Optimize `_read_one` in `fundexpert/data/loader.py` by adding `usecols=lambda c: c in rename.keys()` to the `pd.read_csv` call. This ensures pandas only parses the columns we actually care about, reducing peak memory and speeding up file reading.
```

### 3. Iterating Over DataFrames with iterrows() (P2 - Medium)
**Context:** `fundexpert/select/pick.py` -> `pick_top()`
**Description:** The function uses `sorted_df.iterrows()` to walk through candidates. `iterrows()` creates a new Pandas Series for each row, which carries a large performance penalty. While the number of rows is bounded (the size of the universe), this is an anti-pattern that slows down the selection loop unnecessarily.
**Suggested Fix:**
```text
Refactor `pick_top` in `fundexpert/select/pick.py` to use `sorted_df.itertuples()` instead of `iterrows()`. Access row elements via named tuple attributes (e.g., `row.strategy`, `row.sector`) or `.Index` instead of standard dictionary-like lookup. This will speed up the loop by an order of magnitude.
```

### 4. Sequential Pandas Index Updates (P2 - Medium)
**Context:** `fundexpert/select/weights.py` -> `compute_weights()`
**Description:** In two places, the code uses a python for-loop to iterate over index values and update a Series element-by-element (`display.loc[idx] += _STEP` and `units.loc[idx] += 1`). This bypasses Pandas' vectorized operations and adds overhead.
**Suggested Fix:**
```text
Update `compute_weights` in `fundexpert/select/weights.py` to use vectorized assignment. Replace the `for idx in ...` loops with `.loc` on an index array. For example: `units.loc[winners] += 1`.
```
