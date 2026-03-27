# STORY-004: Pipeline and MCP Tool Propagation — Acceptance Criteria

---

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Pipeline Accepts Hint | Happy path |
| AC-002 | MCP Tool Accepts Hint | Happy path |
| AC-003 | CLI Accepts Flag | Happy path |
| AC-004 | No Hint Means None | Edge case |

---

### AC-001: Pipeline Accepts Hint
**Given** `pipeline.ingest(uris, reliability_hint=0.8)`
**When** the bundle is created
**Then** `bundle.reliability_hint` is `0.8`

### AC-002: MCP Tool Accepts Hint
**Given** `ingest_documents(uris=[...], reliability_hint=0.7)`
**When** the pipeline processes the request
**Then** the bundle has `reliability_hint=0.7`

### AC-003: CLI Accepts Flag
**Given** `team-mind-mcp ingest /path --reliability 0.8`
**When** the pipeline processes the targets
**Then** the bundle has `reliability_hint=0.8`

### AC-004: No Hint Means None
**Given** `pipeline.ingest(uris)` with no reliability_hint
**When** the bundle is created
**Then** `bundle.reliability_hint` is `None`
