---
name: generate-bdd-tests
description: Transform acceptance criteria into executable BDD test scaffolding for Go (spec + testify) or Java (Spock)
triggers:
  - "generate bdd"
  - "generate tests"
  - "create test scaffolding"
  - "bdd tests"
---

# Generate BDD Tests

Transform acceptance criteria into executable BDD test scaffolding.

## Prerequisites

Before running this skill:
1. ACs exist in `specs/SPEC-{NNN}-{slug}/acs/*.md`
2. Run `/derive-acs` first if ACs don't exist

## Process

### Step 1: Detect Target Language

Check `agent-os/standards/tech-stack.md` or ask:

```
Which language should I generate tests for?

1. **Go** — spec + testify (new services)
2. **Java** — Spock framework (existing services)
```

### Step 2: Load ACs and Standards

Read:
```
specs/SPEC-{NNN}-{slug}/acs/*.md     # Acceptance criteria
standards/bdd.md                      # BDD conventions for target language
```

### Step 3: Map ACs to Test Structure

**For Go (spec + testify)**:

| AC Element | Go BDD |
|------------|--------|
| AC file | `{capability}_test.go` |
| AC group | `spec.Run(t, "Capability", ...)` |
| Given | `it.Before(func() { /* setup */ })` |
| When | `when("context", func() { ... })` |
| Then | `it("should outcome", func() { assert... })` |

**For Java (Spock)**:

| AC Element | Spock |
|------------|-------|
| AC file | `{Capability}Spec.groovy` |
| AC | `def "should {behavior}"() { ... }` |
| Given | `given: "context"` |
| When | `when: "action"` |
| Then | `then: "outcome"` + assertions |
| Multiple scenarios | `where:` data table |

### Step 4: Generate Test Files

#### Go Template

```go
package {package}

import (
    "testing"

    "github.com/sclevine/spec"
    "github.com/stretchr/testify/assert"
)

func Test{Capability}(t *testing.T) {
    spec.Run(t, "{Capability}", func(t *testing.T, when spec.G, it spec.S) {
        // Shared setup
        var subject *{SubjectType}

        it.Before(func() {
            subject = New{SubjectType}()
        })

        // AC-001: {Title}
        when("{given context}", func() {
            it.Before(func() {
                // Additional setup from "And" clauses
            })

            it("should {expected outcome}", func() {
                // Act
                result := subject.{Method}()

                // Assert
                assert.Equal(t, expected, result)
            })
        })

        // AC-002: {Title}
        when("{given context}", func() {
            it("should {expected outcome}", func() {
                // Test implementation
            })
        })
    })
}
```

#### Spock Template

```groovy
package {package}

import spock.lang.Specification

class {Capability}Spec extends Specification {

    def subject = new {SubjectType}()

    // AC-001: {Title}
    def "should {expected behavior}"() {
        given: "{context}"
        def input = {setup}

        and: "{additional context}"
        {additional setup}

        when: "{action}"
        def result = subject.{method}(input)

        then: "{outcome}"
        result.{field} == {expected}
    }

    // Parameterized tests for multiple scenarios
    def "should {behavior} for various inputs"() {
        given: "{context with #variable}"
        def input = new Input({variable})

        when: "{action}"
        def result = subject.{method}(input)

        then: "{outcome is #expected}"
        result == expected

        where:
        variable | expected
        value1   | result1
        value2   | result2
    }
}
```

### Step 5: Determine Output Location

Ask user or infer from project structure:

**Go**:
```
services/{service}/internal/{package}/{capability}_test.go
```

**Java**:
```
services/{service}/src/test/groovy/{package}/{Capability}Spec.groovy
```

### Step 6: Generate and Present

Generate test file content and present to user:

```
## Generated BDD Tests

**Language:** Go (spec + testify)
**Source:** specs/SPEC-001/acs/STORY-001-batch-loading.md (5 ACs)
**Output:** services/auth-service/internal/auth/token_validation_test.go

### Test Structure

- 5 test cases generated from ACs
- AC-001: Load factors for single product
- AC-002: Load factors for batch of products
- AC-003: Empty product list returns empty map
- AC-004: Batch respects configured size limit
- AC-005: Handle null product ID in batch

Ready to save? (Save / Adjust / Preview full file)
```

### Step 7: Save and Summarize

After user approval:
1. Write test file to appropriate location
2. Note any TODOs for implementation

```
## Tests Generated

| AC File | Test File | Tests |
|---------|-----------|-------|
| STORY-001-batch-loading.md | batch_loading_test.go | 5 |
| STORY-002-cache-invalidation.md | cache_invalidation_test.go | 6 |

**Total:** 11 BDD tests ready for implementation

### Next Steps
1. Implement subject under test (if not exists)
2. Fill in test assertions with actual expected values
3. Run tests — they should fail (TDD red phase)
4. Implement code to make tests pass (TDD green phase)
```

## Go-Specific Guidance

**Role**: Expert Go (Golang) Test Engineer
**Task**: Convert acceptance criteria into BDD-style test scaffolding
**Stack**: Go standard library `testing`, `github.com/sclevine/spec`, `github.com/stretchr/testify`

**Structural Rules**:
1. **No Cucumber/Gherkin** — Use `spec.Run` and nested `when`/`it` blocks
2. **Contextual isolation** — Use `it.Before` for setup to ensure test isolation
3. **Assertions** — Use `testify/assert` (aliased to `assert`) for all checks
4. **Naming** — Use `Test[Subject]` pattern for entry function

## Spock-Specific Guidance

**Role**: Expert Java/Groovy Test Engineer
**Task**: Convert acceptance criteria into Spock BDD specifications
**Stack**: Spock Framework (`spock-core`)

**Structural Rules**:
1. **Extend Specification** — All specs extend `spock.lang.Specification`
2. **Block labels** — Use `given:`, `and:`, `when:`, `then:`, `where:`
3. **Plain English** — Method names in quotes describe behavior
4. **Data-driven** — Use `where:` block for parameterized scenarios

## Tips

- **Generate stubs, not complete tests** — Values may need adjustment
- **Mark TODOs** — Flag places where implementation details are needed
- **Group related ACs** — Keep related scenarios in the same `when` block (Go) or class (Spock)
- **Include comments** — Reference AC IDs in comments for traceability
