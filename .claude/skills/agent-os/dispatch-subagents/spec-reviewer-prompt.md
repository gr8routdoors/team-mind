# Spec Compliance Reviewer Prompt Template

Use this template when dispatching a spec-compliance reviewer to verify an implementation matches its specification.

---

## Template

```
## Task

Review spec compliance for STORY-{NNN}: {story name}

Your job: Verify the implementation matches the specification (nothing more, nothing less).

---

## What Was Requested

These are the acceptance criteria. The implementation MUST satisfy all of them.

### Acceptance Criteria (from acs/STORY-{NNN}-{slug}.md)

{Full AC text}

Read these carefully. Each AC is a specific behavioral requirement.

---

## What Implementer Claims

The implementer reports:

{Implementer's self-report from previous step}

**CRITICAL: Do NOT trust this report.**

---

## Your Review Process

### Step 1: Read the Actual Code

Don't rely on the implementer's report. Read the files they changed:

{List of files changed, e.g.:
- /path/to/email-validator.go
- /path/to/email-validator_test.go
- /path/to/checkout.go
}

Read each file carefully. Understand what the code does.

### Step 2: Line-by-Line AC Verification

For EACH acceptance criterion:

1. **Read the AC carefully.** What behavior does it require?
2. **Find the code that implements it.** Where in the files is this behavior?
3. **Verify the code is correct.** Does it actually do what the AC says? Are there edge cases it misses?
4. **Check the test.** Is there a test that verifies this AC? Does the test verify behavior (not just mocks)?

Example verification process:

```
AC: "When user provides invalid email, validation rejects it"

Search for: Email validation logic
Found in: email-validator.go, lines 42-67

Check implementation:
- Does it check email format? (Yes, line 45: RFC 5322 validation)
- Does it reject invalid format? (Yes, line 49: return error if invalid)
- What about edge cases? (Checked: blank email handled, special chars handled, etc.)

Check test:
- Is there a test for this? (Yes, test_validation_fails_with_invalid_email)
- Does test verify behavior? (Yes: asserts error is returned)
- Are edge cases tested? (Yes: blank, special chars, international)

RESULT: ✓ AC implemented correctly
```

### Step 3: Check for Missing Requirements

Go through ACs in order. Verify each one:

```
AC 1: [requirement] — ✓ Found in code at [file:line]
AC 2: [requirement] — ✗ NOT FOUND. Implement in [suggestion]
AC 3: [requirement] — ✓ Found in code at [file:line]
```

If an AC is not implemented, flag it.

### Step 4: Check for Extra Work (YAGNI Violations)

Look at the code. Is there anything implemented that ISN'T in the ACs?

Examples of extra work to flag:
- Additional validation rules not mentioned in ACs
- Extra API endpoints not in the story
- Caching or optimization not required
- Features beyond the scope

If implementer added extra stuff, flag it. ("This is good code, but it's outside the story scope. Consider removing or documenting as future work.")

### Step 5: Check for Misinterpretations

Sometimes implementer builds the right *thing* but the wrong *way*.

Examples of misinterpretations:
```
AC: "Validation must work offline"
Code: Calls third-party API
ISSUE: Misinterpretation — "offline" not met

AC: "User can provide custom validation rules"
Code: Only built-in rules, no interface for custom rules
ISSUE: Misinterpretation — customization missing

AC: "Response time must be under 100ms"
Code: No performance testing, just "seems fast"
ISSUE: Misinterpretation — no evidence it meets requirement
```

If you spot a misinterpretation, flag it with the specific AC and what the code does vs. what it should do.

---

## Report Format

After verification, provide your verdict:

### Option A: ✅ Spec Compliant

If all ACs are met, no extra work, no misinterpretations:

```
✅ Spec Compliant

Summary: Implementation satisfies all ACs. No extra work detected. Tests verify behavior.

Verification:
- AC 1: ✓ Verified at email-validator.go:45-49
- AC 2: ✓ Verified at email-validator.go:52-67 with test test_validation_fails
- AC 3: ✓ Verified at checkout.go:12-15 with test test_checkout_uses_validator
- AC 4: ✓ Verified at email-validator_test.go:89-105 (edge cases)

Strengths:
- Clean implementation of ACs
- Good test coverage for AC behaviors
- No extra features outside scope

Ready for code quality review.
```

### Option B: ❌ Issues Found

If any ACs are missing, extra work detected, or misinterpretations found:

```
❌ Issues Found

Summary: [Brief description of issues]

Issues:

1. **Missing: AC 2 (Reject blocked domains)**
   - AC requires: "Validation rejects emails from blocked-domain-list.txt"
   - Code does: Only validates format, doesn't check blocked list
   - Fix: Add blocked domain check in email-validator.go after line 67
   - Evidence: No code found implementing this requirement

2. **Extra work: Async validation (not in ACs)**
   - Code includes: Async validation infrastructure in email-validator.go:100-125
   - Issue: ACs don't require async; this adds complexity beyond scope
   - Recommendation: Remove async code or document as future work (separate story)

3. **Misinterpretation: "Validation must work offline"**
   - AC requirement: "Must work without internet connection"
   - Code does: Calls validate-email.io API (line 58)
   - Fix: Use local validation rules only; remove API call
   - Evidence: checkout.go:15 shows API call

4. **Missing test: AC 3 (International characters)**
   - AC requires: "Accept international email addresses (ä, ü, ö, etc.)"
   - Code: Has validation logic (email-validator.go:52-67)
   - Test: No test for international characters
   - Fix: Add test_validation_accepts_international_email() to test file

---

## Next Steps

Implementer should:
1. Fix each issue listed above
2. Re-run tests to verify fixes
3. Re-commit changes
4. Report back when ready for re-review
```

---

## What NOT to Check

Spec-compliance review focuses ONLY on "did you build what was asked?"

Do NOT check (that's for code-quality review):
- Code style and formatting
- Test quality and coverage (beyond "does test verify AC?")
- Performance or optimization
- Error messages or user experience
- Code cleanliness or design patterns
- SOLID principles or architecture

**Example:** If code implements the AC correctly but uses a bad variable name, that's OK for spec review (flag it as a note, but don't block). Code quality review will catch it.

---

## Tips

- **Compare line by line** — Actually read the code. Don't skim.
- **Test the logic** — Mentally run through scenarios. Does the code handle them?
- **Look for the negative case** — AC says "do X". Does code also NOT do wrong things?
- **Check tests** — Tests are specification in code form. Do tests verify what AC says?
- **Ask for clarification** — If you can't find an AC in code, ask the implementer (don't assume)
- **Document blockers** — If AC is genuinely impossible with current design, flag it early
- **Reusable feedback** — If you find AC ambiguity, suggest clarification for next story

```

---

## Notes on Using This Template

**When to use:** Dispatch this reviewer after implementer reports completion and self-review.

**How to customize:**
- Replace {NNN}, {story name}, {slug} with actual story details
- Copy FULL AC text (no paraphrasing)
- Include implementer's exact report
- List the actual files they changed
- Keep the structure: read code → verify each AC → report verdict

**What makes a good spec review:**
- Actually reads the code (not just the report)
- Checks each AC individually
- Flags missing requirements with specific line references
- Catches misinterpretations and extra work
- Reports actionable feedback (not vague criticism)
- Clear verdict: ✅ or ❌ (not wishy-washy)

**Reviewer mindset:** You are the gatekeeper for spec compliance. If you pass it, the code implements the spec. If you reject it, implementer knows exactly what to fix. No ambiguity.

