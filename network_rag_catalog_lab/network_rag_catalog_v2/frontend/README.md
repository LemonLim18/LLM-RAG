# Network Orchestration Workbench — Iteration 1

This directory contains the VS Code-inspired workbench shell. Devices, configurations, chat messages and activity entries remain local sample fixtures. The shell calls only FastAPI's passive health/runtime-status endpoints; it does not call V9 planning, Ollama, NetBox or any device.

## Prerequisites

- Node.js 24 (the implementation was verified with `v24.11.0`)
- npm 11 (verified with `11.6.2`)
- Chrome for the Playwright smoke test

## Install and run in Windows PowerShell

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd install
npm.cmd run dev -- --host 127.0.0.1
```

Start the backend from the repository root in another PowerShell window:

```powershell
& 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\.venv\Scripts\python.exe' `
  -m uvicorn app.workbench.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:5173`. The Vite development server proxies `/api` to `VITE_DEV_API_TARGET`, which defaults to `http://127.0.0.1:8000`. A deployed frontend can set `VITE_API_BASE_URL` at build time. Press `Ctrl+C` in each terminal to stop the services.

## Verification

```powershell
Set-Location 'C:\Users\limmi\OneDrive\Desktop\LLM_RAG_Practice\network_rag_catalog_lab\network_rag_catalog_v2\frontend'
npm.cmd run build
npm.cmd run lint
npm.cmd run test:e2e
```

The browser smoke test uses the installed Chrome channel. In-memory edits and mock conversations intentionally reset when the page reloads.
