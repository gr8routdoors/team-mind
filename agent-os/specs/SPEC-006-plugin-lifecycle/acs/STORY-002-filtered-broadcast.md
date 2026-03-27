# STORY-002: Filtered Observer Broadcast — Acceptance Criteria

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Unfiltered Observer Gets All Events | Happy path |
| AC-002 | Filtered Observer Gets Only Matching Events | Happy path |
| AC-003 | Filter by Plugin Only | Happy path |
| AC-004 | Filter by Doctype Only | Happy path |
| AC-005 | Combined Filter | Integration |
| AC-006 | No Matching Events Skips Observer | Edge case |
| AC-007 | Mixed Filtered and Unfiltered Observers | Integration |

---

### AC-001: Unfiltered Observer Gets All Events

**Given** an observer with `event_filter = None`
**When** the pipeline broadcasts 5 events from 3 different plugins
**Then** the observer receives all 5 events

### AC-002: Filtered Observer Gets Only Matching Events

**Given** an observer with `event_filter = EventFilter(plugins=["plugin_a"])`
**When** the pipeline broadcasts events from `plugin_a` and `plugin_b`
**Then** the observer receives only events from `plugin_a`

### AC-003: Filter by Plugin Only

**Given** an observer filtering for `plugins=["java_plugin"]`
**When** events from `java_plugin`, `markdown_plugin`, and `travel_plugin` are broadcast
**Then** the observer receives only `java_plugin` events

### AC-004: Filter by Doctype Only

**Given** an observer filtering for `doctypes=["code_signature"]`
**When** events with doctypes `code_signature`, `markdown_chunk`, and `user_interest` are broadcast
**Then** the observer receives only `code_signature` events

### AC-005: Combined Filter

**Given** an observer filtering for `plugins=["java_plugin"]` and `doctypes=["code_signature"]`
**When** events include `java_plugin:code_signature`, `java_plugin:test_case`, and `python_plugin:code_signature`
**Then** the observer receives only the `java_plugin:code_signature` event

### AC-006: No Matching Events Skips Observer

**Given** an observer filtering for `plugins=["nonexistent_plugin"]`
**When** events from other plugins are broadcast
**Then** the observer's `on_ingest_complete` is not called

### AC-007: Mixed Filtered and Unfiltered Observers

**Given** observer A with no filter and observer B filtering for `plugins=["plugin_x"]`
**When** events from `plugin_x` and `plugin_y` are broadcast
**Then** observer A receives all events
**And** observer B receives only `plugin_x` events
