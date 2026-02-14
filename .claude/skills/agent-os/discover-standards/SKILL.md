---
name: discover-standards
description: Use when codebase has undocumented patterns worth standardizing
triggers:
  - "discover standards"
  - "extract standards"
  - "document patterns"
  - "create standards"
---

# Discover Standards

Extract tribal knowledge from your codebase into concise, documented standards.

## Important Guidelines

- **Always use AskUserQuestion tool** when asking the user anything
- **Write concise standards** — Use minimal words. Standards must be scannable by AI agents without bloating context windows.
- **Offer suggestions** — Present options the user can confirm, choose between, or correct.

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to skipping standards discovery:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "The code speaks for itself" | Code is action, not documentation. Tribal knowledge lives in heads, not files. Future developers won't know why patterns exist. | Discover and document the "why" behind patterns. |
| "We don't have any standards" | You do. They're just undocumented. Every codebase has patterns. Documenting them prevents inconsistency. | Discover existing patterns and make them explicit. |
| "We can document standards later" | You won't. The knowledge lives in the original author's head. Once they leave, it's lost. | Discover and document now, before context is lost. |
| "Standards limit flexibility" | No. Standards enable flexibility by setting boundaries. Within boundaries, agents move fast. | Discover constraints to clarify where agents have freedom. |
| "I don't have time to discover standards" | You don't have time NOT to. Without documented standards, every agent rewrites the rules. | Invest 2 hours discovering standards to save weeks of inconsistency. |

## Process

### Step 1: Determine Focus Area

Check if the user specified an area when running this skill. If they did, skip to Step 2.

If no area was specified:

1. Analyze the codebase structure (folders, file types, patterns)
2. Identify 3-5 major areas
3. Use AskUserQuestion to present the areas:

```
I've identified these areas in your codebase:

1. **API Routes** (src/api/) — Request handling, response formats
2. **Database** (src/models/, src/db/) — Models, queries, migrations
3. **Services** (src/services/) — Business logic patterns
4. **Testing** (src/test/) — Test patterns and conventions

Which area should we focus on for discovering standards? (Pick one, or suggest a different area)
```

Wait for user response before proceeding.

### Step 2: Analyze & Present Findings

Once an area is determined:

1. Read key files in that area (5-10 representative files)
2. Look for patterns that are:
   - **Unusual or unconventional** — Not standard framework/library patterns
   - **Opinionated** — Specific choices that could have gone differently
   - **Tribal** — Things a new developer wouldn't know without being told
   - **Consistent** — Patterns repeated across multiple files

3. Use AskUserQuestion to present findings:

```
I analyzed [area] and found these potential standards worth documenting:

1. **API Response Envelope** — All responses use { success, data, error } structure
2. **Error Codes** — Custom error codes like AUTH_001, DB_002 with specific meanings
3. **Pagination Pattern** — Cursor-based pagination with consistent param names

Which would you like to document?

Options:
- "Yes, all of them"
- "Just 1 and 3"
- "Add: [your suggestion]"
- "Skip this area"
```

### Step 3: Ask Why, Then Draft Each Standard

**IMPORTANT:** For each selected standard, complete this full loop before moving to the next:

1. **Ask 1-2 clarifying questions** about the "why" behind the pattern
2. **Wait for user response**
3. **Draft the standard** incorporating their answer
4. **Confirm with user** before creating the file
5. **Create the file** if approved

Example questions:
- "What problem does this pattern solve? Why not use the default approach?"
- "Are there exceptions where this pattern shouldn't be used?"
- "What's the most common mistake with this?"

### Step 4: Create the Standard File

For each standard (after completing Step 3's Q&A):

1. Determine the appropriate folder (create if needed)
2. Check if a related standard file already exists — append to it if so
3. Draft the content and use AskUserQuestion to confirm:

```
Here's the draft for api/response-format.md:

---
# API Response Format

All API responses use this envelope:

```json
{ "success": true, "data": { ... } }
{ "success": false, "error": { "code": "...", "message": "..." } }
```

- Never return raw data without the envelope
- Error responses must include both code and message
- Success responses omit the error field entirely
---

Create this file? (yes / edit: [your changes] / skip)
```

4. Create or update the file in `agent-os/standards/`

### Step 5: Update the Index

After all standards are created:

1. Scan `agent-os/standards/` for all `.md` files
2. For each new file, use AskUserQuestion:

```
New standard needs an index entry:
  File: api/response-format.md

Suggested description: "API response envelope structure and error format"

Accept this description? (yes / or type a better one)
```

3. Update `agent-os/standards/index.yml`

### Step 6: Offer to Continue

Use AskUserQuestion:

```
Standards created for [area]:
- api/response-format.md
- api/error-codes.md

Would you like to discover standards in another area, or are we done?
```

## Writing Concise Standards

Standards will be injected into AI context windows. Every word costs tokens. Follow these rules:

- **Lead with the rule** — State what to do first, explain why second
- **Use code examples** — Show, don't tell
- **Skip the obvious** — Don't document what the code already makes clear
- **One standard per concept** — Don't combine unrelated patterns
- **Bullet points over paragraphs** — Scannable beats readable

**Good:**
```markdown
# Error Responses

Use error codes: `AUTH_001`, `DB_001`, `VAL_001`

```json
{ "success": false, "error": { "code": "AUTH_001", "message": "..." } }
```

- Always include both code and message
- Log full error server-side, return safe message to client
```

**Bad:**
```markdown
# Error Handling Guidelines

When an error occurs in our application, we have established a consistent pattern for how errors should be formatted and returned to the client...
[continues for 3 more paragraphs]
```

## Output Location

All standards: `agent-os/standards/[folder]/[standard].md`
Index file: `agent-os/standards/index.yml`
