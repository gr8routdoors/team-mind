# Python Code Style Standards

## Core Philosophy
- **Idiomatic Python:** Prioritize readability and clarity over cleverness. Follow PEP 8 guidelines.
- **Type Safety First:** Fully type-hinted code is required. Treat type hints as binding contracts.

## Tooling
- **Package Manager:** [uv](https://astral.sh/uv). Fast, unified Python version and dependency management.
- **Linter & Formatter:** [Ruff](https://astral.sh/ruff). Extremely fast, unified linting and formatting. Replaces Black, isort, and Flake8.
- **Type Checker:** [Pyright](https://microsoft.github.io/pyright/) (or Mypy). Strict type checking must pass.

## Typing Guidelines
- Every function explicitly requires typed arguments and a return type (e.g., `def parse_uri(uri: str) -> None:`).
- Use modern type hinting (`list[str]`, `dict[str, int]`, `str | None`).
- Avoid `Any` unless absolutely necessary (e.g., when dealing with opaque JSON from external plugins).

## Imports
- Use absolute imports over relative imports.
- Standard library imports first, followed by third-party imports, then local application imports. (Ruff's `isort` will handle this format automatically).

## Documentation
- Use Google-style docstrings for functions, classes, and complex logic.
- Modules should have a top-level docstring explaining their overarching purpose and public API.
- Prefer descriptive variable names to inline comments.

## Error Handling
- Catch specific exceptions, not broad `Exception` clauses.
- Raise custom domain-specific exceptions where standard Python exceptions do not carry enough semantic meaning (e.g., `class URINotFoundError(Exception)`).
