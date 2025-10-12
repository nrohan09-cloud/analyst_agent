# Repository Guidelines

## Project Structure & Module Organization
`analyst_agent/` is the Python package; `core/` orchestrates the analysis graph, `api/` exposes FastAPI endpoints, `analysis/` holds agent logic, while `adapters/`, `data_sources/`, `models/`, and `sandbox/` support I/O and tooling. `frontend/` is the Vite + TypeScript UI (sources in `src/`, builds in `dist/`). Example workflows live in `examples/`; automation scripts and database helpers reside in `scripts/`, `start_demo.sh`, and `setup_test_db.py`. Tests live in `tests/`, with additional smoke checks (`test_setup.py`, `test_streaming.py`) in the repo root. Sample datasets and fixtures sit under `data/`, and the published TypeScript SDK is in `typescript-sdk/`.

## Build, Test, and Development Commands
Use `pip install -e .[dev]` inside a Python 3.10+ virtualenv. Start the service with `python main.py` or `uvicorn analyst_agent.api.app:app --reload`. Bring up the full stack via `docker-compose up`. Frontend work happens with `cd frontend && npm install && npm run dev`; bundle with `npm run build`. Quality gates: `ruff check .`, `black .`, and `mypy analyst_agent`. Regenerate the SDK with `cd typescript-sdk && npm run build`.

## Coding Style & Naming Conventions
Python code follows Black (88 cols), Ruff, and type-hinted functions. Use 4-space indentation, snake_case for modules/functions, PascalCase for classes, and SCREAMING_SNAKE_CASE for constants. Keep configuration in `.env` or `settings.py`; never commit keys. In the frontend, name components `ComponentName.tsx`, colocate tests next to sources, and prefer functional components with hooks prefixed by `use`.

## Testing Guidelines
Pyproject settings expect files named `test_*.py` under `tests/`. Run `pytest` locally; include `pytest --cov analyst_agent --cov-report=term-missing` before a PR and keep touched areas at ≥80% coverage. Mock external LLM calls and databases; store shared fixtures in `data/`. Reserve `test_setup.py` for quick environment checks and document any new end-to-end scripts.

## Commit & Pull Request Guidelines
Keep commit subjects imperative and under ~72 chars (e.g., `Improve sandbox logging`), mirroring the existing history. Reference related issues with `Refs #123` or `Fixes #123`. PRs must explain the change, list validation commands or screenshots, flag API/schema deltas, and call out follow-up work. Request reviews from affected owners (`core`, `frontend`, `sdk`) and wait for CI (lint, type, pytest) before merging.

## Security & Configuration Tips
Load provider credentials from `.env`; rotate any keys shown in docs. Ignore generated logs (`api.log`, `frontend.log`) and new secret files. Prefer `setup_test_db.py` or local connectors for demos instead of production instances, and scrub sample data before publishing.
