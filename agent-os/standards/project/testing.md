# Project Testing Standards

## Core Testing Tooling
This project uses pure **`pytest`** as the primary testing framework. We reject Cucumber-style `.feature` files and fragmented step definitions in favor of highly readable, inline BDD tests.

## Commands
*Ensure all commands are prefixed with `uv run` to guarantee isolated execution.*

- **Run all tests:** `uv run pytest`
- **Run specific test file:** `uv run pytest tests/core/test_mcp_gateway.py`
- **Verbose output (to see print statements):** `uv run pytest -vv -s`

## Testing Philosophy

### Behavior-Driven Development (BDD) via Inline Pytest
- Acceptance Criteria generated during the `/derive-acs` phase **MUST** be mapped directly to `pytest` test functions.
- We do not use `pytest-bdd`. The "Feature file" concept is redundant since our ACs are already documented in markdown.
- Tests should be written in a single location with clear structural comments (`# Given`, `# When`, `# Then`) dividing the setup, execution, and assertion phases.
- Test names should clearly reference the AC they cover.

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
