# Observability Standards

> Logging, metrics, and tracing conventions.

---

## Philosophy

Good observability enables:
- **Debugging** — Trace issues through the system
- **Monitoring** — Know when things go wrong
- **Understanding** — See how the system behaves in production

**Goal:** Well-thought-out logging that traces flows without being spammy.

---

## Logging

### Platform
- **Splunk** — Primary log aggregation
- **Format** — Structured JSON for machine parsing
- **Standards** — Organizational logging standards

### Log Levels

| Level | When to Use | Example |
|-------|-------------|---------|
| `ERROR` | Something failed that shouldn't have | Exception caught, operation failed |
| `WARN` | Something unexpected but handled | Retry succeeded, fallback used |
| `INFO` | Significant business events | Request received, action complete |
| `DEBUG` | Detailed diagnostic information | Intermediate values, decision points |
| `TRACE` | Very detailed debugging | Loop iterations, raw data |

**Production defaults:** INFO and above. DEBUG/TRACE enabled selectively for troubleshooting.

### What to Log

**Always log:**
- Request entry and exit (with duration)
- Business-critical decisions
- External service calls (with duration and status)
- Errors and exceptions (with context)
- Security-relevant events (auth, access)

**Never log:**
- Sensitive data (PII, credentials, tokens)
- High-frequency operations in hot loops
- Redundant information already in context

### Structured Fields

Use consistent field names for correlation and filtering:

| Field | Purpose | Example |
|-------|---------|---------|
| `requestId` | Trace across services | `"req-abc123"` |
| `productId` | Business entity | `"PROD-456"` |
| `operation` | What's happening | `"someAction"` |
| `duration` | Timing in ms | `125` |
| `status` | Result | `"success"`, `"failure"` |

### Java Example (Slf4j + Structured Logging)

```java
@Slf4j
public class SomeClass {

    public ValueEntity action(SomeRequest request) {
        log.info("Starting action",
            kv("requestId", request.getId()),
            kv("entityId", request.getEntityId()));

        var stopwatch = Stopwatch.createStarted();
        try {
            var value = doAction(request);

            log.info("Action complete",
                kv("requestId", request.getId()),
                kv("entityId", request.getEntityId()),
                kv("duration", stopwatch.elapsed(MILLISECONDS)),
                kv("status", "success"));

            return value;
        } catch (Exception e) {
            log.error("Action failed",
                kv("requestId", request.getId()),
                kv("entityId", request.getEntityId()),
                kv("duration", stopwatch.elapsed(MILLISECONDS)),
                kv("status", "failure"),
                kv("error", e.getMessage()),
                e);
            throw e;
        }
    }
}
```

### Go Example

```go
func (c *ValueEntity) SomeAction(ctx context.Context, req *Request) (*ValueEntity, error) {
    logger := log.With(
        "requestId", req.ID,
        "entityId", req.EntityId,
    )

    logger.Info("starting action")
    start := time.Now()

    entity, err := c.doAction(ctx, req)
    duration := time.Since(start)

    if err != nil {
        logger.Error("some action failed",
            "duration", duration.Milliseconds(),
            "status", "failure",
            "error", err)
        return nil, err
    }

    logger.Info("some action complete",
        "duration", duration.Milliseconds(),
        "status", "success")

    return entity, nil
}
```

---

## Tracing Flow

For complex calculations, log decision points to trace the flow:

```java
log.debug("Taking action",
    kv("entity", entity.getType()),
    kv("entityValue", entity.getValue()),
    kv("valueBeforeAction", value));

log.debug("Action applied",
    kv("valueAfterAction", newValue));
```

**Keep it sparse** — Only log what helps understand the flow. Don't log every variable.

---

## Correlation IDs

- Pass `requestId` through all service calls
- Use MDC (Java) or context (Go) to automatically include in logs
- Include in error responses for support debugging

---

## Metrics (Future)

_To be defined._

Candidates:
- Request count by endpoint
- Request latency (p50, p95, p99)
- Error rate by type
- Cache hit/miss rates
- Database query times

---

## Alerting (Future)

_To be defined._

Candidates:
- Error rate threshold exceeded
- Latency degradation
- Service health check failures

---

_Last updated: 2026-02-03_
