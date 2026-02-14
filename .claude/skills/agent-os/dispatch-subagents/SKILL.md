---
name: dispatch-subagents
description: Use when executing implementation with independent stories in the current session
triggers:
  - "dispatch subagents"
  - "subagent driven"
  - "execute with subagents"
  - "parallel implementation"
---

# Dispatch Subagents

Execute spec stories by dispatching fresh subagent per story, with two-stage review after each implementation.

## Overview

The dispatch-subagents skill enables subagent-driven development adapted for Lit SDLC. Instead of implementing all stories yourself in a single session, you dispatch independent subagents to implement each story, then orchestrate reviews to verify both specification compliance and code quality.

**Key benefits:**
- Fresh perspective per story (avoids tunnel vision)
- Two-stage reviews (spec then quality) catch different issues
- Clean parallelization of independent stories
- Clear hand-offs and verification gates

---

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to skipping the dispatch workflow:

| Rationalization | Why It's Wrong | What To Do Instead |
|-----------------|----------------|-------------------|
| "I can implement all stories myself faster" | You'll miss things, create inconsistencies across stories, and won't catch your own mistakes. Single-implementer approach causes bottlenecks and blind spots. | Dispatch subagents. Fresh eyes catch errors you miss. |
| "Reviews are overkill for simple changes" | No change is too simple to skip review. Simple changes hide subtle bugs. Spec compliance review catches misinterpretations; quality review catches tech debt. | Never skip reviews. Both gates are mandatory. |
| "I'll skip spec review since I wrote the spec" | You wrote it and are now implementing it—you're biased. Spec review must be independent. A fresh reviewer will catch ambiguities and misinterpretations you can't see. | Always dispatch independent spec reviewer. |
| "Quality review is redundant after spec review" | No. Spec review checks "did you build what was asked?". Quality review checks "is it well-built?". Different concerns, different reviewers. | Keep quality review separate and mandatory. |
| "I can skip the implementer self-review step" | Self-review catches obvious mistakes before dispatch to reviewers. It saves reviewer time and catches careless errors. Skipping it wastes everyone's time. | Always include self-review checklist. |
| "One reviewer can do both spec and quality reviews" | No. Spec compliance requires comparing code to ACs. Code quality requires assessing engineering practices. Same person will miss issues in second review. | Dispatch two separate reviewers for two separate reviews. |
| "Dispatch is overkill for this small spec" | Spec size doesn't matter. Review discipline matters. Even 2-story specs benefit from independent review. The process is the point. | Follow the full dispatch workflow regardless of spec size. |

---

## When to Use

Use dispatch-subagents when:

- **You have a spec with multiple independent stories** — Stories don't block each other
- **Stories are defined with clear ACs** — Acceptance criteria are specific enough for independent implementation
- **You want to stay in the current session** — Subagents work in parallel within the same session
- **You want fresh perspective per story** — Each implementer brings independent viewpoint
- **Quality matters more than speed** — Two-stage review catches more issues than single pass

Do NOT use dispatch-subagents when:

- **Stories are sequential/dependent** — Use continue-spec instead; implement in order with gates between
- **You have a single story** — Dispatch adds overhead. Just implement directly with reviews.
- **Spec is still in flux** — Finish shaping first with shape-spec. Dispatch only when spec is stable.
- **ACs are vague** — Use derive-acs to sharpen requirements first. Dispatch needs clear targets.

---

## The Process

### Step 1: Load Spec Context

Identify the spec you're implementing and load its full context:

```
agent-os/specs/SPEC-{NNN}-{slug}/
  ├── README.md          # Scope, context, design decisions
  ├── design.md          # Architecture and execution plan
  ├── stories.yml        # Story definitions and status tracking
  └── acs/               # Acceptance criteria files (one per story or grouped)
```

Read:
- **README.md** — Understand scope, context, and architectural decisions
- **design.md** — Learn implementation strategy and design constraints
- **stories.yml** — Load all story definitions and current status
- **acs/** — Read acceptance criteria for each story you'll dispatch

### Step 2: Load Relevant Standards

Reference applicable standards mentally or run `/inject-standards` to load them:

```
agent-os/standards/
  ├── guardrails.md
  ├── code-style.md (or language-specific: code-style/java.md, code-style/go.md)
  ├── testing.md
  ├── bdd.md
  ├── git.md
  └── [other relevant standards]
```

Which standards apply depends on the spec's technology. For each story dispatch, you'll reference these standards in the subagent prompts.

### Step 3: Create TodoWrite with All Stories

Use TodoWrite to track all stories as tasks. Extract story list from `stories.yml`:

```
todos:
  - content: "Dispatch implementer for STORY-001: [name]"
    status: pending
    activeForm: "Dispatching implementer for STORY-001"
  - content: "Review STORY-001 for spec compliance"
    status: pending
    activeForm: "Reviewing STORY-001 spec compliance"
  - content: "Review STORY-001 code quality"
    status: pending
    activeForm: "Reviewing STORY-001 code quality"
  - content: "Dispatch implementer for STORY-002: [name]"
    status: pending
    activeForm: "Dispatching implementer for STORY-002"
  ... [repeat for each story] ...
  - content: "Final review of entire implementation"
    status: pending
    activeForm: "Running final review of implementation"
```

This gives you a clear checklist of reviews to complete for each story.

### Step 4: Per Story Loop

For each story in stories.yml (in priority/dependency order):

#### 4a. Dispatch Implementer Subagent

Create a clear hand-off to the implementer using the implementer-prompt.md template. Include:

- **Story ID and name** from stories.yml
- **Full story text** from stories.yml
- **Complete AC text** from acs/STORY-{NNN}-{slug}.md
- **Key spec context** from README.md and design.md (2-3 bullet points, not the whole document)
- **Relevant standards** injected from agent-os/standards/
- **Self-review checklist** for implementer to use before reporting back

Example dispatch:

```
Implement STORY-001: [story name]

Use the implementer-prompt.md template to structure this dispatch.

Here's the story context:
[Story text and ACs]

Here's what we're building:
[Architecture notes from design.md]

Here are the standards to follow:
[Standards excerpt or references]

Before you start, review the checklist. After implementation, self-review and report back.
```

#### 4b. Answer Implementer Questions

If the implementer asks clarifying questions:

- Answer directly and clearly
- If the question reveals ambiguity, document it and consider updating the spec README.md
- If the question is about standards or patterns, cite the standard
- Never tell them to "figure it out" — good questions prevent bad code

#### 4c. Implementer Implements, Tests, Commits

The implementer's job:

1. Write failing tests first (TDD)
2. Implement code to pass tests
3. Verify against each AC
4. Commit with clear message
5. Self-review against checklist
6. Report: what was implemented, test results, files changed, any concerns

You don't need to watch this step. Implementer works independently.

#### 4d. Dispatch Spec-Compliance Reviewer

Create a hand-off to the spec reviewer using spec-reviewer-prompt.md. Include:

- **Story ACs** (full text from acs/)
- **Implementer's report** (what they claim to have built)
- **Clear instruction**: "Do NOT trust the report. Read actual code. Compare against ACs line by line."
- **File paths** to check

The reviewer must:

- Read actual implementation files (not just trust report)
- Compare each file against each AC
- Flag missing requirements, extra work, misunderstandings
- Report: ✅ Spec compliant OR ❌ Issues found [with file:line references]

#### 4e. Handle Spec Compliance Issues

If spec-compliance review finds issues:

- Send implementer a list of specific issues with file:line references
- Implementer fixes
- Dispatch spec-compliance review again (to the same reviewer or a different one)
- Repeat until ✅ Spec compliant

Never skip this cycle. Always get spec compliance verification before moving to quality review.

#### 4f. Dispatch Code-Quality Reviewer

Only after spec compliance passes, dispatch code-quality review using code-quality-reviewer-prompt.md. Include:

- **What was implemented** (from implementer's report + verified by spec review)
- **Standards to check against** (code-style, testing, git, observability, etc.)
- **Review criteria** (cleanliness, test quality, error handling, naming, SOLID, performance)

The reviewer must:

- Assess code quality against standards
- Check test quality (assertions verify behavior, not just mock calls)
- Evaluate error handling, naming clarity, maintainability
- Report: Approved / Needs fixes [with file:line references and severity]

#### 4g. Handle Quality Issues

If code-quality review finds issues:

- Categorize: Critical (breaks quality contract) / Important (should fix) / Minor (nice to have)
- Send implementer specific feedback
- Implementer fixes
- Dispatch quality review again
- Repeat until Approved

Quality review is judgment-based. Disagreements are OK — document them and move forward if critical issues are resolved.

#### 4h. Update stories.yml

Once BOTH reviews pass (spec compliance ✅ and quality ✅), update the story's status:

```yaml
STORY-{NNN}:
  name: [story name]
  status: passing
  verified_by: [spec_reviewer_name, code_quality_reviewer_name]
  verified_date: 2026-02-14
```

Mark the TodoWrite task complete.

### Step 5: Final Review of Entire Implementation

After all stories are passing (both reviews complete), dispatch a final review of the entire implementation:

- Run tests across all stories to verify no regressions
- Verify story interactions (do stories work together correctly?)
- Check for duplicated code across stories
- Verify no stories left half-done

This is a holistic check that the spec is fully and correctly implemented.

### Step 6: Run /verify-completion

Before claiming the spec is complete:

1. Run `/verify-completion` with all verification criteria from stories.yml
2. Verify:
   - All stories have status: passing in stories.yml
   - All tests pass (run test suite)
   - All code follows standards (spot-check against standards)
   - All changes are committed (git status clean)
3. Update stories.yml completion section with evidence
4. Move spec status from in_progress to complete (update specs/index.yml)

---

## Red Flags / Never Do This

These actions will compromise the review process:

- **Never skip reviews** — Both spec and quality reviews are mandatory gates. No exceptions.
- **Never dispatch parallel implementers** — Only one implementer per story. Parallel work on same story causes conflicts.
- **Never trust the implementer's self-report** — Spec reviewer must read actual code and verify line by line.
- **Never do quality review before spec compliance passes** — Quality review assumes the code is correct. If spec compliance fails, quality review is wasted.
- **Never merge spec and quality reviews** — Different concerns, different reviewers, separate verdicts.
- **Never let implementer be their own reviewer** — Self-review is for catching obvious mistakes. Independent review catches what implementer is blind to.
- **Never skip the final full-spec review** — After all individual stories pass, verify they work together.
- **Never claim completion without running `/verify-completion`** — Verification command is the proof.

---

## Integration with Lit SDLC Skills

### References and Hand-offs

**Before dispatching:**
- `/continue-spec` — Load spec context (may have already done this)
- `/inject-standards` — Load applicable standards into context

**During dispatch:**
- Implementer subagent works independently; you don't need other skills
- Spec-compliance reviewer works independently; uses spec-reviewer-prompt.md
- Code-quality reviewer works independently; uses code-quality-reviewer-prompt.md

**After dispatch:**
- `/verify-completion` — Run before claiming spec is done (mandatory)
- `/end-session` — After verification passes and all stories are complete, end the session with full summary

### Session Documentation

When dispatching subagents, keep session notes:
- Which subagents were assigned which stories
- What issues each review found (and how they were resolved)
- Any learnings or gotchas discovered during implementation
- Which standards were most frequently referenced

When you `/end-session`, include these notes in the session summary.

---

## Implementation Tips

- **Start with the simplest story first** — Build confidence and process clarity before complex stories
- **Reuse reviewers if possible** — The same spec reviewer across stories understands the spec context. Same quality reviewer understands code patterns.
- **Document blockers early** — If a story blocks others, resolve it before moving forward
- **Keep AC language consistent** — If reviewers find AC misunderstandings, update acs/ for clarity
- **Celebrate passing stories** — Mark each story complete in TodoWrite. Momentum matters.
- **Track time per story** — Implementer time + review time. Helps estimate future specs.

