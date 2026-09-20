---
name: run
description: Starts or reuses the Fundexpert FastAPI backend and Vite frontend, verifies both local endpoints, prints the app URL, and opens it in Cursor's browser. Use when the user says /run, run Fund Expert, open the Fund Expert app or dashboard, or asks for its local URL.
---

# Run Fundexpert

Start the local app without duplicating healthy services, then open it in Cursor's browser.

## Workflow

1. From the repository root, run:

   ```powershell
   .\scripts\run.ps1
   ```

   Add `-EngineRoot '<absolute-path>'` only when the repository is not this workspace and `FUND_EXPERT_ROOT` is unset.
2. Parse the JSON result. Require `status: "success"`, `api.status: "healthy"`, and `ui.status: "healthy"` before claiming the app is ready. On failure the script still prints JSON (`status: "error"` plus `error`); do not treat a PowerShell exception as the only failure mode.
3. Open the returned `url` with Cursor's browser tools. Do not open Edge, Chrome, or another external browser.
4. Keep newly started services running. Report the clickable URL, whether each component was started or reused, and each newly started process ID.

## Failure handling

- Do not start a second copy of a healthy component that belongs to this checkout.
- If another process owns port 8000 or 5173, fail with JSON `status: "error"` and do not reuse it.
- If startup fails, report the returned error and log paths. Include only a short relevant log tail; do not claim the URL is ready.
- Do not change ports automatically. Port conflicts must fail clearly so the conflicting process can be inspected.
- Run `npm ci` only when the Vite executable is missing.
