# Git Worktrees

> Branch isolation pattern for safe development work.

---

## When to Use

Use git worktrees when:
- Starting implementation of a spec (feature work)
- Making changes that shouldn't affect the main branch
- Working on multiple specs simultaneously
- Any work that involves more than trivial changes

## Setup Checklist

1. **Check for existing worktree directory configuration**
   - Look for `.worktrees/` or `worktrees/` directory
   - Check CLAUDE.md or project config for worktree location

2. **Create the worktree**
   ```bash
   git worktree add <path> -b <branch-name>
   ```
   Branch naming: Follow `git.md` conventions (`feat/SPEC-001-feature-name`)

3. **Verify .gitignore**
   - Ensure the worktree directory is in `.gitignore`
   - This prevents accidentally committing worktree contents

4. **Run setup in the worktree**
   - Install dependencies (`npm install`, `go mod download`, etc.)
   - Build the project
   - Verify the build succeeds

5. **Run baseline tests**
   - Run the full test suite in the worktree
   - All tests must pass before starting work
   - If tests fail, fix them first — don't start with a broken baseline

## Working in Worktrees

- Treat each worktree as an isolated workspace
- Commit frequently within the worktree's branch
- Don't modify the main branch from a worktree

## Finishing Work

When the spec/feature is complete:
1. Verify all tests pass
2. Choose one: merge locally, create PR, keep branch, or discard
3. Clean up the worktree:
   ```bash
   git worktree remove <path>
   ```
4. Delete the branch if merged:
   ```bash
   git branch -d <branch-name>
   ```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Worktree directory not in .gitignore | Add it before creating worktree |
| Skipping baseline test run | Always verify tests pass in clean worktree |
| Forgetting to install dependencies | Run full setup after creating worktree |
| Working in wrong worktree | Check `git worktree list` to see all worktrees |
| Not cleaning up after merge | Remove worktree and delete merged branch |

---

_Adapted from Superpowers framework's using-git-worktrees skill._
