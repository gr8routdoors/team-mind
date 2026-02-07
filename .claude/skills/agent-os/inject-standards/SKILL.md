---
name: inject-standards
description: Inject relevant standards into the current context - suggests applicable standards or loads specified ones
triggers:
  - "inject standards"
  - "load standards"
  - "what standards"
  - "apply standards"
---

# Inject Standards

Inject relevant standards into the current context, formatted appropriately for the situation.

## Usage Modes

This skill supports two modes:

### Auto-Suggest Mode (no arguments)
```
/inject-standards
```
Analyzes context and suggests relevant standards.

### Explicit Mode (with arguments)
```
/inject-standards api                           # All standards in api/
/inject-standards api/response-format           # Single file
/inject-standards api/response-format api/auth  # Multiple files
```
Directly injects specified standards without suggestions.

## Process

### Step 1: Detect Context Scenario

Before injecting standards, determine which scenario we're in.

**Three scenarios:**

1. **Conversation** — Regular chat, implementing code, answering questions
2. **Creating a Skill** — Building a `.claude/skills/` file
3. **Shaping/Planning** — In plan mode, building a spec, running `/shape-spec`

**Detection logic:**

- If currently in plan mode OR conversation clearly mentions "spec", "plan", "shape" → **Shaping/Planning**
- If conversation clearly mentions creating a skill, editing `.claude/skills/` → **Creating a Skill**
- Otherwise → **Ask to confirm**

**If neither skill nor plan is clearly detected**, use AskUserQuestion:

```
I'll inject the relevant standards. How should I format them?

1. **Conversation** — Read standards into our chat (for implementation work)
2. **Skill** — Output file references to include in a skill you're building
3. **Plan** — Output file references to include in a plan/spec

Which scenario? (1, 2, or 3)
```

### Step 2: Read the Index (Auto-Suggest Mode)

Read `agent-os/standards/index.yml` to get the list of available standards and their descriptions.

If index.yml doesn't exist or is empty:
```
No standards index found. Run /discover-standards first to create standards,
or /index-standards if you have standards files without an index.
```

### Step 3: Analyze Work Context

Look at the current conversation to understand what the user is working on:
- What type of work? (API, database, UI, etc.)
- What technologies mentioned?
- What's the goal?

### Step 4: Match and Suggest

Match index descriptions against the context. Use AskUserQuestion to present suggestions:

```
Based on your task, these standards may be relevant:

1. **code-style/java** — Java conventions and formatting
2. **testing** — TDD principles and coverage
3. **bdd** — Acceptance criteria and BDD patterns

Inject these standards? (yes / just 1 and 3 / add: observability / none)
```

Keep suggestions focused — typically 2-5 standards.

### Step 5: Inject Based on Scenario

Format the output differently based on the detected scenario:

---

#### Scenario: Conversation

Read the standards and announce them:

```
I've read the following standards as they are relevant to what we're working on:

--- Standard: code-style/java ---

[full content of the standard file]

--- End Standard ---

**Key points:**
- [Summary of key rules]
```

---

#### Scenario: Creating a Skill

```
Include references to these standards in your skill:

@agent-os/standards/code-style/java.md
@agent-os/standards/testing.md
@agent-os/standards/bdd.md

These standards cover:
- Java conventions and formatting
- TDD principles and coverage
- AC format and BDD patterns
```

---

#### Scenario: Shaping/Planning

```
Include references to these standards in your spec:

@agent-os/standards/code-style/java.md
@agent-os/standards/testing.md
@agent-os/standards/bdd.md

These standards cover:
- Java conventions and formatting
- TDD principles and coverage
- AC format and BDD patterns
```

---

## Explicit Mode

When arguments are provided, skip the suggestion step but still detect scenario.

### Parse Arguments

Arguments can be:
- **Folder name** — `api` → inject all `.md` files in `agent-os/standards/api/`
- **Folder/file** — `code-style/java` → inject `agent-os/standards/code-style/java.md`
- **Root file** — `guardrails` → inject `agent-os/standards/guardrails.md`

Multiple arguments inject multiple standards.

### Validate

Check that specified files/folders exist. If not:

```
Standard not found: api/nonexistent

Available standards:
- guardrails
- code-style, code-style/java, code-style/go
- testing
- bdd
- ...

Did you mean one of these?
```

## Tips

- **Run early** — Inject standards at the start of a task, before implementation
- **Be specific** — If you know which standards apply, use explicit mode
- **Check the index** — If suggestions seem wrong, run `/index-standards` to rebuild

## Integration

This skill is called internally by `/shape-spec` to inject relevant standards during planning. You can also invoke it directly anytime you need standards in context.
