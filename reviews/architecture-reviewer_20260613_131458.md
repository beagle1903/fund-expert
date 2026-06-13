# Architecture Review: `fundexpert`

## Overview
The `fundexpert` codebase exhibits a strong, modular pipeline architecture typical of robust data transformation workflows. The separation of concerns between data ingestion (`loader.py`, `merge.py`), mathematical modeling (`score.py`, `horizon.py`, `weights.py`), filtering (`pick.py`), and side-effects/rendering (`cli.py`, `ui.py`, `render/`) is excellent.

Overall Test Coverage is high (~95%), and the application handles failure modes gracefully (e.g., missing API keys for news passes).

Below are the findings, categorized by severity.

---

## P0 (Critical Findings)
**None.** The architecture is solid, and there are no critical structural flaws that prevent the system from functioning correctly or securely in its current single-user CLI context.

---

## P1 (Major Findings)

### 1. Implicit Coupling to Global State (`config.py`)
Many domain functions (`score_candidates`, `compute_weights`, `apply_horizon`) import constants directly from `fundexpert.config`.
*   **Impact**: This global state coupling makes the functions harder to test (requiring `unittest.mock.patch` across tests) and reduces reusability. If you wanted to run two parallel pipelines with different `WEIGHT_EPSILON` or `NEGATIVE_NEWS_PENALTY` in a web backend, you could not do so safely.
*   **Recommendation**: Adopt Dependency Injection. Pass configuration values explicitly as arguments to these functions, potentially grouped in a `ScoringConfig` or `SelectionConfig` dataclass, instantiated and passed down by `pipeline.py`.

### 2. Concurrency Tightly Coupled to Domain Logic (`news/penalty.py`)
`apply_negative_news_penalty` hardcodes a `ThreadPoolExecutor(max_workers=10)` internally to fetch news in parallel.
*   **Impact**: Tying concurrency primitives directly into domain logic reduces testability (hard to mock deterministic execution) and makes it difficult to switch execution models (e.g., to async/await or a different queue). It also risks rate-limiting from the Tavily API since there is no centralized rate limiter if the Top-K multiplier grows.
*   **Recommendation**: Extract the concurrent execution logic. The `apply_negative_news_penalty` function should either accept an `Executor` interface or offload the fetching entirely to an `async` layer, leaving the penalty calculation pure.

### 3. Fragile Data Contracts Between Pipeline Stages
The pipeline operates by passing and mutating `pandas.DataFrame` objects. However, only the initial data merge uses `pandera.DataFrameSchema` for validation.
*   **Impact**: As the dataframe progresses (`horizon` -> `score` -> `sector` -> `pick`), it implicitly accumulates columns (`R`, `score`, `sector`). Modules like `pick.py` are coupled to column names that are injected outside of their purview, leading to fragile contracts and potential runtime errors if the pipeline order changes.
*   **Recommendation**: Introduce `pandera` schemas for intermediate steps (e.g., `ScoredCandidatesSchema`, `SelectedPortfolioSchema`). This will serve as both executable documentation and runtime safety checks.

---

## P2 (Minor Findings)

### 1. Hardcoded Heuristics in Rules Engine (`strategy.py`, `sector.py`)
The logic for determining a fund's sector and strategy relies on hardcoded tuples of strings within the Python modules.
*   **Impact**: Adding or tweaking rules requires a code change and deployment. It mixes data with code.
*   **Recommendation**: Extract `_BUCKET_RULES` and `_SECTOR_RULES` into configuration files (e.g., `rules.yaml` or `rules.json`). This allows non-developers or domain experts to tweak keyword mappings without touching Python code.

### 2. Mixed Concerns in Orchestration (`pipeline.py`)
`pipeline.py` mostly acts as a high-level orchestrator, but the logic to compute "displaced" funds (funds that would have been picked if not for the news penalty) is implemented inline (lines 130-157).
*   **Impact**: This logic is strictly for rendering/reporting and bloats the orchestrator.
*   **Recommendation**: Extract the counterfactual displacement logic into a dedicated reporting or diffing module (e.g., extending `render.diff` or creating a `news.report` module).
