---
name: create-pr
description: Use when you need to create a pull request with a conventional commit title and proper description
triggers:
  - "create pr"
  - "make pr"
  - "create pull request"
  - "make pull request"
  - "open pr"
  - "ship pr"
  - "ship it"
---

# Create Pull Request

Create a well-formatted pull request with a conventional commit title and structured description that follows `git.md` standards.

## Important

- PR titles MUST use conventional commit format: `<type>(<scope>): <description>`
- PR descriptions MUST include Summary and Test plan sections
- Read `@agent-os/standards/git.md` before proceeding — it defines the PR format requirements

## The Agent Will Rationalize

Before following this process, be aware of these rationalizations that lead to poorly formatted PRs:

| Rationalization | Why It's Wrong | What To Do Instead |
|----------------|----------------|-------------------|
| "The commit message is good enough for the PR title" | Maybe for a single commit, but you still need to verify it's in conventional commit format. For multiple commits, you must use the **most significant type** based on the ranking (feat > fix > refactor > perf > docs > style > test > chore). | Read all commit messages, rank them by significance, and use the most significant type for the PR title. |
| "The user can edit the PR after creation" | Get it right the first time. The user asked you to create a PR — deliver a complete, properly formatted one. | Draft the title and description, present for review, create only after approval. |
| "Just use the branch name as the title" | Branch names are not commit messages. They don't follow conventional commit format and often lack the detail needed for a PR title. | Read the commits and synthesize a proper conventional commit title. |
| "The PR description can just be the commit message body" | For a single commit, yes. For multiple commits, you need to synthesize. Either way, verify it has the required sections. | Ensure the description includes Summary and Test plan sections per git.md. |
| "I don't need to present it for review, just create it" | The user deserves to see what you're about to publish. They might want to adjust the wording. | Always present the title and description before calling gh pr create. |

## Process

### Step 1: Analyze Commits (AC-001)

Determine how many commits exist on the current branch compared to the base branch (typically `main`):

```bash
git log --oneline origin/main..HEAD
```

Count the commits in the output.

**If exactly 1 commit:**
- Read the full commit message: `git log -1 --format=%B HEAD`
- Extract the first line (subject) as the PR title candidate
- Extract everything after the first line (body) as the PR description candidate
- Verify the title is in conventional commit format: `<type>(<scope>): <description>`
  - If not, ask the user to provide a conventional commit title

**If multiple commits:**
- Read all commit messages: `git log --format=%B origin/main..HEAD`
- Analyze the commit types and scopes using **commit type significance ranking**:
  - Rank types by significance: `feat` > `fix` > `refactor` > `perf` > `docs` > `style` > `test` > `chore`
  - Breaking changes (types with `!` suffix) always win regardless of base type
  - Use the **most significant type** for the PR title (not the most common or first)
  - If commits have different scopes, use the scope from the most significant commit
- Synthesize a summary description that covers the primary change
- Build PR title: `<most-significant-type>(<scope>): <summary description>`
- **Example**: If commits are `docs(roadmap): update` and `feat(create-pr): add trigger`, use `feat` because feat > docs

### Step 2: Build PR Description (AC-002)

**If exactly 1 commit:**
- Start with the commit body (everything after the first line)
- Verify it includes the required sections:
  - **Summary** or **What** — Brief description of the change
  - **Test plan** or **Testing** — How it was tested

**If multiple commits:**
- Synthesize a description from the commit messages
- Structure it with the required sections:
  - **Summary** — What changed across all commits (focus on the most significant change)
  - **Changes** — List all commits with their types for full transparency
  - **Test plan** — How the changes were tested

**For both cases:**
- If the description is missing required sections, add them based on the code changes
- If testing info isn't clear, use: "Manual verification"
- Append the AI footer with the resolved tool name (see [Resolving AI Tool Name](#resolving-ai-tool-name)):
  ```

  🤖 Generated with [Lit SDLC](https://github.com/gr8routdoors/lit-sdlc) via <resolved tool name>
  ```

### Step 3: Present for Review (AC-001, AC-002)

Present the proposed PR to the user:

```
I'll create a pull request with:

**Title:**
<type>(<scope>): <description>

**Description:**
## Summary
<summary text>

## Changes
- <type>(<scope>)[!]: <commit 1 description>
- <type>(<scope>): <commit 2 description>

(Note: Only include for multi-commit PRs. The `!` suffix indicates breaking changes.)

## Test plan
<testing text>

🤖 Generated with [Lit SDLC](https://github.com/gr8routdoors/lit-sdlc) via <resolved tool name>

Does this look good, or would you like me to adjust anything?
```

Wait for user confirmation. If they request changes, update the title or description and present again.

### Step 4: Create the PR (AC-003)

Once the user approves, create the PR using `gh`:

```bash
gh pr create --title "<title>" --body "<description>"
```

**If the command succeeds:**
- Extract the PR URL from the output
- Report to the user: "Created PR: <URL>"

**If the command fails:**
- Check if `gh` is installed: `which gh`
  - If not found: "The GitHub CLI (gh) is not installed. Install it with: brew install gh (macOS) or follow instructions at https://cli.github.com/"
- Check if `gh` is authenticated: `gh auth status`
  - If not authenticated: "GitHub CLI is not authenticated. Run: gh auth login"
- If other error: Show the error message and suggest the user check their repository setup

---

## Resolving AI Tool Name

The footer must include the name of the AI tool that generated the PR. Detect the environment and substitute accordingly:

| Signal | Tool Name |
|--------|-----------|
| Running inside Cursor IDE (system prompt mentions "Cursor", workspace uses `.cursor/` directories) | **Cursor** |
| Running inside Claude Code CLI (`claude` command, CLAUDE_CODE env) | **Claude Code** |
| Cannot determine | **AI Assistant** (generic fallback) |

The agent MUST resolve this before presenting the PR for review — never show a raw placeholder to the user.

---

## Notes

- This skill creates the PR but does NOT merge it — a human must approve and merge
- The skill uses the default base branch (typically `main`) — if you need a different base, use `gh pr create --base <branch>`
- If you need to add reviewers or labels, use `gh pr create` flags: `--reviewer`, `--label`
