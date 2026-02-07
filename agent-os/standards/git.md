# Git Standards

> Conventions for commits, branches, and pull requests.

---

## Conventional Commits

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to Use |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, missing semicolons (no code change) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `chore` | Maintenance tasks, dependency updates |
| `ci` | CI/CD changes |
| `build` | Build system or external dependency changes |

### Scope

Scope is optional but recommended. Use the component or area affected:

- `some-service`, `another-service`
- `api`, `db`, `auth`
- `deps`, `config`

### Examples

```
feat(component): add some feature for some thing

fix(api): handle null entity IDs in value request

docs(readme): update local development setup instructions

refactor(component): extract rate lookup into separate service

test(component): add coverage for edge cases in order processing

chore(deps): bump spring-boot to 3.2.1
```

### Breaking Changes

For breaking changes, add `!` after the type or include `BREAKING CHANGE:` in the footer:

```
feat(api)!: change response format for value endpoint

BREAKING CHANGE: value field renamed from `amount` to `totalvalue`
```

---

## Branch Naming

```
<type>/<ticket>-<short-description>
```

### Examples

```
feat/ticket_number-feature-title
fix/ticket_number-fix-title
chore/ticket_number-chore-title
```

### Types

- `feat/` — New features
- `fix/` — Bug fixes
- `refactor/` — Refactoring
- `chore/` — Maintenance
- `docs/` — Documentation
- `test/` — Test additions/fixes

---

## Pull Requests

### Title
Follow conventional commit format:
```
feat(component): add some feature for some thing
```

### Description
Include:
- **What** — Brief description of the change
- **Why** — Context and motivation
- **Testing** — How it was tested
- **Jira** — Link to ticket

### Checklist
- [ ] Tests added/updated
- [ ] Documentation updated (if needed)
- [ ] No unrelated changes included
- [ ] Conventional commit message used

---

## Commit Hygiene

- **Atomic commits** — Each commit should be a single logical change
- **Buildable commits** — Each commit should compile and pass tests
- **Squash fixups** — Squash "fix typo" and "address review" commits before merge
- **Meaningful history** — Commits should tell the story of the change

---

## Merge Strategy

- **Squash merge** for feature branches (clean history)
- **Merge commit** for release branches (preserve history)
- **Rebase** your branch on main before creating PR

---

_Last updated: 2026-02-03_
