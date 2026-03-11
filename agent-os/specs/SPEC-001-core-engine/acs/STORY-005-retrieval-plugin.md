# STORY-005: Document Retrieval Plugin — Acceptance Criteria

> ACs for a dedicated plugin and ResourceResolver that fetches full document payloads given a URI, handling local vs remote pointers.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Fetches Local DB Markdown | Happy path |
| AC-002 | Fetches Live File Content via URI Pointer | Happy path |
| AC-003 | Handles Unreachable URI Pointers | Edge case |

---

## Acceptance Criteria

### AC-001: Fetches Local DB Markdown

**Given** a chunk of data was explicitly ingested with the `store_local=True` flag
**When** the AI client calls `get_full_document`
**Then** the `ResourceResolver` bypasses the network/file-system
**And** fetches the exact JSON document payload directly from the `StorageAdapter` DB

---

### AC-002: Fetches Live File Content via URI Pointer

**Given** an ingested bundle that was stored purely as a Pointer (URI) without duplicating the payload locally
**When** the AI client calls `get_full_document`
**Then** the `ResourceResolver` successfully accesses the live pointer (e.g., local disk or remote fetch)
**And** streams the live content back to the client

---

### AC-003: Handles Unreachable URI Pointers

**Given** an AI client requests a URI pointer that has been deleted or moved since ingestion
**When** the `ResourceResolver` attempts to fetch the target
**Then** it gracefully catches the `404` or `FileNotFoundError`
**And** returns a clean MCP Error string indicating the document is no longer available at that Pointer
