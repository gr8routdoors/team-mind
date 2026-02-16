---
name: upgrade-lit
description: Use when the project needs to update its Lit SDLC framework files from upstream
triggers:
  - "upgrade lit"
  - "update framework"
  - "upgrade-lit"
  - "update lit sdlc"
  - "upgrade the framework"
---

# Upgrade Lit

Replace framework-owned files with the latest versions from the upstream Lit SDLC repository while preserving all project-owned content.

## Important

- The upstream Lit SDLC repo URL defaults to `https://github.com/gr8routdoors/lit-sdlc`
- The default branch is `main`
- Read `@agent-os/standards/directory-boundary.md` before proceeding — it defines which paths are framework-owned vs project-owned

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to botched upgrades:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "I can just manually copy the changed files" | You'll miss the boundary logic, the index.yml merge, and the custom file detection. You'll also leave stale files behind after upstream refactors. | Follow the full upgrade process. |
| "The framework probably hasn't changed much" | You don't know that until you fetch upstream and compare. Even small changes to standards or skills can have cascading effects. | Fetch upstream and let the process show what changed. |
| "I'll just update the files that look different" | Partial updates leave stale files that upstream deleted during refactors. The whole point of nuke-and-replace is eliminating drift. | Delete and replace entire framework directories, not individual files. |
| "I'll skip the dirty check, I know the state is fine" | Uncommitted changes make rollback impossible. If the upgrade breaks something, you can't cleanly revert. | Always verify a clean working directory first. |
| "The user already confirmed, I can skip the file scan" | Custom files in framework directories will be silently deleted. The user deserves to know what they'll lose. | Always scan for custom files and warn before deleting. |

## ⛔ HARD GATE

**DO NOT modify any files if the working directory has uncommitted changes.** Run `git status --porcelain` first. If the output is non-empty, inform the user and stop. The user must commit or stash their work before upgrading. No exceptions — this is what makes rollback safe.

## Process

### Step 1: Pre-flight — Clean Working Directory (AC-001)

Run:

```bash
git status --porcelain
```

**If output is non-empty:**

```
Your working directory has uncommitted changes. The upgrade cannot proceed
because uncommitted changes make rollback unsafe.

Please commit or stash your changes first, then run /upgrade-lit again.
```

Stop here. Do not continue.

**If output is empty:** Proceed to Step 2.

### Step 2: Configure Upstream Source (AC-005)

The default upstream configuration is:

- **Repo:** `https://github.com/gr8routdoors/lit-sdlc`
- **Branch:** `main`

Use AskUserQuestion to confirm:

```
I'll upgrade your Lit SDLC framework files from upstream.

- Upstream repo: https://github.com/gr8routdoors/lit-sdlc
- Branch: main

Proceed with these defaults, or do you want to override the repo URL or branch?
```

If the user provides overrides, use those values instead.

### Step 3: Fetch Upstream (AC-005)

Shallow clone the upstream repo to a temp directory:

```bash
git clone --depth 1 --single-branch --branch main https://github.com/gr8routdoors/lit-sdlc /tmp/lit-sdlc-upstream
```

Replace the URL and branch with any user-provided overrides.

**If the clone fails** (auth error, network issue, repo not found):

```
Failed to fetch upstream. Check that:
- The repo URL is correct
- You have access (the repo may be private)
- Your git credentials are configured (SSH key, credential helper, or gh auth)

Error: [show the git error message]
```

Stop here. Clean up any partial temp directory with `rm -rf /tmp/lit-sdlc-upstream`.

### Step 4: Scan for Custom Files (AC-002)

Compare local framework directories against the upstream clone to find files that exist locally but not in upstream. These files will be deleted during the nuke-and-replace.

Framework directories to scan:

- `.claude/skills/agent-os/`
- `agent-os/standards/` (root-level `.md` files and `code-style/` subdirectory only — skip `project/`)
- `AGENTS.md`

For each framework path, list local files and upstream files, then identify files that are only local.

**If custom files are found:**

```
These files exist in framework directories but are NOT in upstream:

- .claude/skills/agent-os/my-custom-skill/SKILL.md
- agent-os/standards/my-custom-standard.md

These files will be DELETED during the upgrade. Options:

1. Move them to project-owned locations before proceeding
   - Skills → .claude/skills/{project}/
   - Standards → agent-os/standards/project/
2. Proceed anyway (files will be deleted)
3. Abort the upgrade
```

Use AskUserQuestion to let the user choose. If they want to move files, help them do so before continuing. If they abort, clean up with `rm -rf /tmp/lit-sdlc-upstream` and stop.

**If no custom files found:** Proceed to Step 5.

### Step 5: Show Replacement Plan and Confirm (AC-001)

Present the upgrade plan to the user:

```
## Upgrade Plan

**Framework paths — will be REPLACED from upstream:**
- `.claude/skills/agent-os/` — deleted and replaced
- `agent-os/standards/*.md` — root-level files deleted and replaced
- `agent-os/standards/code-style/` — deleted and replaced
- `agent-os/standards/index.yml` — merged (your project_owned entries preserved)
- `AGENTS.md` — replaced

**Project paths — will NOT be touched:**
- `agent-os/standards/project/` — preserved
- `.claude/skills/{project}/` — preserved
- `agent-os/product/`, `agent-os/specs/`, `agent-os/context/` — preserved
- `CLAUDE.md`, `README.md` — preserved

> Python paths (tools/, pyproject.toml, uv.lock) are not managed by this
> version of /upgrade-lit.

Proceed with the upgrade?
```

Use AskUserQuestion. If the user declines, clean up with `rm -rf /tmp/lit-sdlc-upstream` and stop.

### Step 6: Execute Nuke-and-Replace (AC-003)

Execute the replacement in this order:

#### 6a: Preserve project-owned index entries

Read `agent-os/standards/index.yml` and extract all entries that have `project_owned: true`. Save them — you will re-inject them after replacing the index.

#### 6b: Delete framework-owned paths

```bash
# Framework skills
rm -rf .claude/skills/agent-os/

# Framework standards — root-level .md files only (NOT project/ subdirectory)
find agent-os/standards/ -maxdepth 1 -name '*.md' -delete

# Framework standards — code-style subdirectory
rm -rf agent-os/standards/code-style/

# Framework standards — index file (will be replaced and merged)
rm -f agent-os/standards/index.yml

# AGENTS.md
rm -f AGENTS.md
```

#### 6c: Copy upstream framework files

```bash
# Framework skills
cp -r /tmp/lit-sdlc-upstream/.claude/skills/agent-os/ .claude/skills/agent-os/

# Framework standards — root-level .md files
find /tmp/lit-sdlc-upstream/agent-os/standards/ -maxdepth 1 -name '*.md' -exec cp {} agent-os/standards/ \;

# Framework standards — code-style subdirectory
cp -r /tmp/lit-sdlc-upstream/agent-os/standards/code-style/ agent-os/standards/code-style/

# Framework standards — index file
cp /tmp/lit-sdlc-upstream/agent-os/standards/index.yml agent-os/standards/index.yml

# AGENTS.md
cp /tmp/lit-sdlc-upstream/AGENTS.md AGENTS.md
```

#### 6d: Merge index.yml

Read the upstream `index.yml` that was just copied into place. Append the project-owned entries that were extracted in Step 6a. Make sure the `project_owned: true` flag is preserved on each re-injected entry.

The merged file should have:
- All framework entries from upstream (replacing whatever was there before)
- All project-owned entries from the local version (preserved exactly as they were)

#### 6e: Clean up temp directory

```bash
rm -rf /tmp/lit-sdlc-upstream
```

### Step 7: Post-upgrade Report (AC-004)

Show the user what changed:

```bash
git diff --stat
```

Present a summary:

```
## Upgrade Complete

**Changes:**
[output of git diff --stat]

**Next steps:**
- Review the changes: `git diff`
- If everything looks good, commit: `git add -A && git commit -m "chore: upgrade lit-sdlc framework"`
- To roll back: `git checkout -- .` (discards all changes since the working directory was clean)
```

## Tips

- **Always read the diff after upgrading** — New standards, changed skills, or updated guardrails may affect your workflow
- **Project content is always safe** — The upgrade never touches `agent-os/standards/project/`, `agent-os/product/`, `agent-os/specs/`, or `agent-os/context/`
- **Rollback is one command** — Since the upgrade requires a clean working directory, `git checkout -- .` reverts everything
- **Run `/inject-standards` after upgrading** — New or updated standards may be available
- **Check for new skills** — Upstream may have added skills; run `/bootstrap` to see what's new
