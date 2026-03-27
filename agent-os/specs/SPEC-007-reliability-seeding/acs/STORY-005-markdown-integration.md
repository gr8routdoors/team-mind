# STORY-005: MarkdownPlugin Reliability Integration — Acceptance Criteria

---

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Uses Hint When Provided | Happy path |
| AC-002 | Falls Back to Default | Happy path |
| AC-003 | No Hint No Default Uses Zero | Edge case |
| AC-004 | Plugin Can Override Hint | Happy path |

---

### AC-001: Uses Hint When Provided
**Given** a bundle with `reliability_hint=0.8`
**When** MarkdownPlugin processes the bundle
**Then** saved documents have `usage_score=0.8`

### AC-002: Falls Back to Default
**Given** a bundle with `reliability_hint=None` and MarkdownPlugin declares `default_reliability=0.5`
**When** MarkdownPlugin processes the bundle
**Then** saved documents have `usage_score=0.5`

### AC-003: No Hint No Default Uses Zero
**Given** a bundle with `reliability_hint=None` and a plugin with `default_reliability=None`
**When** the plugin processes the bundle
**Then** saved documents have `usage_score=0.0` (equivalent to no seeding)

### AC-004: Plugin Can Override Hint
**Given** a plugin that always sets initial_score to 0.95 regardless of hint
**When** it processes a bundle with `reliability_hint=0.3`
**Then** saved documents have `usage_score=0.95` (plugin has last word)
