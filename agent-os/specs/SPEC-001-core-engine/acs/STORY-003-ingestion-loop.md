# STORY-003: URI-based Bundle Ingestion Loop — Acceptance Criteria

> ACs for the event-driven ingestion pipeline that packages URIs into Bundles and broadcasts them.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Successful Broadcast | Happy path |
| AC-002 | Unsupported URIs | Validation |
| AC-003 | Empty Bundle Prevention | Edge case |

---

## Acceptance Criteria

### AC-001: Successful Broadcast

**Given** a `PluginRegistry` with two active plugins
**When** a user submits a list of valid URIs (e.g., `['file://a.md', 'file://b.md']`) for ingestion
**Then** a single `IngestionBundle` is created containing all the URIs
**And** both plugins receive the `.process_bundle()` event synchronously or asynchronously

---

### AC-002: Unsupported URIs

**Given** an ingestion request
**When** a user submits a malformed URI or a schema that no resolver supports (e.g., `unknown://xyz`)
**Then** the `ResourceResolver` throws a clear validation error
**And** the bundle is marked as failed without crashing the core engine

---

### AC-003: Empty Bundle Prevention

**Given** an ingestion request for a directory
**When** the directory URI contains no valid or supported actual files
**Then** the ingestion pipeline detects the empty state
**And** immediately returns a successful "No-Op" without broadcasting an empty bundle to plugins
