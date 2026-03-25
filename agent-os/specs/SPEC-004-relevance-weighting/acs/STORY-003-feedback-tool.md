# STORY-003: Provide Feedback MCP Tool — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Tool Registered | Happy path |
| AC-002 | Positive Feedback Increases Score | Happy path |
| AC-003 | Negative Feedback Decreases Score | Happy path |
| AC-004 | Signal Clamped to Range | Validation |
| AC-005 | Nonexistent Doc ID Errors | Error |
| AC-006 | Reason Stored | Happy path |
| AC-007 | Last Accessed Updated | Happy path |

---

### AC-001: Tool Registered

**Given** the `FeedbackPlugin` is registered
**When** MCP tools are listed
**Then** `provide_feedback` appears with its input schema

---

### AC-002: Positive Feedback Increases Score

**Given** a document with `usage_score=0.0`
**When** `provide_feedback(doc_id, signal=3)` is called
**Then** `usage_score` becomes `3.0`

---

### AC-003: Negative Feedback Decreases Score

**Given** a document with `usage_score=2.0`
**When** `provide_feedback(doc_id, signal=-2)` is called
**Then** `usage_score` becomes `0.0`

---

### AC-004: Signal Clamped to Range

**Given** any document
**When** `provide_feedback` is called with `signal=10` (outside -5 to +5)
**Then** a validation error is returned

---

### AC-005: Nonexistent Doc ID Errors

**Given** no document with `id=99999`
**When** `provide_feedback(doc_id=99999, signal=1)` is called
**Then** an error is returned indicating the document does not exist

---

### AC-006: Reason Stored

**Given** a document
**When** `provide_feedback(doc_id, signal=1, reason="very helpful")` is called
**Then** the feedback is applied and the reason is available for audit

---

### AC-007: Last Accessed Updated

**Given** a document
**When** `provide_feedback` is called
**Then** `last_accessed` in `doc_weights` is updated to the current timestamp
