# ADR-007: Three-Type Model and Semantic Type Routing

**Status:** Accepted
**Date:** 2026-03-27
**See also:** [ADR-001: Plugin-Scoped Doctypes](ADR-001-plugin-scoped-doctypes.md), [ADR-005: Plugin Lifecycle](ADR-005-plugin-lifecycle.md), [Plugin Developer Guide](../plugin-developer-guide.md)

## Context

Team Mind's ingestion pipeline currently uses a broadcast-and-self-filter model: every URI is sent to every `IngestProcessor`, and each plugin decides independently whether it cares (e.g., MarkdownPlugin checks for `.md` file extensions). This creates several problems:

1. **No semantic awareness.** The pipeline doesn't know what kind of data is being ingested — just URIs. A JSON file could be a travel profile, a weather report, or a build manifest. Plugins can't distinguish these without inspecting the content.
2. **No routing control.** The client has no way to say "this data is a travel profile — route it to the travel plugin." Everything goes to everything.
3. **Conflated type concepts.** Our `doctype` field on documents conflates what data *means* (input semantics), how it's *encoded* (media type), and what the plugin *produced* (output type). These are three distinct concerns.
4. **Plugins must hardcode file type filtering.** MarkdownPlugin checks `.md` extensions. A Java plugin would check `.java`. This logic should be declarative, not imperative.

Additionally, the current EventFilter on IngestObserver only supports filtering by `plugin` and `doctype`. With the three-type model, observers need to filter by semantic type as well — "notify me when architecture documentation is ingested" regardless of which plugin processed it.

## Decision

We introduce a **three-type model** that distinguishes what data means, how it's encoded, and what the plugin produces. We replace broadcast-and-self-filter with **semantic-type-based routing** where plugins are matched to content by semantic type at registration time.

### 1. Three Type Taxonomy

| Type | What it answers | Set by | Persisted on | Example |
|------|----------------|--------|-------------|---------|
| **Semantic type** | "What does this data *mean*?" | Ingestion caller | `documents.semantic_type` | `architecture_docs`, `travel_profile`, `payment_service` |
| **Media type** | "How is this data *encoded*?" | Plugin (auto-detected) | `documents.media_type` | `text/markdown`, `application/json`, `text/x-java` |
| **Record type** (renamed from doctype) | "What did the plugin *produce*?" | Plugin, at write time | `documents.record_type` | `markdown_chunk`, `code_signature`, `user_interest` |

**Relationship between types:**
- One semantic type can arrive in multiple media types (travel profile as JSON, CSV, or spreadsheet)
- One semantic type can produce multiple record types (travel profile → `user_interest` + `destination_preference`)
- One media type can carry multiple semantic types (JSON could be anything)
- One plugin can produce multiple record types from one semantic type

### 2. Semantic Type Routing (replaces broadcast)

Plugins no longer receive every URI. Instead:

1. **Plugins declare media type capabilities at build time** — "I can parse `.md`, `.txt`, `.rst`"
2. **Semantic types are mapped to plugins at registration time** — "For `architecture_docs`, use MarkdownPlugin and JavaPlugin"
3. **The ingestion caller specifies semantic type** — `ingest(uris, semantic_type="architecture_docs")`
4. **The pipeline routes only to registered plugins** for that semantic type

**Registration-time configuration, not build-time:**
```python
# At registration (not in plugin code):
register_plugin(
    module_path="team_mind_mcp.markdown.MarkdownPlugin",
    semantic_types=["architecture_docs", "meeting_transcripts", "design_specs"],
)

# Later, add a new semantic type without reinstalling:
update_plugin_semantic_types(
    plugin_name="markdown_plugin",
    semantic_types=["architecture_docs", "meeting_transcripts", "design_specs", "onboarding_guides"],
)
```

This means:
- The MarkdownPlugin doesn't hardcode which semantic types it handles
- Knowledge managers configure the mapping at deployment time
- Semantic types can be added or removed without plugin changes or restarts
- A plugin's media type capabilities are intrinsic; its semantic type assignments are configurable

### Available vs Enabled: Plugin Activation Model

A plugin exists in one of three states:

| State | Code installed? | Registered? | Has semantic types? | Processes content? |
|-------|----------------|------------|--------------------|--------------------|
| **Unavailable** | No | No | — | No |
| **Available** | Yes | Yes | No | No |
| **Enabled** | Yes | Yes | Yes (specific types or `*`) | Yes, for matching types |

**Key design: no semantic types = no processing.** A registered plugin with no semantic type associations is idle — available but not actively processing content. This is intentional:

- **Compile-time plugins are available by default, not enabled by default.** Registering a plugin in `cli.py` makes it available, but it doesn't process ingestion until an admin associates semantic types with it.
- **`*` is explicit opt-in for "process everything"** — not the default. A wildcard semantic type must be deliberately configured.
- **Safety:** A newly installed plugin doesn't automatically process all historical data. The admin explicitly activates it for specific semantic types.

The `register()` method on PluginRegistry accepts optional `semantic_types`:
```python
# Core plugins registered at startup — available but not routing until configured
gateway.registry.register(markdown_plugin, semantic_types=["architecture_docs"])

# Or available with no semantic types (idle until configured)
gateway.registry.register(markdown_plugin)
```

**First-run experience:** A fresh install requires the admin to associate core plugins with semantic types. The CLI could offer a `--enable-defaults` flag or an interactive setup to streamline this.

### 3. Media Type as Plugin Capability

Plugins declare what media types they can parse:

```python
class MarkdownPlugin(IngestProcessor):
    @property
    def supported_media_types(self) -> list[str]:
        return ["text/markdown", "text/plain"]
```

Within a bundle routed by semantic type, the plugin only receives URIs matching its media type capabilities. For a Maven project ingested as `semantic_type="payment_service"`:
- JavaPlugin (media: `text/x-java`) → gets `.java` files
- MarkdownPlugin (media: `text/markdown`) → gets `.md` files
- MavenPlugin (media: `application/xml`) → gets `pom.xml`

Media type can be auto-detected from file extension or explicitly hinted.

### 4. Record Type (renamed from Doctype)

`doctype` is renamed to `record_type` throughout the system. This is a clearer name for what the plugin produces and stores. The concept is unchanged — plugin-scoped, declared via the spec, used for querying.

### 5. Updated IngestionEvent and EventFilter

IngestionEvent gains `semantic_type`:

```python
@dataclass
class IngestionEvent:
    plugin: str
    record_type: str          # renamed from doctype
    semantic_type: str         # NEW — from the ingest request
    uris: list[str]
    doc_ids: list[int]
```

EventFilter gains `semantic_types`:

```python
@dataclass
class EventFilter:
    plugins: list[str] | None = None
    record_types: list[str] | None = None   # renamed from doctypes
    semantic_types: list[str] | None = None  # NEW
```

This enables observers to filter on any dimension:
- "Notify me on any `payment_service` ingest" → `semantic_types=["payment_service"]`
- "Notify me when `code_signature` records are written" → `record_types=["code_signature"]`
- "Notify me on anything from `java_plugin`" → `plugins=["java_plugin"]`

### 6. Schema Changes

```sql
-- Rename doctype → record_type, add semantic_type and media_type
ALTER TABLE documents RENAME COLUMN doctype TO record_type;
ALTER TABLE documents ADD COLUMN semantic_type TEXT DEFAULT '';
ALTER TABLE documents ADD COLUMN media_type TEXT DEFAULT '';

-- Add semantic_types to registered_plugins
ALTER TABLE registered_plugins ADD COLUMN semantic_types JSON;
ALTER TABLE registered_plugins ADD COLUMN supported_media_types JSON;

-- Update indexes
CREATE INDEX idx_documents_semantic_type ON documents(semantic_type);
CREATE INDEX idx_documents_record_type ON documents(record_type);
```

## Alternatives Considered

### 1. Keep broadcast-and-self-filter

Every plugin gets every URI and decides what to process.

**Rejected because:**
- Plugins can't distinguish semantic types from URIs alone (JSON is JSON).
- Wastes compute sending irrelevant URIs to every plugin.
- Forces every plugin to implement filtering logic.

### 2. MIME-type-only routing (no semantic types)

Route based on file extension / MIME type.

**Rejected because:**
- MIME type tells you the encoding, not the meaning. `application/json` could be a travel profile, weather data, or a build manifest.
- Doesn't enable "process this Maven project as a unit."
- Doesn't enable observer filtering by domain ("notify me about architecture docs").

### 3. Hardcode semantic types in plugin code

Plugins declare `supported_semantic_types` as a property.

**Rejected because:**
- The set of semantic types is unbounded and deployment-specific.
- MarkdownPlugin can handle any semantic type that comes as `.md` — hardcoding a list in the plugin is artificially limiting.
- Registration-time configuration is more flexible and doesn't require code changes.

### 4. Keep "doctype" naming

Don't rename to record_type.

**Rejected because:**
- With three type concepts, "doctype" is ambiguous — is it the input type, the encoding, or the output?
- "Record type" clearly communicates "what the plugin wrote to the database."
- We also want to persist semantic_type and media_type, so the naming needs to be distinct.

### 5. Auto-enable compile-time plugins with wildcard semantic type

Compile-time plugins (registered in cli.py) automatically process all content by default (`semantic_types=["*"]`).

**Rejected because:**
- Processing everything is potentially prohibitive for performance at scale.
- A newly added plugin shouldn't automatically process all existing and incoming content without explicit admin intent.
- The available-vs-enabled model is safer: plugins are available by default, enabled when the admin associates semantic types.

## Consequences

### Positive

- **Intentional routing.** Plugins only receive content they're registered to handle.
- **Clear type semantics.** Three distinct concepts, three distinct names, three distinct columns.
- **Flexible configuration.** Semantic types are managed at registration time, not hardcoded.
- **Observer precision.** EventFilter can match on semantic type, record type, or plugin independently.
- **Safe activation.** Plugins don't process content until explicitly enabled with semantic types.
- **Foundation for meta-plugins.** (Future) Observer-triggered secondary ingestion composes naturally with semantic type routing.

### Negative

- **Breaking rename.** `doctype` → `record_type` touches many files. Mitigated by the small codebase and comprehensive tests.
- **Routing complexity.** The pipeline goes from "send to all" to "look up registrations, match media types, route." More logic, more tests needed.
- **Caller must know semantic types.** The ingestion caller needs to specify what the data means. This is additional burden but also additional clarity.
- **First-run friction.** Fresh install requires admin to associate plugins with semantic types before ingestion works. Mitigated by CLI setup tooling.

### Neutral

- Media type detection from file extension is a reasonable heuristic. Explicit hints can override.
- The `registered_plugins` table already exists — adding `semantic_types` and `supported_media_types` columns is a natural extension.
- Meta-plugin / chained processing patterns (observer triggers secondary ingest) are documented as a future roadmap item, not part of this ADR.
