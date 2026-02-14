# Domain Terminology

> Vocabulary used throughout the Lit SDLC framework. When these terms appear in skills, standards, or specs, they carry the specific meanings defined here.

---

## Core Concepts

| Term | Definition |
|------|-----------|
| **Agent OS** | The underlying framework architecture providing standards, skills, specs, and context layers. Based on [agent-os v3](https://github.com/buildermethods/agent-os). |
| **Standard** | A declarative convention document in `agent-os/standards/`. Describes rules and patterns the agent must follow. Indexed by tags for selective injection. |
| **Skill** | A procedural workflow document in `.claude/skills/agent-os/`. Contains step-by-step instructions the agent follows. Triggered via `/skill-name` commands. |
| **Spec** | A feature specification in `agent-os/specs/SPEC-{NNN}-{slug}/`. Contains requirements, design, stories, and acceptance criteria. |
| **Story** | A discrete, independently deliverable unit of work within a spec. Tracked in stories.yml with status `failing` or `passing`. |
| **Acceptance Criteria (AC)** | Testable behavior definition in Given/When/Then format. Each story has one or more ACs in `acs/STORY-{NNN}-{slug}.md`. |

## Standards System

| Term | Definition |
|------|-----------|
| **Tag** | A label in index.yml enabling filtered injection. Examples: `coding`, `testing`, `reviewing`, `java`, `go`, `all`. |
| **Injection** | Loading relevant standards into the agent's context via `/inject-standards`. |
| **Guardrail** | An anti-pattern entry in `guardrails.md` prefixed with GR-{category}{number}. |
| **CSO** | Claude Search Optimization. Rules ensuring skill descriptions state only triggering conditions, not workflow summaries. |

## Workflow Concepts

| Term | Definition |
|------|-----------|
| **Session** | A single working conversation between developer and AI agent. Bounded by `/start-session` and `/end-session`. |
| **Session Summary** | A structured document in `context/sessions/` preserving decisions, learnings, and failures. |
| **Hard Gate** | An explicit blocking point in a skill preventing the agent from progressing until a condition is met. |
| **Anti-rationalization Table** | A table listing common excuses the agent makes to skip a skill, with counter-arguments. |
| **Verification** | Running a command, reading output, citing evidence before claiming completion. |

## Multi-Agent Concepts

| Term | Definition |
|------|-----------|
| **Subagent** | A fresh agent instance dispatched via the Task tool for a specific piece of work. |
| **Two-Stage Review** | Code review in two phases: spec compliance (did you build what was asked?) then code quality (is it well-built?). |
| **Implementer** | A subagent dispatched to implement a story. |
| **Spec Reviewer** | A subagent verifying implementation matches acceptance criteria. |
| **Code Quality Reviewer** | A subagent verifying code cleanliness. Only runs after spec compliance passes. |

## Operating Modes

| Term | Definition |
|------|-----------|
| **Interactive Mode** | Developer present. Agent asks questions and iterates. |
| **Unattended Mode** | Agent works autonomously. Must follow guardrails GR-U01 through GR-U06. |

## Operating Profiles (Future)

| Term | Definition |
|------|-----------|
| **Operating Profile** | A configuration setting in AGENTS.md (`operating_profile: full\|team\|lean`) that tunes skill behavior to match a team's workflow. Not yet implemented — see `SPEC-002/future-profiles.md` for the vision. |
| **Full Profile** | (Future) Subagent per story, two-stage agent review, full verification. Target: solo dev or AI-heavy teams. |
| **Team Profile** | (Future) Single agent, skip agent review (humans review PRs), full verification. Target: teams with human PR review. |
| **Lean Profile** | (Future) Single agent, no agent review, lighter verification. Target: experienced teams with strong CI. |
