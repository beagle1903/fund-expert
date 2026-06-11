# Architecture Review: `fundexpert`

## Overview
The `fundexpert` application follows a straightforward pipeline pattern (Load → Clean → Horizon → Score → Filter News → Pick → Weight → Render). However, the codebase exhibits moderate architectural coupling, particularly by intermingling file system side-effects and business orchestration within the Command Line Interface (CLI) module. 

Overall, the design is functionally sound for a script, but migrating it to a clean architecture separates data access, business rules, and presentation, enhancing testability and extensibility.

---

## P1 (High/Important): Tight Coupling of Pipeline Orchestrator and CLI

### Context
In `fundexpert/cli.py`, the core orchestration function `run_pipeline()` resides alongside the UI prompts and arg parsing. Furthermore, `run_pipeline` directly invokes data loading through `_load_one()`, which reaches out to the filesystem (`DATA_ROOT`). By coupling business logic to I/O and CLI presentation, testing `run_pipeline()` with mock data requires patching out the file system (as seen in `test_cli.py:fake_universe_loader`).

### File/Line References
- `fundexpert/cli.py:46-54` (`_load_one` function accessing `DATA_ROOT`)
- `fundexpert/cli.py:57-194` (`run_pipeline` function definition)

### Suggested Fix Prompt
> Refactor the core pipeline out of `fundexpert/cli.py` into a new module `fundexpert/pipeline.py`. Modify the `run_pipeline` signature to accept a `pd.DataFrame` of candidates instead of a `universe` string, fully decoupling it from disk I/O. Update `cli.py` to handle loading data using `loader.load_universe` and `merge.merge_universe`, and then pass the materialized `DataFrame` directly to `pipeline.run_pipeline`.

---

## P2 (Medium/Low): Counterfactual News Logic Mixed in Core Pipeline

### Context
To support the "displaced funds" rendering feature when the news penalty is active, `run_pipeline()` computes a counterfactual simulation (i.e., calling `pick_top` without the penalty). This logic is inlined directly within `run_pipeline`, spanning ~25 lines. This clutters the primary data flow and merges the reporting/diffing logic with standard data processing.

### File/Line References
- `fundexpert/cli.py:142-167` (The `displaced` calculation loop)

### Suggested Fix Prompt
> Extract the counterfactual 'displaced' logic from `fundexpert/cli.py:run_pipeline` into a standalone helper function `compute_displaced_funds(scored_pre, scored_post, n, max_per_type, max_per_sector)` inside `fundexpert/news/penalty.py`. Update `run_pipeline` to simply call this helper function and attach the result to `news_meta`.

---

## P2 (Medium/Low): Hardcoded Scoring Factors

### Context
In `fundexpert/scoring/score.py`, the `score_candidates()` function explicitly hardcodes the formulas and variable names for `R` (return), `V` (volume), and `F` (fee), as well as the manual assembly of the `_breakdown` dictionary. If a new metric is introduced, the module has to be completely rewritten. 

### File/Line References
- `fundexpert/scoring/score.py:18-54`

### Suggested Fix Prompt
> Refactor `fundexpert/scoring/score.py:score_candidates` to dynamically construct base scores and the `_breakdown` dictionaries using a loop over configured factor specifications rather than hardcoded variables (`R_contrib`, `V_contrib`, `F_contrib`). Move the factor-to-column mappings to `config.py` to make the scoring algorithm easily extensible.

---

## P2 (Medium/Low): Implicit Data Access Strategy

### Context
The application implicitly assumes all data loading happens via local CSVs in a specific folder structure (handled by `_load_one` in `cli.py` and `loader.py`). While there is a `loader.py`, it behaves as a loose collection of functions rather than a cohesive data source boundary. 

### File/Line References
- `fundexpert/data/loader.py`
- `fundexpert/cli.py:46-54`

### Suggested Fix Prompt
> Introduce a formal Data Repository or Source interface (e.g., `fundexpert/data/repository.py`). Implement a `LocalCSVRepository(data_root)` class that encapsulates `load_universe` and file path resolution, exposing a `get_candidates(universe_name)` method. Update `cli.py` to inject this repository.
