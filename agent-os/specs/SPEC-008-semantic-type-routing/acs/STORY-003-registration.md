# STORY-003: Semantic Types on Plugin Registration — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Store Semantic Types on Registration | Happy path |
| AC-002 | Store Supported Media Types on Registration | Happy path |
| AC-003 | Retrieve Registered Semantic Types | Happy path |
| AC-004 | Update Semantic Types Without Reinstall | Happy path |

---

### AC-001: Store Semantic Types on Registration

**Given** a plugin registering with `semantic_types=["architecture_docs", "meeting_notes"]`
**When** the registration is persisted
**Then** the `registered_plugins` row has `semantic_types` stored as JSON `["architecture_docs", "meeting_notes"]`

### AC-002: Store Supported Media Types on Registration

**Given** a plugin registering with `supported_media_types=["text/markdown", "text/plain"]`
**When** the registration is persisted
**Then** the `registered_plugins` row has `supported_media_types` stored as JSON `["text/markdown", "text/plain"]`

### AC-003: Retrieve Registered Semantic Types

**Given** a registered plugin with `semantic_types=["architecture_docs"]`
**When** the plugin record is retrieved
**Then** `semantic_types` is deserialized to `["architecture_docs"]`

### AC-004: Update Semantic Types Without Reinstall

**Given** a registered plugin with `semantic_types=["architecture_docs"]`
**When** the plugin is re-registered with `semantic_types=["architecture_docs", "design_docs"]`
**Then** the `semantic_types` column is updated to `["architecture_docs", "design_docs"]`
**And** no uninstall/reinstall cycle is required
