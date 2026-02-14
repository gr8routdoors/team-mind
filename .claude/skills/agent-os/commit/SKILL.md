---
name: commit
description: Use when ready to commit completed work to git
triggers:
  - "commit"
  - "stamp"
  - "save changes"
  - "git commit"
---

# Commit

Create context-aware conventional git commits with selective staging and atomic commit enforcement.

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to sloppy commits:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "I'll just commit everything at once" | Monolithic commits destroy history. Future developers can't bisect, can't revert, can't understand. | Follow the atomic commit process — one logical change per commit. |
| "The message doesn't matter, we squash anyway" | Not all teams squash. Even squashed PRs use the commit messages as context. And your branch history is your working memory between sessions. | Write a real conventional commit message every time. |
| "I know what changed, I don't need to check the diff" | You'll miss unintended changes, debug artifacts, and files you forgot to unstage. | Always review the diff before committing. |
| "This is too small to split into separate commits" | If the diff contains two unrelated changes, it's two commits regardless of size. | Check for logical separation even in small diffs. |
| "I'll add the spec reference later" | Later never comes. The commit loses its traceability the moment it's created. | Include spec/story references now or not at all. |

## ⛔ HARD GATE

**DO NOT commit without reviewing the full diff.** Every commit must be preceded by a `git diff --staged` review. No exceptions. If you haven't read the diff, you don't know what you're committing.

## Process

### Step 1: Assess the Working Tree

Run these commands to understand the current state:

```bash
git status
git diff --stat
```

Present a summary to the user:

```
## Changes Ready to Commit

**Staged:**
- (list staged files, or "none")

**Unstaged:**
- (list modified files with brief description)

**Untracked:**
- (list new files)
```

If there are no changes, inform the user and stop.

### Step 2: Detect Spec Context

Check if the current work is associated with a spec:

1. Check for an active session context in `agent-os/context/sessions/`
2. Look at `agent-os/specs/index.yml` for specs with status `in_progress`
3. If a spec is active, read its `stories.yml` to find the current story

**If spec context found:**
- Note the spec ID, story ID, and story name for the commit message
- The commit body will reference these

**If no spec context:**
- This is ad hoc work — infer type and scope from the changed files

### Step 3: Identify Logical Units

Review the changes and determine if they represent one or multiple logical units:

**Single logical unit indicators:**
- All changes relate to the same feature/fix/task
- Changes are in closely related files (e.g., a service and its tests)
- Removing one file would break the others

**Multiple logical unit indicators:**
- Unrelated files changed (e.g., a bug fix AND a README update)
- Changes serve different purposes (e.g., new feature AND dependency bump)
- Could be described with different commit types (e.g., `feat` AND `docs`)

If multiple logical units are detected, inform the user:

```
I see changes that span multiple logical units:

1. **feat(commit):** New /commit skill files
2. **docs:** Updated specs/index.yml with new specs

I recommend splitting these into separate commits. Shall I walk you through staging each one separately?
```

If the user agrees, process each unit as a separate pass through Steps 4-7.

### Step 4: Selective Staging

Present the files for the current logical unit and ask the user to confirm staging:

```
## Files to Stage

These files belong to this logical unit:
- path/to/file1.md (new)
- path/to/file2.yml (modified)

Shall I stage these files?
```

**Safety checks before staging:**
- Flag any `.env`, `.secret`, `credentials`, API key files, or `*.pem` files — **refuse to stage these**
- Flag any files not in `.gitignore` that probably should be (e.g., `node_modules/`, `.DS_Store`, `*.log`)
- Respect `.gitignore` — don't stage ignored files

Stage using specific file paths:
```bash
git add path/to/file1.md path/to/file2.yml
```

**Never use `git add -A` or `git add .`** — always stage specific files.

### Step 5: Review the Diff

**This is the hard gate.** Run:

```bash
git diff --staged
```

Read the full output. Look for:
- Debug artifacts (`console.log`, `print()`, `TODO`, `FIXME` left behind)
- Unintended changes (whitespace-only changes, unrelated modifications)
- Sensitive data (API keys, passwords, tokens in the diff)

If issues are found, inform the user and suggest unstaging or fixing before proceeding.

### Step 6: Build the Commit Message

Construct a conventional commit message following `git.md` standards.

**Format:**
```
<type>(<scope>): <description>

[body — what and why, not how]

[footer — spec/story reference if applicable]
```

**Type selection** (from git.md):
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation only
- `style` — Formatting (no code change)
- `refactor` — Code change that neither fixes a bug nor adds a feature
- `perf` — Performance improvement
- `test` — Adding or correcting tests
- `chore` — Maintenance tasks, dependency updates
- `ci` — CI/CD changes
- `build` — Build system or external dependency changes

**Scope:** Infer from the primary area affected. Use the component name, service name, or directory:
- Changes in `.claude/skills/agent-os/commit/` → scope: `commit`
- Changes in `agent-os/standards/` → scope: `standards`
- Changes across multiple areas → use the most significant area, or omit scope

**Subject line rules:**
- Imperative mood ("add feature" not "added feature")
- No period at the end
- Under 72 characters
- Lowercase first letter after the colon

**Body** (if the change warrants explanation):
- What changed and why
- Not how (the diff shows how)
- Blank line between subject and body

**Footer** (if spec context exists):
```
SPEC-002 / STORY-001
```

**Example — spec work:**
```
feat(commit): add context-aware git commit skill

Implements /commit skill with selective staging, atomic commit
enforcement, and conventional commit message generation.
Reads active spec/story context for traceability.

SPEC-002 / STORY-001
```

**Example — ad hoc work:**
```
docs: update specs index with SPEC-002 and SPEC-003

Registers the Developer Workflow and Framework Distribution
specs created during roadmap shaping session.
```

### Step 7: Present for Review

Show the user the complete commit before executing:

```
## Proposed Commit

**Message:**
```
feat(commit): add context-aware git commit skill

Implements /commit skill with selective staging, atomic commit
enforcement, and conventional commit message generation.

SPEC-002 / STORY-001
```

**Staged files:**
- .claude/skills/agent-os/commit/SKILL.md (new)

Shall I proceed with this commit?
```

Wait for explicit approval. Do not commit without it.

### Step 8: Execute the Commit

Once approved:

```bash
git commit -m "$(cat <<'EOF'
feat(commit): add context-aware git commit skill

Implements /commit skill with selective staging, atomic commit
enforcement, and conventional commit message generation.

SPEC-002 / STORY-001
EOF
)"
```

Always use the HEREDOC format to preserve multi-line messages.

After committing, show the result:
```bash
git log --oneline -1
```

### Step 9: Check for Remaining Units

If there were multiple logical units identified in Step 3, loop back to Step 4 for the next unit.

When all units are committed, show a final summary:

```
## Commits Created

1. `abc1234` feat(commit): add context-aware git commit skill
2. `def5678` docs: update specs index with SPEC-002 and SPEC-003

All changes committed. Working tree is clean.
```

## Tips

- **When in doubt, ask** — If you're unsure about staging, scope, or split points, ask the user
- **Spec references are free documentation** — Always include them when working on spec stories
- **Read the diff, every time** — This is non-negotiable. The diff is truth.
- **One commit per logical change** — If you need the word "and" in the subject line, it's probably two commits
- **The user has final say** — Present your suggestion, but the user can always adjust the message, staging, or split
