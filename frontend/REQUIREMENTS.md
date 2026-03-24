# Frontend Requirements

To run the React + Tailwind frontend locally:

- Node.js: 20.19.0 or newer (or 22.12+)
- npm: 10+

Environment
- Copy .env.example to .env and adjust values as needed:
  - VITE_API_BASE=http://localhost:8000/api

Install and start (PowerShell):
1. cd C:\Yashraj\VIT\frontend_converted\frontend
2. npm install
3. npm start

If PowerShell blocks npm.ps1, either run `npm.cmd start` or run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

This starts Vite dev server (default: http://localhost:5173).

Notes
- TailwindCSS is configured via PostCSS (postcss.config.js) and tailwind.config.ts.
- Routing uses react-router-dom; UI is unchanged from the original.

Optional: Backend (FastAPI) for API integration
- The app reads the API base from VITE_API_BASE; default is http://localhost:8000/api
- Typical FastAPI deps:
  - fastapi
  - uvicorn[standard]
- Example request (from client code):
  fetch(`${import.meta.env.VITE_API_BASE}/suggestions`)
