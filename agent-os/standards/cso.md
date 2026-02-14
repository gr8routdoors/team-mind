# Claude Search Optimization (CSO)

> Rules for writing skill descriptions that ensure Claude reads the full SKILL.md instead of following a summary.

---

## The Description Trap

When a skill's `description` field in YAML frontmatter summarizes the workflow, Claude follows the summary instead of reading the full SKILL.md. This causes entire processes to be skipped.

**Example of the problem:**

Bad description (summarizes workflow):
```yaml
description: Create specs by gathering requirements, defining stories, deriving ACs, and building test scaffolding
```
Claude reads this and thinks it knows the full process. It skips reading SKILL.md and follows the summary — missing hard gates, rationalization tables, and detailed steps.

Good description (states triggering conditions only):
```yaml
description: Use when starting significant new work that needs requirements, design, and stories
```
Claude reads this and knows WHEN to trigger the skill, but must read SKILL.md to learn HOW.

## The Rule

**Skill descriptions MUST only state triggering conditions. They MUST NOT summarize the workflow, process, or steps.**

## Checklist

When writing or reviewing skill descriptions:

- [ ] Description answers "WHEN should this skill be used?" — not "WHAT does this skill do?"
- [ ] No verbs describing process steps (avoid: "creates", "generates", "derives", "builds", "transforms")
- [ ] No sequence words (avoid: "first", "then", "after", "before")
- [ ] No output descriptions (avoid: "produces", "outputs", "saves", "creates files")
- [ ] Length under 120 characters

## Examples

| Status | Description | Why |
|--------|-------------|-----|
| ✅ Good | "Use when starting significant new work that needs requirements and design" | States trigger |
| ✅ Good | "Use when about to claim work is complete or passing" | States trigger |
| ✅ Good | "Session startup ritual before any work begins" | States trigger |
| ❌ Bad | "Create specs by gathering requirements, defining stories, and deriving ACs" | Summarizes workflow |
| ❌ Bad | "Generate acceptance criteria from requirements and architectural design" | Describes what it does |
| ❌ Bad | "Transform acceptance criteria into executable BDD test scaffolding" | Describes transformation |

---

_Source: Discovered by Superpowers framework v4.0.0. When descriptions summarized two-stage code review, Claude followed the description instead of the full skill, breaking the review process._
