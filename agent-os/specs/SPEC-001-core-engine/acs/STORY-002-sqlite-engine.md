# STORY-002: SQLite Embedded Storage Engine — Acceptance Criteria

> ACs for implementing the database abstraction layer natively using SQLite with JSON1 and sqlite-vec support.

---

## Summary

| AC | Title | Coverage |
|----|-------|----------|
| AC-001 | Database Initialization | Happy path |
| AC-002 | Vector Extension Required | Error condition |
| AC-003 | Save Payload | Happy path |
| AC-004 | Retrieve by Vector Similarity | Core functionality |

---

## Acceptance Criteria

### AC-001: Database Initialization

**Given** a valid SQLite file path
**When** the `StorageAdapter` is initialized
**Then** it creates the necessary tables for documents, metadata, and vectors if they do not exist
**And** the connection pool is established

---

### AC-002: Vector Extension Required

**Given** an environment where `sqlite-vec` cannot be compiled or loaded
**When** the `StorageAdapter` attempts to initialize
**Then** it throws a clear initialization error stating the missing dependency
**And** gracefully exits before accepting connections

---

### AC-003: Save Payload

**Given** an active `StorageAdapter`
**When** a plugin attempts to insert a document with a 768-dimensional vector, an origin URI, and arbitrary JSON metadata
**Then** the record is successfully committed to the database
**And** an internal document ID is returned

---

### AC-004: Retrieve by Vector Similarity

**Given** a populated vector table with known embeddings
**When** a KNN semantic query is executed with a target vector and a `limit=5`
**Then** exactly 5 (or fewer) results are returned
**And** they are ordered descending by similarity score
