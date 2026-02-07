# Development Best Practices

> Core principles for writing maintainable, robust software.

---

## Keep It Simple

- Strive for simplicity and clarity
- Avoid overly complex logic, deep nesting, and redundant code
- Extract logic into functions, avoiding side-effects where possible
- **YAGNI** — You Ain't Gonna Need It. Don't over-engineer. Stick to the spec.

---

## SOLID Principles

| Principle | Meaning | Guidance |
|-----------|---------|----------|
| **S**ingle Responsibility | One reason to change | Each class/module does one thing well |
| **O**pen/Closed | Open for extension, closed for modification | Extend behavior without changing existing code |
| **L**iskov Substitution | Subtypes are substitutable | Derived classes don't break base class contracts |
| **I**nterface Segregation | Small, focused interfaces | Don't force clients to depend on unused methods |
| **D**ependency Inversion | Depend on abstractions | High-level modules don't depend on low-level details |

---

## Optimize for Readability

- Prioritize code clarity over micro-optimizations
- Use descriptive names for variables, methods, and classes
- Provide clear documentation for complex logic
- Code should be self-explanatory; comments explain "why", not "what"

---

## Test-Driven Development

- Write tests to verify code works (unit, integration, e2e)
- Prefer clear, readable test cases that describe behavior
- Avoid weak assertions that don't verify actual data
- Never use optional assertions guarded by null checks — use `assertNotNull` instead
- **Never remove or weaken assertions to fix broken tests** without explicit approval

---

## Error Handling

- Never swallow errors — always handle, log, or rethrow
- Catch specific exceptions, not generic ones
- Throw exceptions in core classes; handle at the top of the stack
- Only catch exceptions you can properly handle (e.g., retries)
- Ensure proper resource cleanup (try-with-resources, defer)

---

## Performance Mindset

- Choose appropriate data structures for the use case
- Minimize object creation in hot paths and loops
- Be aware of N+1 query patterns in database access
- Profile before optimizing — don't guess at bottlenecks

---

## Dependencies

When adding third-party dependencies:

- Select popular, actively maintained options
- Check for recent commits (within 6 months)
- Verify clear documentation and active issue resolution
- Prefer well-known libraries over obscure alternatives
- Consider the dependency's transitive dependencies

---

_Last updated: 2026-02-03_
