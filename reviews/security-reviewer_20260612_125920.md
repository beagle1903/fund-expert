# Security Review: fundexpert

**Date:** 2026-06-12
**Reviewer:** Security Subagent

## Executive Summary
A comprehensive security review of the `fundexpert` codebase has been completed. The application exhibits a strong security posture with robust input validation, secure file handling, and safe external API interactions. No high-severity vulnerabilities (P0/P1) were found. 

## Findings

### P2 (Low/Info): File Permissions on Windows for Temp Files
- **Location:** `fundexpert/history/store.py` and `fundexpert/cli.py` (cache writing mechanisms)
- **Description:** The codebase correctly uses `tempfile.NamedTemporaryFile` combined with `os.replace` for atomic file writes. While directories are created with `mode=0o700`, Windows handles permissions differently (ACLs), meaning temp files could inherit broader permissions than intended if the parent directory (like `%TEMP%`) allows it.
- **Recommendation:** No immediate action required, but if sensitive user configurations or portfolios are stored and the CLI runs on a shared system, consider explicitly applying restrictive ACLs to the cache files.

### Security Positives (What the codebase does well)
1. **Safe Serialization:** The application exclusively uses `json` for serialization and caching. No unsafe formats like `pickle` or `yaml.load` are present, completely mitigating arbitrary code execution risks from deserialization.
2. **Denial of Service Protection:** `fundexpert/data/loader.py` enforces a `MAX_CSV_SIZE_BYTES` limit before reading user-provided CSV files via `pandas`, protecting against memory exhaustion and large file DoS attacks.
3. **Safe API Integration:** External requests to Tavily in `fundexpert/news/tavily.py` are strictly made over HTTPS. The API key is securely loaded from environment variables rather than being hardcoded or logged. `json.JSONDecodeError` and timeout exceptions are caught gracefully.
4. **Command Injection Prevention:** There are no instances of `subprocess`, `os.system`, `eval`, or `exec` in the execution path. All parameters are passed safely and external data is treated as strings.
5. **Input Validation:** User inputs are tightly constrained via `questionary` choices and `argparse` types, effectively mitigating path traversal and injection from malicious interactive or CLI inputs.

## Conclusion
The codebase is highly secure for its intended use as a CLI application. The data handling, caching, and external networking components are implemented defensively.
