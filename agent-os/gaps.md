# Agent OS Framework Gaps

> Identified gaps, ambiguities, and open questions for future resolution.
> 
> Created: 2026-02-07

---

## Summary

| Category | Status | Priority |
|----------|--------|----------|
| Spec lifecycle | ✅ Clear | — |
| BDD workflow | ✅ Clear | — |
| Context preservation | ✅ Clear | — |
| Standards system | ✅ Clear | — |
| Code review / PR | ✅ Resolved | — |
| Deployment | ❓ Missing | TBD |
| Hotfix workflow | ❓ Missing | TBD |
| Story dependencies | ❓ Missing | TBD |
| Multi-agent coordination | ✅ Resolved | — |
| NFR tracking | ❓ Unclear | TBD |
| Refactoring workflow | ❓ Unclear | TBD |
| External tool integration | ❓ Missing | TBD |

---

## Missing Workflows

### GAP-001: Code Review & PR Workflow

**What's missing:**
- No skill or defined process for creating pull requests
- No guidance on conducting code reviews
- No workflow for merging code
- Unclear who approves what

**Current state:**
- `git.md` covers commit conventions
- Verification criteria mention "code review approved" but no process defined

**Questions to resolve:**
- Is code review part of verification, or a separate step?
- How does reviewed code get merged?
- Should there be a `/create-pr` or `/review-code` skill?

---

### GAP-002: Deployment & Release Management

**What's missing:**
- No mention of environments (dev/staging/prod)
- No deployment process or skill
- No release notes or changelog generation
- No CI/CD integration guidance

**Current state:**
- Spec lifecycle ends at `complete → archived`
- No connection between "complete" and "deployed"

**Questions to resolve:**
- Does "complete" mean deployed, or is deployment separate?
- Should deployment be tracked in specs or separately?
- How do release notes get generated from completed specs?

---

### GAP-003: Hotfix / Emergency Workflow

**What's missing:**
- No streamlined path for critical production bugs
- No guidance for security patches
- No lightweight workflow for trivial changes

**Current state:**
- All work routes through `/shape-spec`
- Guardrail GR-C02: "Don't build without a spec"

**Questions to resolve:**
- Is there a threshold for when specs are required?
- Should there be a `/hotfix` skill with abbreviated process?
- How do you balance rigor with urgency?

**Potential solution:**
- Define spec-optional criteria (e.g., "changes not affecting behavior")
- Create lightweight hotfix workflow that still preserves context

---

### GAP-004: Story Dependencies

**What's missing:**
- No mechanism to track story dependencies
- No way to mark stories as blocked
- No dependency ordering in execution plan

**Current state:**
- Stories described as "independently deliverable"
- `stories.yml` has no dependency field

**Questions to resolve:**
- How do you handle stories that must complete in order?
- Should `stories.yml` support a `depends_on` field?
- How do blocked stories get surfaced in `/start-session`?

**Potential solution:**
```yaml
stories:
  STORY-001:
    name: Create data model
    status: passing
    
  STORY-002:
    name: Implement API endpoint
    status: failing
    depends_on: [STORY-001]  # New field
```

---

### GAP-005: Refactoring / Tech Debt Workflow

**What's missing:**
- No guidance for large refactors that don't add functionality
- No workflow for tech debt paydown
- No pattern for dependency upgrades

**Questions to resolve:**
- Do refactors get full specs?
- Is there a lighter-weight pattern for tech debt?
- How do you track tech debt items vs. feature work?

**Potential solutions:**
- Add "refactor" as a spec type with streamlined requirements
- Create tech debt backlog in `roadmap.md`
- Define when refactors need specs vs. when they don't

---

## Unclear Areas

### GAP-006: Multi-Agent Coordination

**What's unclear:**
- How multiple agents avoid conflicts on same spec
- Lock/claim mechanisms for stories
- Merging parallel work

**Current state:**
- Framework mentions story parallelism as a benefit
- No coordination mechanisms defined

**Questions to resolve:**
- Is this framework designed for single-agent use?
- If multi-agent, how do agents claim/release stories?
- How do you prevent two agents from working on the same story?

**Potential solutions:**
- Add `assigned_to` field in `stories.yml`
- Define story claiming protocol
- Use file locking or external coordination

---

### GAP-007: Non-Functional Requirements (NFRs)

**What's unclear:**
- Where security requirements get captured
- Where performance requirements get tracked
- Where accessibility requirements live

**Current state:**
- Could live in domain knowledge, standards, or per-spec requirements
- No explicit structure defined

**Questions to resolve:**
- Should NFRs be part of every spec template?
- Should there be an NFR standards file?
- How do NFRs flow into acceptance criteria?

**Potential solutions:**
- Add NFR section to spec `README.md` template
- Create `standards/nfr.md` with baseline requirements
- Include NFR checklist in `/derive-acs`

---

### GAP-008: Story ↔ AC ↔ BDD Test Cardinality

**What's unclear:**
- Exact relationship between stories, ACs, and tests
- Can one AC generate multiple test cases?
- How parameterized tests map to ACs

**Current assumption:**
- 1 story → N ACs → N tests (roughly 1:1 AC to test case)
- Parameterized tests cover variations of single AC

**Questions to resolve:**
- Should this be explicitly documented?
- Is there a recommended ratio (e.g., 3-7 ACs per story)?

---

### GAP-009: Spec Changes After Implementation Starts

**What's unclear:**
- How to handle requirement changes mid-implementation
- Whether humans can modify `stories.yml`
- How scope changes get tracked

**Current state:**
- Guardrail says agents can't add/remove stories
- No guidance for humans

**Current assumption:**
- Humans can modify stories; agents cannot (scope creep prevention)

**Questions to resolve:**
- Should spec changes create a new version or modify in place?
- How do you document scope changes that occur?
- Should there be a `/modify-spec` skill?

---

## Missing Integrations

### GAP-010: External Tool Integration

**What's missing:**
- No integration with issue trackers (Jira, GitHub Issues, Linear)
- No CI/CD pipeline integration
- No communication tool integration (Slack)
- No observability linkage (specs to metrics)

**Questions to resolve:**
- Is this intentionally left to implementers?
- Should there be optional integration patterns?
- How do specs link to external issue IDs?

**Potential solutions:**
- Add optional `external_id` field to specs
- Document integration patterns in a guide
- Create example CI/CD workflow

---

### GAP-011: Component-Details Initialization

**What's missing:**
- No workflow for documenting existing components
- No equivalent to `/discover-standards` for components
- No guidance on when/how component-details get created

**Current state:**
- `/investigate` updates component-details as side effect
- No proactive documentation skill

**Questions to resolve:**
- Should there be a `/document-component` skill?
- When should component-details be created?
- What's the minimum viable documentation?

---

## Template Improvements

### GAP-012: Empty Template Files

**What's missing:**
- Example content in template files
- Placeholder markers showing expected format

**Affected files:**
- `product/mission.md`
- `product/roadmap.md`
- `product/domain/terminology.md`
- `product/domain/business-rules.md`
- `context/architecture/system-overview.md`

**Questions to resolve:**
- Should templates include example content?
- Should placeholders be `[PLACEHOLDER]` or comments?

**Potential solution:**
Add example content with clear markers:

```markdown
# Mission

<!-- Replace this section with your mission statement -->

## Example Format

**Mission:** [One sentence describing what you're building and for whom]

**Vision:** [Where this is going in 2-3 years]

**Objectives:**
1. [Measurable objective]
2. [Measurable objective]
```

---

## Resolution Tracking

| Gap ID | Status | Resolved Date | Resolution |
|--------|--------|---------------|------------|
| GAP-001 | Resolved | 2026-02-14 | SPEC-001: Created request-code-review and receive-code-review skills |
| GAP-002 | Open | — | — |
| GAP-003 | Open | — | — |
| GAP-004 | Open | — | — |
| GAP-005 | Open | — | — |
| GAP-006 | Resolved | 2026-02-14 | SPEC-001: Created dispatch-subagents skill with implementer + reviewer prompts |
| GAP-007 | Open | — | — |
| GAP-008 | Open | — | — |
| GAP-009 | Open | — | — |
| GAP-010 | Open | — | — |
| GAP-011 | Open | — | — |
| GAP-012 | Open | — | — |

---

_Last updated: 2026-02-14_
