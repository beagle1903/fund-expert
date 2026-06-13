# Architecture Review: Fund Expert

## Overview
`fundexpert` follows a robust procedural pipeline architecture. The application revolves around a well-defined sequence of stateless transformations on Pandas DataFrames. Data flow proceeds predictably:
Data Loading/Merging -> Scoring -> Domain Selection (Sector/Strategy Caps) -> Weight Allocation -> Rendering.

## Findings: Separation of Concerns

### Strengths
- **Pipeline Stage Isolation**: Distinct modules (`loader`, `scoring`, `select`, `render`) handle focused domain steps. The system acts on DataFrames sequentially without hidden state mutations or circular dependencies.
- **Schema Validation**: The data ingestion layer leverages `pandera` schemas (`data/merge.py`), ensuring clean, strongly-typed data structures before hitting core business logic.
- **News Module Encapsulation**: The negative-news system (`news/penalty.py`) perfectly abstracts its complexity. External API orchestration, caching, and concurrent ThreadPool execution are fully hidden from the mainline pipeline. The module implements a robust fail-soft design.
- **Orthogonal Selection Logic**: The domain concepts of `Strategy` and `Sector` are treated as independent limits. This prevents portfolio concentration gracefully, acknowledging domain realities (e.g. "Tech" funds mapping to multiple strategy umbrellas).

### Areas for Improvement
- **`cli.py` Responsibility Overload**: The `cli.py` module orchestrates user prompting, argument parsing, file I/O (last-run history saving), character encoding (`_ensure_utf8_stdio`), *and* pipeline invocation. Extracting the prompting logic and history management into a `session` or `config_builder` module would drastically improve separation of concerns.
- **Leaky Text Normalization**: Turkish string capitalization `(df["fon_adi"].str.replace("i", "İ").str.replace("ı", "I").str.upper())` happens inline within `pipeline.py`. `select/strategy.py` explicitly states it assumes strings are "already fully normalized and uppercased by pipeline.py". This logic should be centralized into a reusable `utils/string.py` function, or pushed upstream into the `clean_candidates` preprocessing step.
- **Pipeline Return Signature**: `run_pipeline` returns a bulky 4-element tuple (`weighted, header, hits_for_render, news_meta`). Refactoring this to yield a `PipelineResult` dataclass would create a cleaner, less fragile API interface for the rendering stage.
- **Counter-factual Analysis Bleed**: `pipeline.py` recalculates a counter-factual portfolio (`scored_pre`) to determine which funds were displaced by news penalties. While functionally correct, this clutters the primary orchestrator with analytical "what-if" logic.

## Maintainability & Quality
- **Extensive Test Coverage**: The `tests/` directory boasts comprehensive module-level coverage (20 distinct test files). This aligns excellently with maintainability goals.
- **Centralized Configuration**: `config.py` acts as a highly effective single source of truth for tunable business logic (priority weights, risk lambdas, API constraints, and cache policies).
- **Clear Code Conventions**: Type hinting is heavily utilized, leading to an auditable and highly readable codebase.

## Actionable Recommendations
1. **P1: Centralize Normalization**: Create a `utils/string.py` helper for Turkish character uppercase normalization and apply it during the data merge or clean steps.
2. **P2: Refactor Pipeline Outputs**: Introduce a `PipelineResult` dataclass in `pipeline.py` to encapsulate the multiple artifacts returned by the pipeline.
3. **P3: Decouple CLI**: Extract the interactive questionary routines and `_save_last_run`/`_load_last_run` mechanisms into a dedicated UI/state controller separate from CLI entry and arg parsing.
