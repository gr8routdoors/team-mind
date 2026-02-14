# Code Quality Reviewer Prompt Template

Use this template when dispatching a code-quality reviewer to verify an implementation is well-built.

**IMPORTANT:** Only dispatch after spec-compliance review passes. This review assumes the code is correct; it checks if the code is well-engineered.

---

## Template

```
## Task

Review code quality for STORY-{NNN}: {story name}

Your job: Verify the implementation is well-built (clean, tested, maintainable, follows project standards).

**Prerequisite:** This implementation has already passed spec-compliance review. You don't need to verify the code does what was asked. It does. You're reviewing how well it's done.

---

## What Was Implemented

The implementer built:

{Summary from implementer's report, 2-3 sentences}

Files changed:
{List of files and line counts}

Spec-compliance review already confirmed: ✓ All ACs implemented, no extra work, no misinterpretations.

---

## Standards to Check Against

When reviewing, reference these standards from agent-os/standards/:

{List applicable standards}

Example standards to check:
- @agent-os/standards/code-style/go.md — Naming, formatting, idioms
- @agent-os/standards/testing.md — Test quality, coverage, TDD
- @agent-os/standards/git.md — Commit hygiene, messages
- @agent-os/standards/bdd.md — Acceptance test structure
- @agent-os/standards/observability.md — Logging, monitoring (if applicable)

Key sections from standards:
{Summarize 1-2 most relevant rules per standard}

---

## Your Review Process

### Step 1: Read the Code

Read all changed files carefully. Understand:
- What does this code do?
- How does it do it?
- What are the moving parts?

### Step 2: Check Against Review Criteria

Evaluate each criterion below. Rate each as:
- ✅ **Approved** — Good or excellent. Meets standard.
- ⚠ **Issues** — Notable problems. Should fix.
- ❌ **Blocked** — Critical failures. Must fix.

---

## Review Criteria

### 1. Code Cleanliness and Readability

Does code clearly express intent? Is it easy to understand?

Check:
- **Naming** — Are names clear and accurate? (functions, variables, classes)
  - Good: `validateEmailFormat()`, `maxRetries`, `UserRepository`
  - Bad: `check()`, `x`, `Mgr`
- **Formatting** — Does code follow style standard? (indentation, line length, spacing)
- **No magic numbers** — Hard-coded numbers should be named constants
  - Bad: `if (retries > 3)`
  - Good: `const MAX_RETRIES = 3; if (retries > MAX_RETRIES)`
- **Comments** — Complex logic has clear comments. Obvious code doesn't need comments.
- **Complexity** — Functions should do one thing. If a function is >50 lines, consider splitting.

**Report:**
```
✅ Code Cleanliness: Names are clear (validateEmailFormat, maxRetries). Formatting matches style guide. No magic numbers. Functions are focused (largest is 38 lines). A few comments would help complex regex logic (line 45-52).

OR

⚠ Code Cleanliness Issues:
- Line 12: Function `process()` is too vague. Rename to `validateAndStoreUser()` for clarity.
- Line 34-67: This function does validation AND storage. Split into two functions.
- Line 45: Magic number `100`. Should be `const MAX_EMAIL_LENGTH = 100`.
```

### 2. Test Coverage and Quality

Are there tests? Do they verify behavior? Are they well-written?

Check:
- **Coverage** — Is code covered by tests? (aim for 80%+ for business logic)
- **Behavior verification** — Do tests check actual behavior, or just mocks?
  - Good: `assert(validator.validate("test@example.com") == true)`
  - Bad: `assert(mockValidator.validate() was called once)` (only verifies mock, not behavior)
- **Test names** — Do test names describe what they test?
  - Good: `test_validates_correct_email_format`
  - Bad: `test_email`
- **Edge cases** — Are edge cases tested?
  - Good: Test blank email, special chars, international chars, max length, etc.
  - Bad: Only test happy path
- **Test isolation** — Does each test test one thing? Can you run tests in any order?

**Report:**
```
✅ Test Coverage: 85% coverage. Tests verify actual behavior (asserts check return values, not mocks). Test names are clear (test_validates_correct_email, test_rejects_invalid_domain). Edge cases covered: blank, special chars, international, max length. Tests run in isolation.

OR

⚠ Test Quality Issues:
- Coverage: Only 62%. Add tests for error paths (lines 34-45, 67-78 untested).
- Line 15 (test_email): Name is too vague. Rename to test_validates_correct_email_format.
- Lines 20-30: This test only checks mocks were called. Should assert actual behavior: assert(validator.validate(...) == expectedResult).
- Missing: No test for international characters. AC requires support; add test.
```

### 3. Error Handling

Does code gracefully handle errors and edge cases?

Check:
- **Exceptions/errors** — Are errors returned or handled? (don't silently fail)
  - Good: `if (invalid) return error("Email invalid")`
  - Bad: `if (invalid) { }` (swallows error silently)
- **Logging** — Are errors logged for debugging?
- **User-facing** — If user-facing, are error messages clear?
- **Recovery** — Can the system recover from errors, or does it crash?

**Report:**
```
✅ Error Handling: Errors are returned and logged. Invalid inputs are handled gracefully. Error messages are clear.

OR

⚠ Error Handling Issues:
- Line 45: Validation error is swallowed silently. Should return error or log.
- Line 67: If API call fails, code crashes. Add try/catch or error return.
- Error messages are cryptic ("ERR_001"). Make them user-friendly.
```

### 4. Naming Clarity

Are names accurate and consistent?

Check:
- **Function names** — Describe what function does (verb + noun)
  - Good: `validateEmail`, `storeUser`, `getActiveUsers`
  - Bad: `process`, `handle`, `doThing`
- **Variable names** — Descriptive, not abbreviated
  - Good: `maxRetries`, `isValid`, `emailAddress`
  - Bad: `mr`, `v`, `e`
- **Class/type names** — Nouns, describe what they represent
  - Good: `EmailValidator`, `User`, `ValidationResult`
  - Bad: `Handler`, `Manager`, `Processor`
- **Consistency** — Same concept has same name everywhere
  - Good: Always use `emailAddress` (not sometimes `email`, sometimes `addr`)
  - Bad: Inconsistent naming confuses readers

**Report:**
```
✅ Naming: Clear and consistent. Functions describe behavior (validateEmail, storeResult). Variables are descriptive (maxRetries, isValid). Types are nouns (EmailValidator, ValidationResult). Consistent naming throughout.

OR

⚠ Naming Issues:
- Function `process()` is too vague. Should be `validateAndStoreEmail()`.
- Variable `e` (line 34) should be `emailAddress` for clarity.
- Inconsistent: Sometimes `email`, sometimes `emailAddr`, sometimes `e`. Pick one and use consistently.
```

### 5. SOLID Principles

Does code follow basic design principles? (Single Responsibility, Open/Closed, etc.)

Check:
- **Single Responsibility** — Each class/function does one thing
  - Good: `EmailValidator` only validates; `UserRepository` only stores
  - Bad: `UserManager` does validation, storage, logging, caching (too much)
- **Open/Closed** — Open for extension, closed for modification
  - Good: You can add new validators without changing existing code
  - Bad: Adding new validation requires changing the validator class
- **Dependency Injection** — Dependencies are passed in, not hard-coded
  - Good: `EmailValidator(blacklist)` — blacklist is injected
  - Bad: `EmailValidator` creates its own blacklist (hard-coded dependency)

**Report:**
```
✅ SOLID: Each class has one responsibility (EmailValidator validates, Repository stores). Code is open for extension (easy to add new validation rules). Dependencies are injected.

OR

⚠ SOLID Issues:
- EmailValidator does validation AND logging AND caching. Too many responsibilities. Split into separate classes.
- Hard-coded dependency: Repository creates its own database connection. Should inject connection.
```

### 6. Performance Concerns

Is code efficient? Any obvious performance problems?

Check:
- **Algorithms** — Are algorithms appropriate for the data? (no N^2 loops over large data)
- **Network calls** — Are unnecessary API/database calls avoided?
- **Caching** — Is data cached if it's expensive to fetch?
- **Resource leaks** — Are files, connections, memory properly cleaned up?

**Report:**
```
✅ Performance: Efficient algorithms. No unnecessary network calls. Resources properly cleaned up.

OR

⚠ Performance Issues:
- Line 45: Loop calls API inside loop. Should fetch once, then loop. (N API calls instead of 1)
- Line 78: Validation regex is complex. May be slow on large inputs. Consider optimization.
```

---

## Severity Levels

When you find issues, categorize them:

- **Critical** — Code doesn't work, violates major standards, has security issues, or crashes
  - Examples: Unhandled exception, security vulnerability, infinite loop
  - **Action:** Implementer MUST fix before approval

- **Important** — Code works but violates standards or best practices significantly
  - Examples: Missing test coverage, poor naming, too much complexity
  - **Action:** Implementer should fix; approve if implementer explains and you agree trade-off is acceptable

- **Minor** — Code works and mostly follows standards, but has small improvements possible
  - Examples: Comment could be clearer, could rename one variable, could simplify one line
  - **Action:** Implementer may fix or skip; doesn't block approval

---

## Report Format

### Option A: ✅ Approved

If code quality is good (no critical issues, maybe a few minor suggestions):

```
✅ Approved

Summary: Implementation is well-engineered. Clean code, good tests, follows standards.

Strengths:
- Clear function and variable names throughout
- 87% test coverage with good edge case tests
- Proper error handling and logging
- Follows Go style guide consistently
- Single responsibility per function/type

Minor suggestions (not blocking):
- Line 45: Comment could explain why regex is structured this way
- Line 78: Variable `m` could be renamed `matcher` for clarity
- Tests could include one performance test for large inputs

Ready to merge / mark as passing.
```

### Option B: ⚠ Needs Fixes (Important)

If code has important issues that should be fixed, but not critical:

```
⚠ Needs Fixes

Summary: Implementation works but has some quality issues that should be addressed.

Issues to Fix:

1. **Test Coverage Too Low (Important)**
   - Current: 64% coverage
   - Issue: Error handling paths not tested (lines 34-45, 67-78)
   - Fix: Add tests for error cases (invalid input, API failure, etc.)
   - Severity: Important (error paths should be tested)

2. **Function Too Complex (Important)**
   - Location: validateAndStore() function, lines 20-67 (48 lines)
   - Issue: Does validation AND storage. Should be two functions.
   - Fix: Split into validateEmail() and storeResult()
   - Severity: Important (single responsibility principle)

3. **Magic Numbers (Important)**
   - Line 34: `if (retries > 3)` should be named constant
   - Line 45: `100` should be `const MAX_EMAIL_LENGTH`
   - Fix: Define constants at top of file
   - Severity: Important (maintainability)

Strengths:
- Good error handling
- Clear variable names
- No performance issues

Next Steps: Fix these issues, re-run tests, report back for final check.
```

### Option C: ❌ Blocked

If code has critical issues that prevent approval:

```
❌ Blocked

Summary: Implementation has critical issues that must be fixed before approval.

Critical Issues:

1. **Unhandled Exception (Critical)**
   - Location: Line 67, API call not wrapped in try/catch
   - Issue: If API fails, code crashes. No error handling.
   - Fix: Wrap API call in error handling; return error or retry
   - Evidence: No error handling visible in code

2. **Silent Error (Critical)**
   - Location: Line 45, validation error swallowed
   - Issue: Invalid input doesn't return error; silently succeeds
   - Fix: Return error when validation fails
   - Evidence: If statement with empty body

3. **Test Coverage Missing (Critical)**
   - Coverage: 45% (below acceptable minimum of 80%)
   - Issue: Half the code untested. Can't verify correctness.
   - Fix: Add tests for all untested paths
   - Severity: Critical (no evidence code works)

Strengths:
- Good naming
- Follows style guide

Next Steps: Fix critical issues. Re-test. Report back.
```

```

---

## What NOT to Check

Code-quality review assumes spec compliance is already verified. Do NOT re-verify:
- Whether code implements all ACs (that's spec review's job)
- Whether tests match the AC behavior (spec review already checked this)

Focus on HOW, not on WHETHER.

---

## Tips

- **Use standards as reference** — Quote specific standards when flagging issues
- **Be specific** — Point to line numbers and give examples
- **Distinguish severity** — Critical vs. important vs. minor matters
- **Acknowledge good work** — Point out strengths too, not just issues
- **Be actionable** — Tell implementer what to fix, not just "this is bad"
- **Trust the spec review** — Don't re-check ACs; assume code is correct
- **Focus on patterns** — If the same issue appears in multiple places, note the pattern

---

## Integration Notes

After this review:
- If ✅ Approved: Mark story as passing in stories.yml. Story is complete.
- If ⚠ Needs Fixes: Implementer fixes. You review again (same reviewer preferred).
- If ❌ Blocked: Implementer fixes critical issues. You review again.

Once approved (✅), story is complete and ready to move to next story.

```

---

## Notes on Using This Template

**When to use:** Only after spec-compliance review passes. Never before.

**How to customize:**
- Replace {NNN}, {story name} with actual story details
- Include implementer's report summary
- List actual files changed
- Include actual applicable standards from agent-os/standards/
- Keep the 6 review criteria (code cleanliness, tests, error handling, naming, SOLID, performance)
- Keep severity levels (critical/important/minor)

**What makes a good quality review:**
- Actually reads the code line by line
- Evaluates against standards (not just gut feel)
- Flags specific issues with line numbers and examples
- Clearly states severity (critical/important/minor)
- Provides actionable feedback (how to fix, not just what's wrong)
- Clear verdict: ✅ / ⚠ / ❌ (not wishy-washy)

**Reviewer mindset:** You are the gatekeeper for code quality. If you approve it, the code is well-engineered and maintainable. If you ask for fixes, implementer knows exactly what to improve. No ambiguity.

