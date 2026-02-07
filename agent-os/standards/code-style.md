# Code Style Guide

> General formatting principles and language-specific references.

---

## General Principles

### Formatting
- Use automated formatters where available (`gofmt` for Go, IDE formatters for Java)
- Consistent indentation within each language's conventions
- Keep line lengths reasonable (100-120 chars for Java, no hard limit for Go but be sensible)

### Naming
- Names should be descriptive and reveal intent
- Avoid abbreviations unless universally understood
- Match the conventions of the language you're writing

### Comments
- Explain the "why", not the "what"
- Document non-obvious business logic
- Keep comments up to date when modifying code
- Never remove existing comments unless removing the associated code

### File Organization
- One primary type/class per file
- Group related functionality together
- Keep files focused on a single responsibility

---

## Language-Specific Guides

Select the appropriate guide based on what you're working on:

| Language | Guide | When to Use |
|----------|-------|-------------|
| Java | [java.md](code-style/java.md) | Existing services, Spring Boot, Vaadin |
| Go | [go.md](code-style/go.md) | New services and rewrites |

---

## GraphQL Conventions

For GraphQL schema and query design:

- **Schema-first development** — Define schema before implementation
- **Naming**: Types in `PascalCase`, fields in `camelCase`, enums in `SCREAMING_SNAKE_CASE`
- **Nullability**: Be explicit — use `!` for required fields
- **Descriptions**: Document all types and fields in the schema
- **Queries vs Mutations**: Queries are read-only, mutations change state

---

_Last updated: 2026-02-03_
