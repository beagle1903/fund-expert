# Security Review — 2026-06-12

## Executive Summary
A deep security audit of the `fundexpert` codebase was performed. The application generally exhibits a secure design with no remote code execution (RCE) or SQL injection vulnerabilities, and it safely handles the `TAVILY_API_KEY` by sending it exclusively within the body of HTTPS POST requests. However, three key security findings were identified. The most significant (P1) is a Rich markup injection vulnerability that could allow malicious terminal output manipulation. Two secondary risks (P2) involve local arbitrary file overwrite via symlink attacks on cache files, and a minor Denial of Service (DoS) risk through unbounded CSV file loading.

## Findings

### [P1] Terminal Output Manipulation / Rich Markup Injection
- **File(s)**: `fundexpert/render/table.py` (lines 80, 90, 115, 131)
- **Issue**: The application renders untrusted string data—such as fund names from user-supplied CSV files and news titles/URLs from the external Tavily API—directly to the terminal using the `rich` library. Because `Console.print` and `Table.add_row` parse markup tags by default, an attacker who controls the CSV or a compromised news website can embed tags like `[bold]`, `[clear]`, or `[link=file:///...]` in their data. This can be exploited to manipulate the terminal display, hide vital content, or drop malicious click-to-execute links.
- **Risk**: P1. Can be used to trick the user into executing arbitrary commands via hidden terminal links or obfuscating risk levels.
- **Recommendation**: Import `escape` from `rich.markup` and use it to escape untrusted strings before rendering them.
- **Agent Prompt**: "Fix Rich markup injection in `fundexpert/render/table.py`. Import `rich.markup.escape` and wrap all untrusted variables (e.g., `item['title']`, `item['url']`, `item['source']`, `r['fon_adi']`) with `escape()` before passing them to `console.print` or `table.add_row`."

### [P2] Arbitrary File Overwrite via Symlink Attack on Cache Files
- **File(s)**: `fundexpert/history/store.py` (line 44), `fundexpert/cli.py` (line 72), `fundexpert/news/tavily.py` (line 126)
- **Issue**: The application writes state and cache data to predictable paths within `~/.fundexpert/` (e.g., `last.json`, `news_cache/<hash>.json`) using `Path.write_text()`. If an attacker with local access pre-creates these files as symbolic links to sensitive targets (e.g., system config files), running the tool will overwrite the targets with JSON output because `write_text` blindly follows symbolic links.
- **Risk**: P2. Local arbitrary file overwrite, restricted to environments with shared local user access.
- **Recommendation**: Write data to a temporary file in the target directory using `tempfile.NamedTemporaryFile`, then securely rename it to the final filename using `os.replace()`. This atomic swap mitigates symlink following.
- **Agent Prompt**: "Fix symlink arbitrary file overwrite vulnerabilities in `fundexpert/cli.py` (`_save_last_run`), `fundexpert/history/store.py` (`save_run`), and `fundexpert/news/tavily.py` (`_write_cache`). Update file writing logic to write to a temporary file using `tempfile.NamedTemporaryFile(delete=False, dir=path.parent)` and then commit the file via an atomic `os.replace()`."

### [P2] Unbounded Memory Consumption during CSV Loading (Denial of Service)
- **File(s)**: `fundexpert/data/loader.py` (lines 46-53)
- **Issue**: The `pd.read_csv` function loads user-supplied CSV files entirely into memory without size validation or chunking. Processing an extremely large, maliciously crafted CSV file can cause Python to exhaust available memory and crash the application.
- **Risk**: P2. Causes application crash (OOM Denial of Service). The impact is limited to local execution.
- **Recommendation**: Validate `path.stat().st_size` against a reasonable upper limit (e.g., 50 MB) before invoking `pd.read_csv()`, and raise an informative error if the file is excessively large.
- **Agent Prompt**: "Harden `fundexpert/data/loader.py` against overly large CSV files to prevent Out-of-Memory Denial of Service. Check the file size using `path.stat().st_size` before calling `pd.read_csv`, and raise a `ValueError` if the file size exceeds 50MB."
