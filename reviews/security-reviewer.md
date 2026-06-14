# Security Review: fundexpert

## Executive Summary
A comprehensive security review was conducted on the `fundexpert` codebase. The architecture demonstrates a fundamentally strong security posture and adheres to multiple best practices. Threat modeling focused on inputs (CLI arguments, CSV files, configuration), data handling (JSON caches, DataFrame processing), and common attack vectors (Command Injection, SSRF, Path Traversal, Terminal Injection). 

**No critical (P0) or high-severity vulnerabilities were found.** The application correctly enforces type casting on CLI inputs, restricts local file reads to explicitly allowed directory subsets, leverages purely safe serialization formats (JSON), and escapes dynamically retrieved text before terminal rendering.

A few medium and low-severity findings (P1/P2) were identified primarily concerning software supply chain risks and explicit networking security configurations.

---

## Detailed Findings

### P1: Lack of Dependency Lockfile (Supply Chain Risk)
* **Location:** `requirements.txt` and `pyproject.toml`
* **Description:** The project relies on lower-bound version pinning (e.g., `pandas>=2.2`, `rich>=13.7`). This introduces a significant supply-chain risk. If a malicious or broken update is published for any of these libraries (or their transitive dependencies), users installing `fundexpert` could automatically pull the compromised versions.
* **Impact:** High impact, but standard likelihood for un-locked python environments.
* **Recommended Fix:** Adopt a lockfile mechanism (such as `pip-tools` to generate a frozen `requirements.txt`, or standardizing on `Poetry`/`uv` with `uv.lock`) to ensure deterministic and strictly hashed dependency resolution.

### P2: Explicit TLS Context Enforcement Not Specified
* **Location:** `fundexpert/news/tavily.py` (`_post_tavily` function)
* **Description:** The application makes outgoing network requests to the Tavily API using `urllib.request.urlopen()`. While the code explicitly verifies the `https://` scheme (preventing SSRF via arbitrary schemes like `file://`), it does not explicitly construct and pass a strict `ssl_context`. It relies entirely on the system's default Python SSL environment.
* **Impact:** Low. Modern Python versions (>= 3.4) enforce TLS verification by default, but passing an explicit `ssl.create_default_context()` hardens the request against environments where the default may have been globally weakened.
* **Recommended Fix:** 
  ```python
  import ssl
  context = ssl.create_default_context()
  with urllib.request.urlopen(req, timeout=timeout_seconds, context=context) as resp:
  ```

### P2: Silent JSONDecodeError on Oversized API Responses
* **Location:** `fundexpert/news/tavily.py` (`_post_tavily` function)
* **Description:** As a Denial of Service (DoS) mitigation, the code safely bounds the API response body by reading a maximum of 5MB: `raw_data = resp.read(5 * 1024 * 1024)`. If Tavily were to return a payload larger than 5MB, the JSON would be abruptly truncated, resulting in a silent `json.JSONDecodeError` during `json.loads()`.
* **Impact:** Low. It gracefully fails-soft and logs a warning without crashing the pipeline, but legitimate hits would be ignored.
* **Recommended Fix:** If the payload strictly hits the 5MB boundary (`len(raw_data) == 5242880`), consider logging a specific "Response too large" warning to differentiate it from malformed responses, or gracefully parsing the partial content if feasible (though typically invalid JSON).

### P2: Temporary File Permission Race Condition (Windows vs Unix)
* **Location:** `fundexpert/ui.py` and `fundexpert/history/store.py`
* **Description:** The codebase secures local files (history, caches) by creating temp files and explicitly executing `os.chmod(tmp_name, 0o600)` after the content is written but before they are moved. On POSIX environments, `tempfile.NamedTemporaryFile` inherently creates the file with `0o600` permissions. On Windows, however, it inherits default directory ACLs until `os.chmod` is called.
* **Impact:** Very Low. Since the application explicitly enforces `mode=0o700` on the parent directories (e.g., `~/.fundexpert`), the risk of local user data exposure is functionally mitigated before the file is even created.
* **Recommended Fix:** No immediate action required, but noting that Windows ACLs handle `os.chmod` loosely; maintaining the strict parent directory permission (`0o700`) is the correct primary defense.

---

## Positive Security Practices Highlighted (What went right)
* **Terminal Injection / XSS Prevention:** The `render_portfolio` function meticulously applies `rich.markup.escape()` to all dynamically loaded strings (such as `fon_adi`, URL sources, and news titles). This protects the terminal from malicious markup manipulation.
* **Safe Serialization:** Exclusively uses `json` for storing/loading state, entirely avoiding dangerous Python `pickle` deserialization.
* **Defense-in-Depth for Denial of Service:**
  * Local CSV files are strictly verified to be under 50MB before parsing.
  * API response bodies are capped at a 5MB read limit.
  * RegEx usage for mapping rules (e.g., `\bOKS\b`) is linear and resistant to Catastrophic Backtracking (ReDoS).
* **Environment Variable Secret Handling:** The `TAVILY_API_KEY` is loaded directly via the environment, skipping the CLI argument parser entirely. This actively prevents the API key from leaking into `.bash_history` or process monitoring tools.
* **Secure Cache Key Generation:** File paths for cached responses use a SHA256 digest of the query/domains. This completely neutralizes any Path Traversal attempts via maliciously crafted fund names.
