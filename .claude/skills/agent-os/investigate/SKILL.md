---
name: investigate
description: Investigate bugs, performance issues, or understand existing behavior - document findings for future sessions
triggers:
  - "investigate"
  - "debug"
  - "why is this"
  - "understand how"
  - "figure out"
  - "troubleshoot"
---

# Investigate

Investigate bugs, performance issues, or understand existing behavior. Document findings for future sessions.

## Process

### Step 1: Clarify the Investigation

Use AskUserQuestion to understand scope:

```
What are we investigating?

- Bug or unexpected behavior
- Performance issue
- Understanding how something works
- Security concern
- Other: ___

Please describe what you're seeing or what you want to understand.
```

### Step 2: Check Existing Knowledge

Before diving in, check if we already know something:

**Component details:**
```
agent-os/context/component-details/{component}/
├── current-behavior.md
├── gotchas.md
├── performance.md
└── data-fetching.md
```

**Previous sessions:**
```
agent-os/context/sessions/
```

**Guardrails (known anti-patterns):**
```
agent-os/standards/guardrails.md
```

Summarize any relevant existing knowledge before investigating further.

### Step 3: Form Hypotheses

Based on the problem description and existing knowledge, form 1-3 hypotheses:

```
Based on what you've described and what I know about this component:

**Hypothesis 1:** {Most likely cause}
- Evidence for: ...
- How to verify: ...

**Hypothesis 2:** {Alternative cause}
- Evidence for: ...
- How to verify: ...

Which should we investigate first?
```

### Step 4: Investigate

Gather evidence:
- Read relevant code
- Check logs or error messages (if provided)
- Trace data flow
- Run queries (if applicable)
- Test hypotheses

Document as you go — don't rely on memory.

### Step 5: Document Findings

Create or update documentation based on what you learned:

**New behavior discovered → Update component details:**
```markdown
# In context/component-details/{component}/current-behavior.md

## {New Section}
Discovered: {date}

{What you learned about how it works}
```

**New gotcha discovered → Update gotchas:**
```markdown
# In context/component-details/{component}/gotchas.md

### {Gotcha Title}
**Severity:** High
**Discovered:** {date}

{Description of the gotcha}

**How to avoid:** {Guidance}
```

**Anti-pattern discovered → Update guardrails:**
```markdown
# In standards/guardrails.md

### GR-{X}{NN}: {Title}
**Don't:** {What not to do}
**Instead:** {What to do instead}
```

### Step 6: Summarize Investigation

Present findings:

```
## Investigation Summary: {Topic}

### Finding
{What we discovered — the root cause or explanation}

### Evidence
{Key evidence that supports the finding}

### Impact
{What this means for the codebase/feature/user}

### Recommendations
1. {Immediate action if needed}
2. {Longer-term improvement if applicable}

### Documentation Updated
- ✅ `component-details/{component}/gotchas.md` — Added {gotcha}
- ✅ `standards/guardrails.md` — Added GR-{X}{NN}
```

## Investigation Patterns

### Performance Issues
1. Identify the slow operation
2. Check for N+1 queries or exponential fetching
3. Look at data access patterns in component-details
4. Profile if possible
5. Document in `performance.md`

### Unexpected Behavior
1. Clarify expected vs actual behavior
2. Check if it's a known gotcha
3. Trace the code path
4. Identify where behavior diverges
5. Document in `current-behavior.md` or `gotchas.md`

### Data Issues
1. Understand the data model
2. Check for constraint violations
3. Look for edge cases in business rules
4. Document in `data-fetching.md` or `gotchas.md`

## Tips

- **Investigate, don't fix** — This skill is for understanding, not implementing changes
- **Document everything** — Future sessions will thank you
- **Update guardrails** — If you find an anti-pattern, add it so we don't repeat it
- **Be specific** — Vague findings aren't useful; include code paths, query patterns, etc.
