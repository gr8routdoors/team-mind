# Project Build Standards

## Tooling: `uv`
This project utilizes **[uv](https://astral.sh/uv)** as the standard Python package and project manager. `uv` is exceptionally fast, manages Python versions automatically, and eliminates the need for manual virtual environment management.

## Prerequisites
- macOS / Linux / Windows
- Install `uv`: 
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Homebrew: `brew install uv`

## Core Commands

### Setup & Installation
- **Initialize a project/repo:** `uv init`
- **Sync dependencies:** `uv sync` (Creates a virtual environment securely in `.venv` and installs all dependencies exactly as defined in `pyproject.toml` and locked in `uv.lock`).

### Running Code
- **Execute a script:** `uv run python script.py` 
- **Run a module:** `uv run python -m my_module`
*Note: `uv run` automatically uses the isolated `.venv` environment. You do not need to run `source .venv/bin/activate` manually.*

### Managing Dependencies
- **Add a runtime dependency:** `uv add <package>` (e.g., `uv add mcp sqlite-vec`)
- **Add a development dependency:** `uv add --dev <package>` (e.g., `uv add --dev pytest ruff`)
- **Remove a dependency:** `uv remove <package>`

## CI / Verification
Before asserting any completion of a feature, you should ensure the environment syncs cleanly and the required verification steps (testing, linting) execute successfully via `uv run`.
