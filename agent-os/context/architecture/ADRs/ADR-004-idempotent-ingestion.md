# ADR-004: Idempotent Ingestion via Content Hashing, Plugin Versioning, and IngestionContext

**Status:** Accepted
**Date:** 2026-03-26
**Spec:** SPEC-005 (Idempotent Ingestion with Content Hashing)
**See also:** [Plugin Developer Guide](../plugin-developer-guide.md), [ADR-002: Plugin Architecture](ADR-002-plugin-architecture.md)

## Context

Team Mind's ingestion pipeline (SPEC-001, SPEC-003) broadcasts URIs to all registered `IngestProcessor` plugins. However, it treats every ingestion as a fresh insert — there is no awareness of whether a URI has been ingested before, whether the content has changed, or whether the plugin processing it has been updated.

This creates three problems:

1. **Duplicate rows on re-ingestion.** Ingesting the same file twice creates duplicate chunks. Old and new chunks compete in search results, diluting relevance.
2. **Wasted compute.** An idempotent plugin (like MarkdownPlugin) re-chunks, re-embeds, and re-stores identical content — work that produces the same output.
3. **No version-aware re-processing.** When a plugin updates its logic (e.g., better chunking strategy in v2.0), there's no way to identify documents that were processed by the old version and may benefit from re-processing.

## Decision

The platform provides structured **IngestionContext** to processors for every URI, enabling them to make informed decisions about whether to skip, re-process, or replace content. The platform computes the context; plugins decide what to do with it.

### 1. Content Hash on Documents

Every document row stores a SHA-256 hash of its content at ingestion time:

```sql
ALTER TABLE documents ADD COLUMN content_hash TEXT;
```

The hash is computed by the plugin from whatever it considers the "content" (e.g., the raw chunk text for MarkdownPlugin). The platform stores it and uses it for comparison on re-ingestion.

**Why SHA-256:** Standard, collision-resistant, fast enough for our scale. Not used for security — purely content identity.

### 2. Plugin Version on Documents

Every document row records which version of the plugin processed it:

```sql
ALTER TABLE documents ADD COLUMN plugin_version TEXT DEFAULT '0.0.0';
```

Plugins declare a `version` property on `IngestProcessor`:

```python
class MarkdownPlugin(IngestProcessor):
    @property
    def version(self) -> str:
        return "1.0.0"
```

Default is `"0.0.0"` for backward compatibility. The version is a free-form string — the platform doesn't parse it, just stores and compares for equality.

### 3. IngestionContext — Platform-Provided, Plugin-Consumed

Before broadcasting a bundle to processors, the pipeline queries the database for each URI and builds an `IngestionContext`:

```python
@dataclass
class IngestionContext:
    uri: str
    is_update: bool                     # URI+plugin+doctype already exists
    content_changed: bool | None        # True/False/None (None = no prior hash)
    plugin_version_changed: bool        # Current version != stored version
    previous_doc_ids: list[int]         # IDs of existing rows
    previous_content_hash: str | None   # Hash from prior ingestion
    previous_plugin_version: str | None # Version from prior ingestion
```

Contexts are attached to the `IngestionBundle` and keyed by URI. Each processor gets context specific to its own plugin + doctype — not other processors' history.

### 4. Plugin Decision Matrix

The platform provides the signals. Plugins make the call:

| is_update | content_changed | version_changed | Typical action |
|-----------|----------------|-----------------|----------------|
| false | N/A | N/A | Fresh insert (new content) |
| true | false | false | Skip (nothing changed) |
| true | true | false | Wipe and replace (content updated) |
| true | false | true | Re-process (plugin logic changed) |
| true | true | true | Wipe and replace (both changed) |

**Why the plugin decides, not the platform:**
- A deterministic parser (MarkdownPlugin) should skip unchanged content — same input always produces same output.
- A non-deterministic analyzer (e.g., sentiment analysis via LLM) may want to re-process the same content to get updated results.
- A plugin upgrading from v1 to v2 may need to re-process everything, or only docs from specific old versions.

The platform cannot make these decisions generically. It provides the information; plugins apply their domain knowledge.

### 5. Composite Index for Efficient Lookups

```sql
CREATE INDEX idx_documents_uri_plugin_doctype ON documents(uri, plugin, doctype);
```

The URI lookup happens once per URI before the processor broadcast. With the composite index, this is a fast indexed query even at scale.

## Alternatives Considered

### 1. Platform auto-replaces on duplicate URI

The platform automatically deletes old rows and inserts new ones when a URI is re-ingested.

**Rejected because:**
- Non-deterministic plugins may want to re-process the same content without deleting old results.
- Auto-replace destroys accumulated usage_score weights — a document that earned a high score through feedback would lose it.
- Plugins should control when deletion happens, using `delete_by_uri` explicitly.

### 2. Content hash in metadata JSON instead of a column

Store the hash inside the `metadata` JSON blob rather than a dedicated column.

**Rejected because:**
- Querying hashes across documents would require JSON extraction — slower than a column comparison.
- The hash is a first-class concept used by the platform, not arbitrary plugin metadata.

### 3. Platform-managed semantic deduplication (vector similarity)

Before storing a chunk, check if a semantically similar chunk already exists by running a KNN query.

**Rejected because:**
- Expensive: a KNN search on every insert would significantly slow ingestion.
- Non-deterministic: similarity thresholds are subjective — what's "similar enough" varies by domain.
- URI-based idempotency with content hashing covers the common cases (re-ingestion, file updates) deterministically and cheaply.
- If needed in the future, this is better suited for the Librarian validation pipeline (Phase 3).

### 4. Integer auto-incrementing plugin version

Use an integer version instead of a string.

**Rejected because:**
- Strings are more flexible — plugins can use semver, date-based versions, or any format.
- The platform only needs equality comparison, not ordering. Strings work fine for that.

## Consequences

### Positive

- **Idempotent ingestion by default.** Plugins like MarkdownPlugin can skip unchanged content with zero wasted compute.
- **Version-aware re-processing.** Plugin upgrades can trigger targeted re-ingestion without re-ingesting everything.
- **Clean separation.** Platform provides context, plugins decide. No forced behavior.
- **Efficient.** One indexed query per URI per ingest. Content hash comparison is a string equality check.
- **Backward compatible.** `version` defaults to `"0.0.0"`, `content_hash` is nullable, existing plugins work unchanged.

### Negative

- **Hash computation cost.** Plugins must hash their content before saving. SHA-256 is fast but it's additional work per chunk. Negligible at current scale.
- **Context lookup adds latency.** One query per URI before broadcasting. Amortized by the compute saved from skipping unchanged content.
- **Plugin version is honor-system.** If a plugin doesn't update its version string when logic changes, old docs won't be flagged for re-processing. Mitigated by documentation and developer guide.

### Neutral

- The `IngestionContext` is per-(URI, processor) pair. Two processors ingesting the same URI get independent contexts reflecting their own history.
- Content hash covers the "same URI, same content" case. It does NOT cover the "different URI, similar content" case — that remains out of scope.
