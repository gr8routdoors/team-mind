# Guardrails

> What NOT to do — anti-patterns and lessons learned from failures.

---

## Architecture

### GR-A01: Don't Add Caching Without Fixing Root Cause
**Don't:** Add Redis as a band-aid over bad data fetching.
**Instead:** Fix the data fetching pattern first.

### GR-A02: Don't Conflate Service Responsibilities
**Don't:** Let a service handle CRUD operations it shouldn't own.
**Instead:** Keep clear separation between processing logic and data management.

---

## Code

### GR-C01: Don't Reverse-Engineer Behavior from Code
**Don't:** Understand what code should do by reading buggy implementation.
**Instead:** Write specifications first, validate against code.

### GR-C02: Don't Build Without a Spec
**Don't:** Start implementing features without a written specification.
**Instead:** Use `/shape-spec` to create spec documentation first.

### GR-C03: Don't Disable Tests
**Don't:** Don't disable tests that fail as a result of a change.
**Instead:** Triage why the test is failing to understand if the change has defects.

### GR-C04: Don't Change Test Expectations To Get Them To Pass
**Don't:** Don't change a test's expectations to get them to pass, unless specifically instructed to do so.
**Instead:** Triage why the test is failing to understand if the change has defects.

---

## Data

### GR-D01: Don't Fetch Exponentially
**Don't:** Make N+1 queries or fetch entire object graphs for simple operations.
**Instead:** Design data access patterns that scale linearly.

---

## Process

### GR-P01: Don't Skip Pre-Build Validation
**Don't:** Start implementing without validating dependencies.
**Instead:** Complete Pre-Build Validation checklist first.

### GR-P02: Don't End Sessions Without Context Preservation
**Don't:** Finish significant work without documenting learnings.
**Instead:** Run `/end-session` to create session summary and update artifacts.

### GR-P03: Don't Claim Completion Without Verification Evidence
**Don't:** Say "done", "fixed", "passing", or mark stories as passing without running verification commands.
**Instead:** Run the verification command, read the output, cite specific evidence, then claim the result.

---

## Unattended Mode

When running autonomously (without Devon present), these additional guardrails apply:

### GR-U01: Don't Modify Database Schemas
**Don't:** Create, alter, or drop database tables/columns unattended.
**Instead:** Document proposed schema changes for Devon to review.

### GR-U02: Don't Change Spec Requirements
**Don't:** Modify functional requirements or acceptance criteria without approval.
**Instead:** Flag proposed changes in session summary for review.

### GR-U03: Don't Assume Business Logic
**Don't:** Guess at business rules or domain logic when uncertain.
**Instead:** Document the assumption and skip — flag for Devon to clarify.

### GR-U04: Don't Make Destructive Changes
**Don't:** Delete files, drop data, or make irreversible changes.
**Instead:** Propose changes, document rationale, wait for approval.

### GR-U05: Don't Skip Session Summary
**Don't:** End unattended work without comprehensive documentation.
**Instead:** Always run `/end-session` with extra detail on decisions and assumptions.

### GR-U06: Don't Exceed Scope
**Don't:** Expand beyond the specific task assigned.
**Instead:** Complete the assigned task, document related improvements for later.

---

## Recently Added

| ID | Title | Added | Source |
|----|-------|-------|--------|
| GR-P03 | Don't Claim Completion Without Verification Evidence | 2026-02-14 | STORY-002 |
| GR-A02 | Don't Conflate Service Responsibilities | 2026-02-03 | Environment reset |
| GR-C02 | Don't Build Without a Spec | 2026-02-03 | Environment reset |
| GR-D01 | Don't Fetch Exponentially | 2026-02-03 | Environment reset |
| GR-P02 | Don't End Sessions Without Context Preservation | 2026-02-03 | Workflow update |
| GR-U01–U06 | Unattended Mode Guardrails | 2026-02-03 | Workflow update |

---

_Last updated: 2026-02-14_
