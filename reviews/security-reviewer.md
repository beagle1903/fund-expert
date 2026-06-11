# Security Review: Fund Expert

## Overview
A comprehensive security review of the `fundexpert` codebase was conducted. The codebase is generally sound, with no critical (P0) vulnerabilities found such as remote code execution or SQL injection. However, there are important findings related to insecure data handling, terminal markup injection, and dependency management.

---

## Findings

### 1. Insecure Directory Permissions for Application Data (P1 - High)
**Context:**
The application stores user-specific data, including generated portfolios (`runs/`), application state (`last.json`), and external API caches (`news_cache/`) within the `~/.fundexpert` directory.

**Issue:**
When these directories and files are created using `Path.mkdir(parents=True, exist_ok=True)`, they are created with the system's default permissions (subject to the OS umask). On a multi-user system, this could allow other local users to read the user's query history, financial choices, and generated portfolios.

**References:**
- `fundexpert/cli.py:215` (`LAST_RUN_FILE.parent.mkdir(...)`)
- `fundexpert/history/store.py:19` (`history_dir.mkdir(...)`)
- `fundexpert/news/tavily.py:124` (`cache_dir.mkdir(...)`)

**Suggested Fix Prompt:**
> "Update the application's file and directory creation logic to use strict permissions. Modify the `mkdir()` calls in `fundexpert/cli.py`, `fundexpert/history/store.py`, and `fundexpert/news/tavily.py` to include `mode=0o700` so that only the owner can read/write the `.fundexpert` directory contents."

---

### 2. Terminal Markup Injection via Untrusted External Data (P2 - Medium)
**Context:**
The application renders data from the TEFAS CSVs (`fon_adi`) and the external Tavily API (`title`, `source`) to the terminal using the `rich` library.

**Issue:**
The `rich` library automatically parses and evaluates specific markup tags (e.g., `[bold]`, `[link=...]`) embedded in strings unless explicitly escaped. If an external API response or CSV data contains these tags, it will be rendered as formatted text or clickable links in the user's terminal. A malicious news source could inject a deceptive clickable link (e.g., `[link=http://malicious.example.com]Click for more info[/link]`), which `rich` would present natively, leading to a potential phishing or client-side attack if clicked by the user.

**References:**
- `fundexpert/render/table.py` (Usage of `console.print` and `Table.add_row` with unescaped `item['title']`, `item['source']`, `r['fon_adi']`, and `r['umbrella_type']`)
- `fundexpert/render/diff.py` (Usage of `console.print` with unescaped `p['fon_adi']`)

**Suggested Fix Prompt:**
> "In `fundexpert/render/table.py` and `fundexpert/render/diff.py`, import `escape` from `rich.markup`. Wrap all untrusted string interpolations (such as `item['title']`, `item['source']`, `r['fon_adi']`, and `r['umbrella_type']`) with `escape()` before they are passed to `console.print()` or added to the `rich.table.Table`."

---

### 3. Unpinned Dependencies Leading to Supply Chain Risks (P2 - Medium)
**Context:**
The `pyproject.toml` file declares application dependencies using broad lower bounds (`pandas>=2.2`, `rich>=13.7`, `questionary>=2.0`).

**Issue:**
Without a lockfile (like `requirements.txt` via `pip-compile`, `poetry.lock`, or `uv.lock`), consecutive installations of the application may pull different versions of transitive dependencies. This introduces reproducibility issues and exposes the project to supply chain attacks if a transitive dependency releases a compromised or breaking update.

**References:**
- `pyproject.toml`

**Suggested Fix Prompt:**
> "Introduce a lockfile mechanism to the project to ensure deterministic builds. Add a step to generate a strict `requirements.txt` using a tool like `pip-compile` (from `pip-tools`), or migrate the dependency management to `uv` or `Poetry` so that exact versions of all transitive dependencies are securely locked."
