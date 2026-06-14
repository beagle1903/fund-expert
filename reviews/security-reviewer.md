# Security Review: fundexpert

## Executive Summary
A comprehensive security review of the `fundexpert` codebase was performed, focusing on injection risks, hardcoded secrets, unsafe practices (e.g., `eval`, `pickle`, unsafe `yaml`), and other common vulnerabilities. The codebase is well-structured and actively follows good security practices.

## Findings

### P0 (Critical)
None found.

### P1 (High)
None found.

### P2 (Low / Best Practices)
1. **Hardcoded Secret Defense Mechanism (Safe):** 
   The codebase successfully avoids hardcoding the `TAVILY_API_KEY` by loading it from the environment (`os.environ.get(NEWS_API_KEY_ENV)` in `cli.py`). This is the correct approach.
2. **CSV Parsing Bounds (Safe):**
   `data/loader.py` enforces a `MAX_CSV_SIZE_BYTES` constraint (50MB) before parsing any CSV files into pandas DataFrames. This successfully mitigates Denial of Service (DoS) attacks via memory exhaustion from massive files.
3. **Unsafe Methods and Deserialization (Safe):**
   No usages of `eval()`, `exec()`, or `pickle` were found in the project. Deserialization correctly employs safe alternatives like `json.loads` natively.
4. **Network Request Security (Safe):**
   `news/tavily.py` performs safe API calls. It explicitly verifies that outgoing connections are established over HTTPS (`if not req.full_url.startswith("https://"): raise ValueError(...)`) and utilizes TLS context validation correctly (`ssl.create_default_context()`).
5. **Path Traversal Prevention (Safe):**
   File writing operations establish paths securely. The `_cache_key` computation in `tavily.py` securely hashes query elements and configuration into a SHA-256 digest, preventing any potential path traversal vulnerability. History files also rely on safe `datetime` outputs and locally defined enum choices.
6. **File Permissions (Safe):**
   Data/history persistence methods use temporary files cleanly and securely, actively enforcing restrictive read/write permissions (`os.chmod(tmp_name, 0o600)` found in `store.py`, `ui.py`, and `tavily.py`). This minimizes risks of local file hijacking or credential leaks to other OS users.

## Conclusion
The `fundexpert` codebase exhibits strong defensive coding practices. No critical or high-priority security vulnerabilities were identified in the core pipeline, logic, or CLI wrappers.
