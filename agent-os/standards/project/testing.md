# Project Testing Standards

## Core Testing Tooling
This project uses **`pytest`** as the primary testing framework, partnered with **`pytest-bdd`** for executing our Acceptance Criteria behavior-driven tests.

## Commands
*Ensure all commands are prefixed with `uv run` to guarantee isolated execution.*

- **Run all tests:** `uv run pytest`
- **Run specific test file:** `uv run pytest tests/path/to/test.py`
- **Verbose output (to see print statements):** `uv run pytest -vv -s`
- **Run BDD tests only:** `uv run pytest tests/features/`

## Testing Philosophy

### Behavior-Driven Development (BDD)
- Acceptance Criteria generated during the `/derive-acs` phase **MUST** be backed by `pytest-bdd` tests.
- Feature files (`.feature`) should identically match the `Given/When/Then` logic established in the AC markdown documents.
- Step definitions should be cleanly organized in `tests/step_defs/`.

### Unit tests
- Fast, isolated unit tests for core deterministic logic (e.g., chunking logic, URI parsing).
- **Mocking:** Use `unittest.mock` strictly to isolate tests from network access, disk I/O, or LLM inference. Validating logic should not require a live internet connection.

### Integration Tests
- Verify actual integrations with external systems or DBs. 
- For example, database operations should test against a real, ephemeral in-memory SQLite database (`:memory:`) to validate extensions like `sqlite-vec` behave as expected.

## Quality Gates
Test pass rate ensures behavioral correctness, but quality involves more than just passing tests:
- **Type Checking:** `uv run pyright` must pass completely without ignoring core typing rules.
- **Linting & Formatting:** `uv run ruff check` and `uv run ruff format --check` must pass. Code should be clean and standardized.
