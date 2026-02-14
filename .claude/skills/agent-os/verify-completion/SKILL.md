---
name: verify-completion
description: Use when about to claim work is complete or passing
triggers:
  - "verify completion"
  - "before completion"
  - "verify work"
  - "check if done"
---

# Verify Completion

**The Iron Law: NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE**

This skill enforces a critical discipline: agents must never claim work is done, fixed, passing, or complete without running a verification command and reading the actual output. Avoid rationalizations like "should work", "probably fixed", or "looks good to me".

## The Agent Will Rationalize

Agents are prone to saying:
- "Should work now" (without testing)
- "I'm confident this fixes it" (without evidence)
- "Just this once, I'm sure" (classic corner-cutting)
- "The code looks right" (visual inspection is not verification)
- "I believe tests will pass" (belief is not evidence)

This skill prevents those failures by enforcing: **run command → read output → verify → then claim**.

---

## The Gate Function

Before any completion claim, follow this exact sequence:

1. **IDENTIFY** — What command proves the claim? (test command, build command, manual verification, etc.)
2. **RUN** — Execute the full command, capture all output
3. **READ** — Read the complete output and check exit code
4. **VERIFY** — Does the output confirm the claim?
5. **CLAIM** — Only after verification, state the result with evidence

### Example: "Tests Pass"

| Action | Evidence | Bad Approach | Correct Approach |
|--------|----------|--------------|------------------|
| Claim: Tests pass | Test output | "Should pass now" | Run `npm test`, read output, cite passing count |
| Claim: Build succeeds | Exit code 0 | "Looks compiled" | Run `npm run build`, verify exit code 0 |
| Claim: Bug fixed | Original symptom test | "Code looks right" | Reproduce original symptom, verify it's gone |
| Claim: Feature working | Feature test output | "I think it works" | Run acceptance test, read result |

---

## Common Failures

These are claims without the corresponding verification evidence:

| Claim | Requires | What Agents Skip |
|-------|----------|-----------------|
| "Tests pass" | Full test output with pass count | Running tests at all |
| "Build succeeds" | Exit code 0 and build artifact | Skipping build step |
| "Bug is fixed" | Reproducing original symptom, verifying gone | Only reading code |
| "Feature works" | Acceptance test passing | Manual testing only, no automation |
| "No regressions" | Full test suite output, no failures | Spot-checking files |
| "Code compiles" | Exit code 0 from compiler | Only syntax review |
| "All changes committed" | `git status` clean, `git log` shows commit | Not checking git status |

---

## Red Flags — Stop and Verify

When you see these phrases, **stop immediately** and run verification:

- "should work"
- "probably"
- "seems to"
- "looks good"
- "I believe"
- "confidence that"
- "about to commit"
- "ready to mark as done"
- "just looks right"

---

## Rationalization Prevention Table

Agents will try these rationalizations. Counter them:

| Rationalization | What To Do |
|-----------------|-----------|
| "Should work now" | Run the test. Read output. |
| "I'm confident" | That feeling is not evidence. Run the test. |
| "Just this once" | Never. Run the test every time. |
| "The code looks right" | Visual inspection is not verification. Run the test. |
| "I already tested it mentally" | Mental testing doesn't count. Run the test. |
| "It passed last time" | Run it again. State new evidence. |
| "I don't have time to verify" | Always make time. Verification is not optional. |

---

## Process

### Step 1: Recognize the Completion Claim

Listen for phrases like:
- "done"
- "fixed"
- "passing"
- "complete"
- "ready"
- "verified"
- "it works"

When you hear these, **stop and enter verification mode**.

### Step 2: Identify Verification Command

Ask: What command proves this claim?

Use AskUserQuestion if unclear:

```
You mentioned [work] is done. To verify, I need to run a command.

What command proves this is complete?
1. Run tests (npm test, pytest, etc.)
2. Build the project (npm run build, cargo build, etc.)
3. Manual reproduction (specific steps to verify)
4. Other verification step
```

### Step 3: Run Full Command

Execute the verification command completely. Capture all output including:
- Exit code
- Log messages
- Test results
- Build artifacts
- Error messages

### Step 4: Read Output Completely

Don't skim. Read the entire output. Look for:
- Exit code (0 = success, non-zero = failure)
- Pass/fail counts
- Error messages
- Warnings that might indicate incomplete work

### Step 5: Check Against Claim

Compare output to the completion claim:

- Does the output confirm "tests pass"? (look for "X tests passed")
- Does the exit code show success? (0 = yes)
- Are there any failures or errors? (indicate incomplete work)

### Step 6: Cite Evidence When Claiming

When claiming completion, cite specific evidence:

```
Tests pass: All 47 tests passed (exit code 0).

Commit ready: git status shows no uncommitted changes. Commit hash abc1234.

Bug fixed: Ran reproduction steps from STORY-001. Original error no longer appears.
```

NOT:
```
Tests pass.
Commit ready.
Bug fixed.
```

### Step 7: Update Story Status

When verification confirms completion, update `agent-os/specs/STORY-{NNN}/stories.yml`:

```yaml
STORY-{NNN}:
  status: passing
  verified_by: [command that verified]
  evidence: "[specific output or result]"
  verified_at: 2026-02-14T12:34:56Z
```

---

## Integration with Lit SDLC

### Before Updating stories.yml

Always run `/verify-completion` before marking a story `passing` in `stories.yml`.

### Before /end-session

Run verification on all completed work before calling `/end-session`. Reference verification evidence in session summary.

### Before Git Commit

Never commit work without verification. The commit message should cite the verification evidence:

```
git commit -m "STORY-002: Fix payment validation

Tests pass: All 23 tests passing (test-payment.ts)
Manual verification: Tested payment flow with valid/invalid cards
Exit code: 0

Fixes: #450"
```

---

## Tips

- **Verify early** — Don't wait until the end to discover failures
- **Automate verification** — Use scripts, test runners, build tools — not manual inspection
- **Keep logs** — Save verification output in session notes for reference
- **Don't shortcut** — Verification is mandatory, not optional
- **When in doubt, verify again** — If uncertain, run the command again and read the output
