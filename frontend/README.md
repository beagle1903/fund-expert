# Fundexpert Web UI

React/Vite dashboard for the local Fundexpert FastAPI service.

## Commands

From the repository root:

```powershell
npm --prefix frontend install
npm --prefix frontend run dev
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
```

The development and preview servers proxy relative `/api` requests to
`http://127.0.0.1:8000`, or to the port in `FUNDEXPERT_API_PORT` when that is
set. Start the backend with:

```powershell
.venv\Scripts\python.exe -m uvicorn fundexpert.api:app --reload
```

The UI intentionally uses the stable projected API fields rather than raw
DataFrame columns. Data export provenance comes from `data_snapshot` in every
generation response.
