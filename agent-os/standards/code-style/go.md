# Go Style Guide

> Conventions for Go code, based on Effective Go and community standards.

---

## Core Philosophy

Go emphasizes simplicity, readability, and consistency. The language provides tools like `gofmt` to eliminate style debates. Write code that is easy for other Go programmers to understand.

---

## Formatting

### gofmt is Non-Negotiable
- All Go code must be formatted with `gofmt`
- No exceptions — this is enforced in CI
- Use `goimports` to also manage imports automatically

### Indentation
- Tabs for indentation (gofmt enforces this)
- No hard line length limit, but keep lines reasonable

---

## Naming

Go has strong naming conventions that affect visibility and idiomatic usage.

### Visibility
- **Exported** (public): `UpperCamelCase` — visible outside package
- **Unexported** (private): `lowerCamelCase` — package-internal only

### Packages
- Short, concise, lowercase, single-word names
- No underscores or mixedCaps
- Avoid meaningless names: `util`, `common`, `misc`, `helpers`
- Package name should describe what it provides, not what it contains

### Functions & Methods
- `MixedCaps` (exported) or `mixedCaps` (unexported)
- No `Get` prefix for getters: field `owner` → method `Owner()`, not `GetOwner()`
- Setters use `Set` prefix: `SetOwner()`

### Interfaces
- One-method interfaces: method name + `-er` suffix
- Examples: `Reader`, `Writer`, `Formatter`, `Stringer`
- Keep interfaces small — prefer composition

### Constants
- `MixedCaps` even for constants (not `SCREAMING_SNAKE_CASE`)
- Exported: `MaxRetryCount`
- Unexported: `maxRetryCount`

### Variables
- Short names for short scopes: `i`, `n`, `err`
- Longer names for longer scopes and broader visibility
- Receivers: short (1-2 letters), consistent across methods

---

## Imports

- Group imports with blank lines between groups:
  1. Standard library
  2. Third-party packages
  3. Internal/local packages
- Avoid renaming imports unless necessary to resolve conflicts
- Never use dot imports (`. "package"`)

```go
import (
    "context"
    "fmt"

    "github.com/pkg/errors"

    "github.com/some/internal/api"
)
```

---

## Error Handling

### Always Handle Errors
- Never discard errors with `_`
- Check every error return value
- Handle it, return it, or in truly exceptional cases, panic

### Error Strings
- Lowercase, no punctuation at end
- Will be concatenated with other context: `fmt.Errorf("open file: %w", err)`

### Error Wrapping
- Use `fmt.Errorf` with `%w` to wrap errors and preserve the chain
- Add context about what operation failed

```go
if err != nil {
    return fmt.Errorf("get user %s: %w", userID, err)
}
```

### When Panic is Acceptable
- Only for truly unrecoverable situations (nil dereference, impossible state)
- Never for normal error handling
- `Must` prefix functions may panic on initialization: `MustCompile`, `MustParse`

---

## Control Flow

### Early Returns
- Prefer early returns to reduce nesting
- Handle errors first, then happy path

```go
// Good
if err != nil {
    return err
}
// continue with success case

// Avoid
if err == nil {
    // deeply nested success case
}
```

### Switch Statements
- No `break` needed (implicit)
- Use `fallthrough` keyword if needed (rare)
- Prefer switch over long if-else chains

---

## Concurrency

### Goroutines
- Always know how a goroutine will exit
- Use `context.Context` for cancellation
- Don't start goroutines you can't stop

### Channels
- Sender closes, receiver checks for close
- Prefer unbuffered channels unless you have a specific reason
- Document channel ownership and lifecycle

### sync Package
- Use `sync.Mutex` for protecting shared state
- Prefer channels for coordination, mutexes for state protection
- `sync.WaitGroup` for waiting on multiple goroutines

---

## Structs & Methods

### Struct Design
- Group related fields together
- Zero value should be useful when possible
- Use constructor functions for complex initialization: `NewOrderProcessor()`

### Method Receivers
- Use pointer receivers for methods that modify state
- Use value receivers for small, immutable types
- Be consistent within a type — don't mix receiver types

```go
// Pointer receiver — modifies state
func (p *Processor) SetRate(rate decimal.Decimal) {
    p.rate = rate
}

// Value receiver — read-only, small type
func (p value) String() string {
    return p.amount.String()
}
```

---

## Testing

- Test files: `*_test.go` in same package
- Test functions: `TestXxx(t *testing.T)`
- Table-driven tests for multiple cases
- Use `t.Helper()` in test helper functions
- Subtests with `t.Run()` for grouping related cases

---

## Documentation

- Package comment: First sentence is package summary
- Exported functions: Comment starts with function name
- Complete sentences, proper punctuation

```go
// Package auth provides user authentication and authorization.
package auth

// Authenticate validates credentials and returns a session token
// with appropriate permissions and expiry.
func Authenticate(ctx context.Context, req *Request) (*Session, error) {
```

---

## References

- [Effective Go](https://go.dev/doc/effective_go)
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)
- [Google Go Style Guide](https://google.github.io/styleguide/go/)
- [Uber Go Style Guide](https://github.com/uber-go/guide/blob/master/style.md)

---

_Last updated: 2026-02-03_
