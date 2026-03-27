# SPEC-007: Reliability Seeding — Design

## Overview

Three-layer reliability seeding ensures documents enter the knowledge base with appropriate initial quality scores. The ingest hint is always available to plugins; plugins decide the final seed value.

## Components

| Component | Type | Change |
|-----------|------|--------|
| IngestionBundle | Data Model | **Extended** — `reliability_hint: float | None` field. |
| DoctypeSpec | Data Model | **Extended** — `default_reliability: float | None` field. |
| StorageAdapter | Abstraction | **Extended** — `initial_score` parameter on `save_payload`. |
| IngestionPipeline | Event Loop | **Extended** — `reliability_hint` parameter on `ingest()`. |
| IngestionPlugin | Plugin | **Extended** — `reliability_hint` parameter on `ingest_documents` MCP tool. |
| MarkdownPlugin | Plugin | **Updated** — Uses three-layer reliability resolution. |

## Data Flow

### Three-layer resolution

```
1. Caller triggers ingestion with reliability_hint=0.8
     (e.g., "this is from the architecture repo")

2. Pipeline attaches hint to IngestionBundle
     bundle.reliability_hint = 0.8

3. Plugin receives bundle, reads hint and its own default:
     hint = bundle.reliability_hint          # 0.8 (from caller)
     default = self.doctypes[0].default_reliability  # 0.6 (from doctype)

4. Plugin decides final reliability:
     # Strategy A: prefer hint over default
     final = hint if hint is not None else default

     # Strategy B: take the max
     final = max(hint or 0, default or 0)

     # Strategy C: ignore hint, always use domain knowledge
     final = 0.95  # "I know my data is highly reliable"

5. Plugin passes final value to save_payload:
     storage.save_payload(..., initial_score=final)

6. StorageAdapter seeds usage_score to the initial_score value:
     INSERT INTO doc_weights (doc_id, usage_score, signal_count) VALUES (?, ?, 0)
     # signal_count stays 0 — initial_score is not a "signal"
```

### Interaction with existing weighting

- `initial_score` sets the starting `usage_score`. It's not a signal — `signal_count` stays 0.
- Future feedback signals average normally from the seeded starting point.
- Example: initial_score=0.8, then one +5 signal → `new_score = 0.8 + (5 - 0.8) / 1 = 5.0` (first signal dominates, as expected).
- Example: initial_score=0.8, then 10 signals of +3 → score converges toward 3.0, gradually overriding the seed.

## API Changes

### IngestionBundle

```python
@dataclass
class IngestionBundle:
    uris: List[str]
    events: List[IngestionEvent] = field(default_factory=list)
    contexts: Dict[str, IngestionContext] = field(default_factory=dict)
    reliability_hint: float | None = None
```

### DoctypeSpec

```python
@dataclass
class DoctypeSpec:
    name: str
    description: str
    schema: dict = field(default_factory=dict)
    plugin: str = ""
    decay_half_life_days: float | None = None
    default_reliability: float | None = None
```

### StorageAdapter.save_payload

```python
def save_payload(
    self, uri, metadata, vector, plugin, doctype,
    decay_half_life_days=None,
    content_hash=None,
    plugin_version="0.0.0",
    initial_score: float = 0.0,
) -> int:
```

### IngestionPipeline.ingest

```python
async def ingest(self, uris, reliability_hint=None) -> IngestionBundle | None:
```

### ingest_documents MCP tool

```
ingest_documents(uris: list[str], reliability_hint?: float)
```

### CLI

```
team-mind-mcp ingest [targets] --reliability 0.8
```

## Execution Plan

### Task 1: Bundle + DoctypeSpec fields
- Add `reliability_hint` to IngestionBundle.
- Add `default_reliability` to DoctypeSpec.
- *Stories:* STORY-001, STORY-002

### Task 2: save_payload initial_score
- Add `initial_score` parameter.
- Seed `usage_score` in doc_weights INSERT.
- *Stories:* STORY-003

### Task 3: Pipeline + MCP + CLI propagation
- Pipeline passes hint to bundle.
- MCP tool accepts hint.
- CLI accepts --reliability flag.
- *Stories:* STORY-004

### Task 4: MarkdownPlugin integration
- Read hint, resolve against default, pass to save_payload.
- *Stories:* STORY-005

### Task 5: Documentation
- Plugin developer guide, roadmap, system overview.
- *Stories:* STORY-006
