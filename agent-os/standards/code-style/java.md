# Java Style Guide

> Conventions for Java code.

---

## File Structure

- File encoding: UTF-8
- One top-level class per file
- File name = class name + `.java`
- Order: license/copyright → package → imports → class
- One blank line between sections

---

## Imports

- **No wildcard imports** (`import java.util.*` forbidden)
- Order: static imports → non-static imports (blank line between)
- ASCII sort order within blocks
- No static import for nested classes

---

## Formatting

### Braces
- Always use braces for `if/else/for/do/while` (even single statements)
- K&R style (Egyptian brackets):
  - No line break before opening `{`
  - Line break after opening `{`
  - Line break before closing `}`

### Indentation
- +2 spaces per block level (no tabs)
- Continuation lines: +4 spaces minimum

### Line Length
- Column limit: 100 characters
- Exceptions: long URLs, package/import statements, text blocks

### Whitespace
**Required single space:**
- After keywords: `if (`, `for (`, `catch (`
- Before opening braces: `method() {`
- Around binary/ternary operators: `a + b`, `a ? b : c`
- Around lambda arrows: `x -> y`
- After commas: `a, b`

**No space:**
- Method references: `Object::toString`
- Dot operators: `object.method()`

---

## Naming

| Element | Convention | Example |
|---------|------------|---------|
| Package | `lowercase` | `org.some.thing` |
| Class | `UpperCamelCase` | `OrderProcessor` |
| Method | `lowerCamelCase` | `processOrder` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT` |
| Field/Variable | `lowerCamelCase` | `orderTotal` |
| Type Variable | Single capital or `ClassNameT` | `T`, `RequestT` |

### Getters/Setters
- Getter for field `owner`: use `getOwner()` (standard JavaBean convention)
- Boolean getters: prefer `isEnabled()` over `getEnabled()`

### Test Classes
- Name ends with `Test`: `OrderProcessorTest`

---

## Programming Rules

### Required
- `@Override` annotation always used when overriding
- Caught exceptions must be handled (logged, rethrown, or commented why ignored)
- Static members qualified with class name: `Foo.staticMethod()`

### Forbidden
- Finalizers (`Object.finalize()`)
- Wildcard imports
- C-style array declarations: use `String[] args` not `String args[]`

---

## Switch Statements

- Prefer new-style (`->`) over old-style (`:`) in Java 14+
- Every switch must be exhaustive (include `default`)
- Old-style: comment fall-through with `// fall through`

---

## Annotations

- **Class**: One per line after Javadoc
- **Method**: One per line (except single parameterless)
- **Field**: Multiple allowed on same line
- **Type-use**: Immediately before type (`@Nullable String`)

---

## Javadoc

- Required for all public classes and members
- Exception: Self-explanatory members (`getFoo()`)
- Exception: Override methods (inherits parent doc)
- Summary fragment: Noun/verb phrase, not complete sentence
- Block tags order: `@param` → `@return` → `@throws` → `@deprecated`

---

## Modifiers Order

```
public protected private abstract default static final sealed non-sealed
transient volatile synchronized native strictfp
```

---

## Style Preferences

- Use `Optional` over null checks when returning potentially absent values
- Use streams for collection transformations (but keep readable)
- Prefer immutability where practical
- Use Lombok judiciously — `@Data`, `@Builder`, `@Slf4j` are fine

---

_Last updated: 2026-02-03_
