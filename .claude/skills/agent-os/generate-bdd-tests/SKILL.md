---
name: generate-bdd-tests
description: Use when acceptance criteria exist and need test scaffolding
triggers:
  - "generate bdd"
  - "generate tests"
  - "create test scaffolding"
  - "bdd tests"
---

# Generate BDD Tests

Transform acceptance criteria into executable BDD test scaffolding.

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to skipping test scaffolding:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "I'll write tests as I go" | Tests written after code are confirmations, not specs. They test what you built, not what you should build. | Generate test scaffolding first as executable specifications. |
| "The ACs are specific enough to code from" | ACs are narratives. Tests are machine-checkable contracts. Narratives are too ambiguous for TDD. | Transform ACs into test cases to drive implementation. |
| "Writing test scaffolding is wasted effort" | Scaffolding forces clarity. Without it, you code uncertain, then refactor endlessly. | Use test structure to clarify implementation intent. |
| "I know how to test this" | Assumption. Tests without ACs miss edge cases and integration scenarios. | Generate tests from ACs to ensure comprehensive coverage. |
| "We'll test everything at the end" | Too late. By then, bugs are baked in. Catching them at design time costs a fraction. | Use test scaffolding to catch issues during implementation. |

## HARD GATE

⛔ **DO NOT write implementation code** until BDD test scaffolding has been generated and saved.

Tests come first. Code comes second. If no test scaffolding exists, you have nothing to implement toward. Generate the scaffolding, then implement to make it pass.

## Prerequisites

Before running this skill:
1. ACs exist in `specs/SPEC-{NNN}-{slug}/acs/*.md`
2. Run `/derive-acs` first if ACs don't exist

## Process

### Step 1: Discover Testing Stack

Determine the project's language(s) and BDD framework(s):

1. Read `agent-os/standards/project/tech-stack.md` for project languages
2. Read `agent-os/standards/project/testing.md` for the project's declared BDD framework

**If the project's testing standard declares a BDD framework:** Use it. The project declaration is the authority.

**If the project's testing standard does not declare a BDD framework:** Ask the user which language and BDD framework to target. Do not assume.

### Step 2: Load ACs and Conventions

Read:
```
specs/SPEC-{NNN}-{slug}/acs/*.md       # Acceptance criteria
agent-os/standards/bdd.md              # BDD methodology and language-specific conventions
```

From `bdd.md`, always use:
- **AC format** — Given/When/Then structure
- **Coverage patterns** — Happy path, validation, edge cases, error conditions
- **Traceability** — AC-to-requirement linking

From `bdd.md`, use language-specific sections if they match the target language discovered in Step 1 (e.g., "Go BDD" section for Go projects, "Java BDD" section for Java projects). These sections contain templates, structural rules, and transformation patterns.

**If the project's `testing.md` declares a BDD framework that differs from what `bdd.md` covers:** Use the project declaration as the authority for framework choice. Use the BDD methodology from `bdd.md` (AC format, traceability, coverage patterns) combined with your knowledge of the declared framework to generate idiomatic test scaffolding.

### Step 3: Map ACs to Test Structure

Using the transformation patterns from `bdd.md` (if available for the target language) or the project's declared BDD framework, map each AC element to the corresponding test construct:

| AC Element | Maps To |
|------------|---------|
| AC file | One test file per capability |
| AC group | Test suite or describe block |
| Given | Setup / context / fixture |
| When | Action under test |
| Then | Assertion / expectation |
| And | Additional setup or assertion |
| Multiple scenarios | Parameterized / data-driven tests |

The specific syntax depends on the target framework. Use the conventions from `bdd.md` or the project's testing standard — do not invent your own patterns.

### Step 4: Generate Test Files

Generate test file content using the templates and structural rules from `bdd.md` for the target language. If `bdd.md` does not have a section for the target language, generate idiomatic BDD test scaffolding based on the project's declared framework.

Every generated test file must:
- Reference AC IDs in comments for traceability
- Include TODOs where implementation details are needed
- Follow the structural rules from the conventions (naming, setup patterns, assertion style)
- Group related ACs together within the test structure

### Step 5: Determine Output Location

Infer the output location from existing project structure (look at where existing test files live). If the project structure is unclear or no existing tests exist, ask the user.

### Step 6: Generate and Present

Generate test file content and present to user:

```
## Generated BDD Tests

**Framework:** {framework name from discovered conventions}
**Source:** specs/SPEC-{NNN}-{slug}/acs/{story}.md ({N} ACs)
**Output:** {inferred or confirmed output path}

### Test Structure

- {N} test cases generated from ACs
- AC-001: {Title}
- AC-002: {Title}
- ...

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
| {story}.md | {test_file} | {count} |

**Total:** {N} BDD tests ready for implementation

### Next Steps
1. Implement subject under test (if not exists)
2. Fill in test assertions with actual expected values
3. Run tests — they should fail (TDD red phase)
4. Implement code to make tests pass (TDD green phase)
```

## Tips

- **Generate stubs, not complete tests** — Values may need adjustment
- **Mark TODOs** — Flag places where implementation details are needed
- **Group related ACs** — Keep related scenarios together in the test structure
- **Include comments** — Reference AC IDs in comments for traceability
- **Follow project conventions** — Match the style and patterns already used in the project's test suite
