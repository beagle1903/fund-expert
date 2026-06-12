# Architecture Review: fundexpert

## Overview
A comprehensive architecture review of the `fundexpert` codebase. The application adopts a robust, functional pipeline approach utilizing `pandas` DataFrames, and clearly separates concerns across well-defined modules.

## Findings

### P0 - None

### P1 - Complex Parameter Passing in Pipeline
* **Issue**: The core orchestrator function `run_pipeline` (in `pipeline.py`) accepts 12 distinct arguments (e.g., `candidates`, `universe`, `risk_level`, `horizon`, `volume_priority`, `n`, `news_enabled`, etc.). This causes bloat and tightly couples `cli.py` parsing directly to the function signature.
* **Recommendation**: Introduce a `PipelineConfig` or `RunRequest` dataclass. This object should encompass all the configuration parameters (vade, risk, news options, etc.). Passing a single configuration object will clean up the signature of `run_pipeline`, making future additions (e.g., new tunables) seamless and easier to test.

### P2 - News Logic and Counterfactual Coupling
* **Issue**: `pipeline.py` currently handles a significant amount of conditional logic specifically for the news penalty, including running a "counterfactual" `pick_top` on a `scored_pre` dataframe to identify "displaced" funds. Additionally, low-level news cache TTLs and keys are injected all the way down from the config/cli through `pipeline.py`.
* **Recommendation**: Encapsulate the entire news integration—including the counterfactual evaluation—into a dedicated `NewsProcessor` class or a `apply_news_stage` function. It should accept the pre-news `DataFrame` and a `NewsConfig` dataclass, returning a composite object containing the updated `DataFrame`, `hits_by_code`, and `news_meta` (including displaced funds).

### P2 - Implicit DataFrame Schemas
* **Issue**: Throughout the application, functions expect certain columns to exist on the DataFrame (e.g., `aum_change_pct`, `R`, `score`) implicitly. While `loader.py` maps CSV columns to expected names, there is no formal schema validation or type checking on the DataFrames passing between stages. A slight change in TEFAS/BEFAS export schemas could lead to obscure errors deep in `scoring/` or `select/`.
* **Recommendation**: Implement a formal DataFrame schema validation step right after `merge_universe` and possibly at stage boundaries. Consider using a library like `pandera` to enforce column presence, types, and constraints explicitly.

## Strengths
- **Functional Pipeline**: The flow of data transformations (`clean` -> `horizon` -> `score` -> `news` -> `pick` -> `weights`) is exceptionally clear and avoids mutating state unpredictably, returning new or copied DataFrames.
- **Module boundaries**: `cli.py` handles user interaction exclusively, `render/` handles only output formatting, and core logic sits in decoupled `scoring/` and `select/` modules. This ensures high testability.
- **Vulture Results**: Checked with `vulture fundexpert/` – no dead code detected.
