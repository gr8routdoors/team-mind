# BDD Standards

> Conventions for acceptance criteria and behavior-driven tests.

---

## Workflow

```
Requirements → Architectural Design → Acceptance Criteria → BDD Tests → Code
```

Each step informs the next. Don't skip architectural design — knowing *how* helps define *what done looks like*.

---

## Acceptance Criteria

### Format

Use Given/When/Then in markdown:

```markdown
### AC-001: Process order with valid items

**Requirement:** REQ-003

**Given** an order with 3 items totaling $300
**And** the customer has a valid account
**When** the order is submitted
**Then** the order status is "confirmed"
**And** a confirmation email is sent
```

### File Organization

ACs live in `specs/{feature}/acs/` with files named by capability:

```
specs/orders-v2/acs/
├── order-submission.md
├── order-fulfillment.md
├── validation-rules.md
└── error-handling.md
```

This enables parallel work on different capabilities.

### Coverage Patterns

Every feature needs ACs for:

| Pattern | Description | Example |
|---------|-------------|---------|
| **Happy path** | Primary success scenario | Valid order confirmed correctly |
| **Validation** | Invalid input handling | Null order ID returns error |
| **Business rules** | Rule violation handling | Inactive account rejected |
| **Edge cases** | Boundaries, empty, null | Zero quantity, max items |
| **Error conditions** | Downstream failures | Database timeout handled |

### Quality Checklist

Before finalizing ACs:

- [ ] **Testable** — Can write automated test
- [ ] **Specific** — No ambiguous terms ("fast", "appropriate", "properly")
- [ ] **Independent** — Doesn't depend on other ACs' state
- [ ] **Traceable** — Links to source requirement
- [ ] **Complete** — Covers happy, validation, edge, and error cases

---

## Go BDD (spec + testify)

**Stack**: `testing`, `github.com/sclevine/spec`, `github.com/stretchr/testify`

### Structural Rules

1. **No Cucumber/Gherkin** — Use `spec.Run` with nested `when`/`it` blocks
2. **Contextual isolation** — Use `it.Before` for setup
3. **Assertions** — Use `testify/assert` for all checks
4. **Naming** — Use `Test[Subject]` pattern for entry function

### Template

```go
func TestOrderProcessing(t *testing.T) {
    spec.Run(t, "OrderProcessing", func(t *testing.T, when spec.G, it spec.S) {
        var processor *OrderProcessor
        var order *Order

        it.Before(func() {
            processor = NewOrderProcessor()
            order = &Order{Items: 3, Total: decimal.NewFromInt(300)}
        })

        when("customer has valid account", func() {
            it.Before(func() {
                processor.SetCustomer(Customer{Status: "active"})
            })

            it("should confirm the order", func() {
                result := processor.Submit(order)
                assert.Equal(t, "confirmed", result.Status)
            })

            it("should send confirmation email", func() {
                result := processor.Submit(order)
                assert.True(t, result.EmailSent)
            })
        })

        when("order has zero items", func() {
            it.Before(func() {
                order = &Order{Items: 0, Total: decimal.Zero}
            })

            it("should return error", func() {
                _, err := processor.Submit(order)
                assert.ErrorIs(t, err, ErrEmptyOrder)
            })
        })
    })
}
```

### Transformation Pattern

| AC Format | Go BDD |
|-----------|--------|
| Given [context] | `it.Before(func() { /* setup */ })` |
| When [action] | `when("action", func() { ... })` |
| Then [outcome] | `it("should outcome", func() { ... })` |
| And [additional] | Additional setup in `it.Before` or assertion in `it` |

---

## Java BDD (Spock)

**Stack**: Spock Framework (`spock-core`)

### Structural Rules

1. **Extend Specification** — All specs extend `Specification`
2. **Block labels** — Use `given:`, `when:`, `then:`, `where:`
3. **Plain English** — Method names describe behavior in quotes
4. **Data-driven** — Use `where:` block for parameterized tests

### Template

```groovy
class OrderProcessingSpec extends Specification {

    def processor = new OrderProcessor()

    def "should confirm order for active customer"() {
        given: "an order with 3 items totaling 300"
        def order = new Order(items: 3, total: 300.00)

        and: "the customer has an active account"
        processor.setCustomer(new Customer(status: "active"))

        when: "the order is submitted"
        def result = processor.submit(order)

        then: "the order is confirmed"
        result.status == "confirmed"
        result.emailSent == true
    }

    def "should reject orders with no items"() {
        given: "an order with zero items"
        def order = new Order(items: 0, total: 0)

        when: "submission is attempted"
        processor.submit(order)

        then: "an error is thrown"
        thrown(EmptyOrderException)
    }

    def "should process orders of various sizes"() {
        given: "an order with #items items"
        def order = new Order(items: items, total: total)
        processor.setCustomer(new Customer(status: "active"))

        when: "the order is submitted"
        def result = processor.submit(order)

        then: "the order status is #expectedStatus"
        result.status == expectedStatus

        where:
        items | total  | expectedStatus
        1     | 50.00  | "confirmed"
        5     | 250.00 | "confirmed"
        10    | 500.00 | "confirmed"
    }
}
```

### Transformation Pattern

| AC Format | Spock |
|-----------|-------|
| Given [context] | `given: "context"` |
| And [additional context] | `and: "additional"` |
| When [action] | `when: "action"` |
| Then [outcome] | `then: "outcome"` + assertion |
| Multiple inputs | `where:` block with data table |

---

## Traceability

### AC → Requirement

Each AC should reference its source:

```markdown
### AC-003: Validate order item association

**Requirement:** REQ-007 (Order items must be associated with inventory)
```

### Coverage Matrix

Track coverage in spec:

```markdown
## Coverage Matrix

| Requirement | Happy | Validation | Edge | Error |
|-------------|-------|------------|------|-------|
| REQ-001     | AC-001| AC-005     | AC-008| AC-012|
| REQ-002     | AC-002| AC-006     | AC-009| —     |
| REQ-003     | AC-003, AC-004| AC-007| AC-010, AC-011| AC-013|
```

---

## Common AC Patterns

### CRUD Operations

```markdown
### AC: Create [entity]
**Given** valid [entity] data
**When** create is called
**Then** [entity] is persisted
**And** ID is returned

### AC: Create [entity] with invalid data
**Given** [entity] data with null [required field]
**When** create is called
**Then** validation error is returned
**And** [entity] is not persisted
```

### Processing

```markdown
### AC: Process [result] for [scenario]
**Given** [inputs with specific values]
**When** processing runs
**Then** [result] equals [expected value]

### AC: Process [result] at boundary
**Given** [input] at [min/max boundary]
**When** processing runs
**Then** [boundary behavior]
```

### Validation

```markdown
### AC: Reject null [field]
**Given** request with null [field]
**When** submitted
**Then** error code [CODE] is returned
**And** message indicates [field] is required
```

---

_Last updated: 2026-02-04_
