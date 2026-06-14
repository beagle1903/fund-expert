# Architecture Review: fundexpert

## Executive Summary
The `fundexpert` codebase exhibits a strong, modular architecture built around the "Functional Core, Imperative Shell" pattern. Data flows linearly through a series of pure and deterministic dataframe transformations (`clean` -> `horizon` -> `score` -> `penalize` -> `pick` -> `weight`). Type-safety and data contracts are clearly defined using `pandera` schemas, and external side-effects (like the Tavily API integration and CLI orchestration) are cleanly bounded. Overall architectural integrity is high, but there are opportunities to improve dependency injection, eliminate inline environment variable checks, and decouple the main pipeline orchestrator from concrete constants.

## Detailed Findings

### P1 Findings (Important)
*   **Leaky Configuration and Missing Dependency Injection (DI) in `pipeline.py`**:
    *   `pipeline.py` imports a large number of constants directly from `config.py` (e.g., `NEGATIVE_NEWS_KEYWORDS`, `NEWS_DOMAIN_ALLOWLIST`, `NEWS_CACHE_DIR`). This circumvents the `PipelineConfig` object, making it harder to test the news module with different parameters without monkeypatching globals.
    *   *Impact*: Reduces testability and violates the Open/Closed Principle.
*   **Environment Variable Coupling in Domain Logic**:
    *   Both `pipeline.py` and `data/merge.py` contain inline checks like `if os.environ.get("DEBUG") == "1":`. The domain code should not be aware of system environment variables. Validation toggles should be injected through configuration or managed via decorators.
    *   *Impact*: Blurs the line between system environment and domain rules, complicating testing and execution environments.
*   **Orchestrator Monolithism in `pipeline.py`**:
    *   `run_pipeline` does too much orchestration logic that could be encapsulated. For example, it directly manages the `concurrent.futures.ThreadPoolExecutor` for the news penalty pass instead of delegating the execution strategy to `apply_negative_news_penalty`.
    *   *Impact*: `pipeline.py` is bloated and overly aware of the news processing internals.

### P2 Findings (Minor)
*   **Pandera Schema Validation Pattern**:
    *   Schemas are validated procedurally via `Schema.validate(df)` inside `if` blocks. This clutters the core pipeline logic. The idiomatic approach in `pandera` is to use `@pa.check_output` or `@pa.check_types` decorators, which can be globally disabled/enabled based on configuration without bleeding into the functions themselves.
*   **Hardcoded I/O Expectations in `data/loader.py`**:
    *   `load_candidates_for_universe` expects specifically named files (`getiri.csv`, `buyukluk.csv`, `yonetim ucreti.csv`). While this matches TEFAS/BEFAS standard exports, it makes the data ingestion layer rigid to format changes.

## Recommended Fixes (Actionable Agent Prompts)

1.  **Extract News Configuration (P1)**:
    *   *Prompt*: "Refactor `config.py` to group all news-related constants into a `NewsConfig` dataclass. Update `PipelineConfig` to accept `news_config: NewsConfig | None`, and remove all direct imports of news constants from `pipeline.py`. Pass the config down to `apply_negative_news_penalty`."
2.  **Remove `os.environ` from Domain Code (P1)**:
    *   *Prompt*: "Remove `os.environ.get("DEBUG")` checks from `pipeline.py` and `data/merge.py`. Instead, use `validate_schemas` from `PipelineConfig` (for `pipeline.py`), and update `merge_universe` to accept a boolean flag or rely entirely on pandera decorators configured centrally."
3.  **Encapsulate Concurrency in News Module (P1)**:
    *   *Prompt*: "Move the `ThreadPoolExecutor` instantiation out of `pipeline.py` and into `apply_negative_news_penalty` in `fundexpert/news/penalty.py` or a dedicated wrapper. `pipeline.py` should just call the penalty function without worrying about thread management."
4.  **Adopt Pandera Decorators (P2)**:
    *   *Prompt*: "Refactor schema validation to use `pandera` decorators (`@pa.check_output`) on the pipeline transformation functions. Configure a central mechanism to enable/disable validation based on the `DEBUG` environment variable at startup, keeping the domain functions clean."
