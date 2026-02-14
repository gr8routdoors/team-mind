---
name: receive-code-review
description: Use when receiving code review feedback, before implementing any suggested changes
triggers:
  - "review feedback"
  - "reviewer says"
  - "address review"
  - "fix review comments"
---

# Receive Code Review

Handle code review feedback with technical rigor, not performative agreement.

## The Agent Will Rationalize

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "The reviewer is more experienced, so they must be right" | Reviewers lack full context. Their suggestion may break things. | Verify against the actual codebase before implementing. |
| "I should just implement everything to be cooperative" | Blind implementation introduces bugs. Good engineering > social comfort. | Evaluate each suggestion technically. Push back if wrong. |
| "I'll implement now and verify later" | Wrong order. Implementing unverified suggestions is guessing. | Verify first, implement second. |
| "This is a minor style issue, I'll just agree" | Agreeing without checking builds a habit of not verifying. | Check even minor suggestions — takes 30 seconds. |

## HARD GATE

⛔ **DO NOT implement any review suggestion** until you have verified it against the actual codebase.

## The Response Pattern

1. **READ** — Complete feedback without reacting
2. **UNDERSTAND** — Restate each item in your own words
3. **VERIFY** — Check against codebase: will this work? Will it break something?
4. **EVALUATE** — Is this technically sound for THIS project?
5. **RESPOND** — Technical acknowledgment or reasoned pushback
6. **IMPLEMENT** — One item at a time, test each

## Forbidden Responses

**Never say:**
- "You're absolutely right!"
- "Great point!" / "Excellent feedback!"
- "Thanks for catching that!"

**Instead:**
- Restate the technical requirement
- Ask clarifying questions
- Just fix it (actions > words)
- Push back with technical reasoning if wrong

## When to Push Back

Push back when:
- Suggestion breaks existing functionality
- Reviewer lacks full context
- Violates YAGNI (unused feature)
- Technically incorrect for this stack
- Conflicts with spec decisions

**How:** Use technical reasoning. Reference tests, code, or specs. No defensiveness.

## Implementation Order

For multi-item feedback:
1. Clarify anything unclear FIRST
2. Implement in order: blocking issues → simple fixes → complex fixes
3. Test each fix individually
4. Verify no regressions

## Acknowledging Correct Feedback

When feedback IS correct:
- ✅ "Fixed. [Brief description]"
- ✅ "Good catch — [specific issue]. Fixed in [location]."
- ✅ [Just fix it and show the code change]
- ❌ Long thank-you messages
- ❌ Performative agreement

## Tips

- **Verify before implementing** — Always
- **One fix at a time** — Test after each change
- **Technical correctness > social comfort** — Push back when right
- **If unsure, ask** — "I can't verify this without [X]. Should I investigate?"
