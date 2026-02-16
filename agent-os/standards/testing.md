# Testing Standards

> Requirements and patterns for testing code.

---

## Philosophy

- Tests are documentation — they describe expected behavior
- Tests enable refactoring — they give confidence to change code
- Tests catch regressions — they prevent reintroducing bugs
- **Test behavior, not implementation** — tests shouldn't break when refactoring internals

---

## Test Pyramid

| Layer | Purpose | Speed | Coverage Target |
|-------|---------|-------|-----------------|
| **Unit** | Test individual functions/methods in isolation | Fast | High |
| **Integration** | Test component interactions, database access | Medium | Medium |
| **E2E** | Test full system flows | Slow | Critical paths |

Prefer more unit tests, fewer integration tests, minimal E2E tests.

---

## Naming Conventions

### Java
- Test class: `{ClassName}Test`
- Test method: `test{Method}_{Scenario}_{ExpectedResult}` or descriptive name
- Example: `testSomeAction_DoesSomeThing_WithSomeSetup`

### Go
- Test file: `{filename}_test.go`
- Test function: `Test{Function}` or `Test{Function}_{Scenario}`
- Example: `testSomeAction_DoesSomeThing_WithSomeSetup`

---

## Test Structure

Use the **Arrange-Act-Assert** pattern:

```java
@Test
void testSomeAction_DoesSomeThing_WithSomeSetup() {
    // Arrange
    var value = new SomeAction();
    var entity = createEntity(100.00);
    var anotherValue = AnotherEntity.value(10);

    // Act
    var result = value.action(entity, anotherValue);

    // Assert
    assertThat(result.amount()).isEqualTo(new BigDecimal("90.00"));
}
```

---

## Assertions

### Do
- Use specific assertions: `assertEquals`, `assertThat(...).isEqualTo(...)`
- Assert on actual data values, not just that something isn't null
- Use `assertNotNull` before accessing properties
- Test edge cases and boundary conditions

### Don't
- **Never weaken assertions to make tests pass** — fix the code instead
- Don't use `if (x != null) assert...` — this hides failures
- Don't assert only on collection size without checking contents
- Don't ignore test failures — investigate and fix

---

## Test Data

- Use builders or factory methods for test data
- Make test data clearly artificial: `"test-product-123"`, `"user@test.com"`
- Avoid hardcoding magic numbers — use named constants
- Each test should set up its own data (isolation)

---

## Mocking

- Mock external dependencies (databases, APIs, services)
- Don't mock the class under test
- Prefer fakes over mocks when behavior matters
- Verify interactions only when the interaction itself is the behavior being tested

---

## Coverage Expectations

| Type | Minimum | Target |
|------|---------|--------|
| Unit tests | 70% | 85% |
| Critical paths | 100% | 100% |
| New code | 80% | 90% |

Coverage is a guide, not a goal. 100% coverage with weak assertions is worse than 70% with strong assertions.

---

## Java-Specific

- Use JUnit 5 (`@Test`, `@BeforeEach`, `@DisplayName`)
- Use AssertJ for fluent assertions
- Use `@SpringBootTest` sparingly — prefer unit tests
- Use H2 for data layer integration tests
- Test resources in `src/test/resources/`

---

## Go-Specific

- Table-driven tests for multiple scenarios
- Use `t.Helper()` in helper functions
- Use `t.Run()` for subtests
- Use `testify/assert` or standard library assertions
- Test files live alongside source files

```go
func TestProcessOrder(t *testing.T) {
    tests := []struct {
        name   string
        order  Order
        user   User
        want   Status
    }{
        {"valid order", order(3), activeUser(), statusConfirmed()},
        {"empty order", order(0), activeUser(), statusRejected()},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := ProcessOrder(tt.order, tt.user)
            assert.Equal(t, tt.want, got)
        })
    }
}
```

---

## Project-Specific

Test commands are project-owned. See `standards/project/testing.md`.

---

_Last updated: 2026-02-15_
