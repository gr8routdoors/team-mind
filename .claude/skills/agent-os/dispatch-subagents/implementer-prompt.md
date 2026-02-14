# Implementer Subagent Prompt Template

Use this template when dispatching an implementer subagent to build a story.

---

## Template

```
## Task

Implement STORY-{NNN}: {story name}

---

## Story Description

{Full story text from stories.yml, including motivation and scope}

### Acceptance Criteria

{Complete AC text from acs/STORY-{NNN}-{slug}.md}

Each AC is a behavioral requirement. Your implementation must satisfy all of them, nothing more, nothing less.

---

## Spec Context

### Scope and Architecture

{2-3 bullet points from README.md or design.md explaining what this spec is building and why}

Example:
- This spec adds payment validation to the checkout flow
- Validation must work offline without calling third-party services
- All validation rules are documented in design.md under "Validation Rules"

### Related Stories

If other stories exist in this spec, list them:
- STORY-001: ...
- STORY-002: ...
- STORY-003: ... (you are here)
- STORY-004: ...

Your story is independent. You don't need to implement the others. But you should know they exist.

---

## Standards to Follow

Reference these standards in your work:

{Relevant standards from agent-os/standards/, listed as references}

Example:
- @agent-os/standards/code-style/go.md — Go naming, formatting, idioms
- @agent-os/standards/testing.md — Test coverage and TDD practices
- @agent-os/standards/bdd.md — How to write acceptance tests
- @agent-os/standards/git.md — Commit message format

Key points from these standards:
- {Summarize 1-2 most important rules for this story}
- {Summarize 1-2 more important rules}

---

## Before You Begin

**Have questions about the requirements?** Ask now.

Do you understand:
- What behavior each AC requires?
- How it fits into the larger spec?
- Which standards apply?
- Any edge cases or ambiguities?

If anything is unclear, ask. Don't guess. Good questions prevent bad code.

---

## Your Job

1. **Implement exactly what the ACs specify.** Not more, not less. (This is called YAGNI: You Aren't Gonna Need It.)
2. **Write tests first** (TDD). Write a failing test for each AC, then implement code to pass it.
3. **Verify against each AC.** After implementing, go through each AC and confirm: "Does my code satisfy this?"
4. **Commit your work.** Use the format from git.md standard. Message should reference the story.
5. **Self-review.** Before reporting back, check your work against the self-review checklist below.
6. **Report back.** Tell me what you implemented, test results, files changed, and any concerns.

---

## Implementation Pattern (TDD)

For each AC:

1. **Write a failing test** that verifies the AC behavior
   ```
   Example AC: "When user provides invalid email, validation fails"
   Write test: test_validation_fails_with_invalid_email()
   Run test: it fails (expected, code doesn't exist yet)
   ```

2. **Implement minimal code** to pass that test
   ```
   Add email validation logic
   ```

3. **Run test again.** It should pass.

4. **Repeat for next AC.** Each AC gets its own test.

After all ACs have tests and code:

5. **Run full test suite** to verify no breaks
6. **Verify each AC manually** — read the code and confirm it does what the AC says

---

## Self-Review Checklist

Before reporting back, verify:

- [ ] **All ACs implemented** — I have code that satisfies every AC, line by line
- [ ] **Tests cover all ACs** — Each AC has a test that verifies its behavior
- [ ] **No extra work** — I didn't add features not in the ACs (YAGNI). Delete any extra code.
- [ ] **Tests verify behavior** — Tests check real behavior (assertions), not just mock verification. No fake tests.
- [ ] **Clear names** — Function names, variable names, class names clearly express purpose
- [ ] **No warnings** — Compiler/linter runs clean. Fix or suppress with good reason.
- [ ] **Error handling** — What happens when AC conditions aren't met? Handled gracefully.
- [ ] **Follows standards** — Code matches code-style standard. Commits match git standard. Tests match testing standard.
- [ ] **Committed** — Changes are committed with clear message (not staged or dirty)
- [ ] **No broken tests** — Full test suite passes, including my new tests

---

## What to Report Back

After you've completed self-review, tell me:

1. **What you implemented** — 2-3 sentences describing the feature/fix/change
2. **Test results** — "All 12 tests pass (9 new, 3 existing)"
3. **Files changed** — List changed files with line counts (e.g., "payment-validator.go: +45 lines, tests_payment.go: +89 lines")
4. **Concerns** — Any edge cases, limitations, or gotchas I should know about before review
5. **Self-review result** — "Self-review checklist complete ✓"

Example report:
```
Implemented: Email validation for checkout. Validates RFC 5322 format, rejects blocked domains, handles international characters.

Test results: All 23 tests pass (17 new tests for email validation, 6 existing tests for checkout).

Files changed:
- email-validator.go: +67 lines (validation logic)
- email-validator_test.go: +142 lines (17 new tests)
- checkout.go: +3 lines (integration)

Concerns: Validation is synchronous; if you expect high volume, we may need async validation later. Also, test assumes no network access (which is correct per AC).

Self-review: Complete ✓
```

---

## Questions

If you hit blockers or have questions:

1. **Ask me first** — Don't guess or make assumptions
2. **Be specific** — "Is X ambiguous?" not "What should I do?"
3. **Reference the AC** — "AC says X, but it's unclear if Y applies. Which is it?"

I'll clarify and keep you unblocked.

```

---

## Notes on Using This Template

**When to use:** Whenever you dispatch a subagent to implement a story.

**How to customize:**
- Replace {NNN}, {story name}, {slug} with actual story details
- Fill in the spec context section with actual README/design excerpts
- List actual standards that apply to the story's tech stack
- Keep the structure and emphasis on TDD, self-review, and clear reporting

**What makes a good dispatch:**
- Clear story description (implementer should understand *why* not just *what*)
- Complete AC text (no ambiguity about requirements)
- Relevant standards cited (implementer knows what "good code" means in this project)
- Self-review checklist (implementer catches their own obvious mistakes)
- Permission to ask questions (implementer doesn't waste time guessing)

**Subagent mindset:** The implementer should feel empowered to ask questions, implement with clarity on what "done" means, and report results without guessing whether they succeeded.

