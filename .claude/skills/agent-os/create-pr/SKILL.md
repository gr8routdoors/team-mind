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
| "The commit message is good enough for the PR title" | Maybe for a single commit, but you still need to verify it's in conventional commit format. For multiple commits, you need to synthesize. | Read the commit message(s) and ensure the PR title follows conventional commits. |
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
- Analyze the commit types and scopes:
  - If all commits have the same type and scope, use that type/scope for the PR title
  - If commits have different types, identify the most common type
  - If commits have different scopes, identify the broadest applicable scope
- Synthesize a summary description that covers the changes across all commits
- Build PR title: `<type>(<scope>): <summary description>`

### Step 2: Build PR Description (AC-002)

**If exactly 1 commit:**
- Start with the commit body (everything after the first line)
- Verify it includes the required sections:
  - **Summary** or **What** — Brief description of the change
  - **Test plan** or **Testing** — How it was tested

**If multiple commits:**
- Synthesize a description from the commit messages
- Structure it with the required sections:
  - **Summary** — What changed across all commits
  - **Test plan** — How the changes were tested

**For both cases:**
- If the description is missing required sections, add them based on the code changes
- If testing info isn't clear, use: "Manual verification"
- Append the Claude Code footer:
  ```

  🤖 Generated with [Claude Code](https://claude.com/claude-code)
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

## Test plan
<testing text>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

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

## Notes

- This skill creates the PR but does NOT merge it — a human must approve and merge
- The skill uses the default base branch (typically `main`) — if you need a different base, use `gh pr create --base <branch>`
- If you need to add reviewers or labels, use `gh pr create` flags: `--reviewer`, `--label`
