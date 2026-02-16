# Product Roadmap

## Current Focus

**Phase 3: Distribution** — Making Lit SDLC easy to install and adopt in new projects.

## Phase 1: Foundation (Complete)

- [x] Agent OS v3 integration (standards, skills, specs, context layers)
- [x] Core skills: shape-spec, derive-acs, generate-bdd-tests, continue-spec
- [x] Session management: start-session, end-session
- [x] Standards system: indexed, tagged, selectively injectable
- [x] Guardrails: anti-patterns and unattended mode rules
- [x] BDD workflow: Go (spec + testify) and Java (Spock)
- [x] Investigation skill with component-details documentation

## Phase 2: Discipline Enforcement (Complete)

- [x] Anti-rationalization tables in all skills (SPEC-001)
- [x] Hard gates in workflow skills (SPEC-001)
- [x] Verify-completion skill (SPEC-001)
- [x] Dispatch-subagents skill with two-stage review (SPEC-001)
- [x] Code review skills: request + receive (SPEC-001)
- [x] CSO standard — Claude Search Optimization (SPEC-001)
- [x] Git worktrees standard (SPEC-001)

## Phase 3: Distribution (In Progress)

**Completed:** SPEC-003 (AGENTS.md redesign, directory boundary, `/upgrade-lit` skill, minimal `/create-pr` skill)

**Up next:** `/commit` skill, Python tooling foundation, operating profiles, enhanced `/create-pr`, adoption workflows

### 3.1 — `/commit` skill

No skill currently exists for creating structured git commits. Agents either run `git commit` ad hoc with inconsistent messages, or don't commit at all. `/commit` is a standalone skill that stages changes, assembles a conventional commit message from the current work context, and stamps the commit. Usable any time — for personal repos this is the end of the line; for team repos it feeds into `/ship-pr`.

- [ ] **Context-aware commit message** — Build the commit message from Lit SDLC context: the active spec and story (if any), a summary of what changed and why, and conventional commit format per `git.md` standards. For work outside a spec (e.g., framework improvements, ad hoc fixes), infer the type and scope from the changed files. Present the message for human review before committing, or auto-commit in `full`/`autonomous` profiles.
- [ ] **Selective staging** — Review unstaged and staged changes, present a summary of what will be committed, and let the user confirm or adjust. Respect `.gitignore`. Flag any potentially sensitive files (`.env`, credentials) and refuse to stage them.
- [ ] **Atomic commits** — Enforce the `git.md` standard: each commit should be a single logical change that compiles and passes tests. If the working tree contains changes spanning multiple logical units, suggest splitting into multiple commits and walk the user through it.
- [ ] **Commit-PR message alignment** — The commit message format is designed to feed directly into `/ship-pr`. When `/ship-pr` creates a PR, it can pull from the commit messages to build the PR description, so they're naturally aligned. This avoids writing the same context twice.

### 3.2 — Python tooling foundation

Lit SDLC ships with a `pyproject.toml` at root and uses [UV](https://github.com/astral-sh/uv) for dependency management. Python tools live in a `tools/` directory and work out of the box — no separate install step. This gives the framework executable tooling alongside the declarative markdown/YAML content, enabling deterministic scripts that are testable with pytest.

- [ ] **`pyproject.toml` + UV setup** — Add `pyproject.toml` to the repo root with UV as the package manager. Define the `tools/` directory as a Python package. Include core dependencies (PyYAML, python-frontmatter, Click) and dev dependencies (pytest, ruff). Document the convention in a standard so agents know to use UV.
- [ ] **Standards index validator** (`tools/validate_standards.py`) — Parse `standards/index.yml`, verify all referenced files exist, validate tag syntax, check for orphaned standard files not in the index. First concrete tool demonstrating the pattern.
- [ ] **Install validation script** (`tools/validate_install.py`) — Verify directory structure, check all skill files present, validate AGENTS.md has required sections. Used by `/clean-install` skill under the hood.
- [ ] **Session frontmatter parser** (`tools/parse_session.py`) — Parse enhanced session summaries with YAML frontmatter (session_id, tokens_used, cost_usd, status, stories_completed/remaining). Foundation for autonomous execution and session analytics.

### 3.3 — Upgrade and contribution workflow ✅ COMPLETE (SPEC-003)

**Delivered:** Framework directory boundary convention, `/upgrade-lit` skill for nuke-and-replace upgrades, minimal AGENTS.md as generic boot loader, minimal `/create-pr` skill.

- [x] **Framework vs. project boundary** — Delivered as directory convention in SPEC-003 STORY-002. Framework files live in `.claude/skills/agent-os/`, `agent-os/standards/*.md`, `agent-os/standards/code-style/`, and `AGENTS.md`. Project files live in `.claude/skills/{project}/`, `agent-os/standards/project/`, `agent-os/product/`, `agent-os/specs/`, `agent-os/context/`. Documented in `agent-os/standards/directory-boundary.md`.
- [x] **`/upgrade-lit` skill** — Delivered in SPEC-003 STORY-003. Nuke-and-replace framework directories from upstream via shallow clone. Aborts if uncommitted changes exist. Warns about custom files in framework directories. Merges `index.yml` to preserve project-owned standards.
- [x] **Minimal `/create-pr` skill** — Delivered in SPEC-003 STORY-004. Enforces conventional commit format for PR titles. Handles single commit (use commit message) and multiple commits (synthesize). Generates proper PR descriptions per git.md. To be enhanced in Phase 3.5 with artifact integration and profile-aware behavior.
- [ ] **Upgrade Python tooling** (`tools/upgrade.py`) — Deferred to future spec (YAGNI — no Python tools ship with framework yet).
- [ ] **`/contribute-upstream` skill** — Deferred to future spec.
- [ ] **Version tagging** — Deferred to future spec.

### 3.4 — Operating profiles (token optimization)

The discipline enforcement features (subagent-per-story, two-stage code review, full verification) are valuable but token-heavy. Teams with strong human review processes don't need the agent reviewing its own work before a human reviews it again. Operating profiles let teams choose their tradeoff between agent autonomy and token cost.

- [ ] **Profile configuration** — A setting in AGENTS.md or a config file that skills read at startup. Skills adjust their behavior based on the active profile. Profiles are: `full` (default), `team`, and `lean`. (A fourth `autonomous` profile will be added when Phase 5 lands — its capabilities depend on the enhanced session skills and cost enforcement built in Phases 4 and 5.)
- [ ] **Full discipline profile** (default) — Current behavior. Subagent per story, two-stage agent code review, full verify-completion with evidence gathering. Best for solo developers, small teams, or unattended work where the agent's output needs to be right the first time.
- [ ] **Team profile** — Single agent executes stories sequentially (no subagent dispatch), skip agent-side code review (humans handle that via PR), still enforce verify-completion and all hard gates. Anti-rationalization tables and spec discipline remain. Estimated ~40-50% token reduction vs. full profile.
- [ ] **Lean profile** — Single agent, no agent code review, lighter verification (confirm tests pass but skip the full evidence-gathering ritual). For experienced teams with strong CI pipelines and review culture who primarily want the spec structure and session memory. Minimal token overhead beyond baseline.
- [ ] **Profile-aware skill behavior** — `/dispatch-subagents` checks profile: in `full` mode it spawns fresh subagents; in `team`/`lean` mode it executes stories inline. `/request-code-review` checks profile: in `full` mode it dispatches reviewers; in `team`/`lean` mode it skips. `/verify-completion` checks profile: in `full`/`team` mode it does full evidence gathering; in `lean` mode it does a lighter check. Anti-rationalization tables and hard gates remain active in all profiles — they're essentially free (just text the agent reads).

### 3.5 — Enhanced `/create-pr` skill (was `/ship-pr`)

**Note:** The minimal `/create-pr` skill was delivered in SPEC-003 STORY-004. It handles basic PR creation with conventional commit titles and proper descriptions. This phase enhances it with Lit SDLC artifact integration, profile-aware behavior, and git hygiene automation.

The implementation workflow currently ends at `/verify-completion` — the existing `/create-pr` skill creates a well-formatted PR but doesn't leverage Lit SDLC artifacts or adapt to operating profiles. This phase makes it context-aware and profile-intelligent.

- [ ] **PR assembly from Lit SDLC artifacts** — Enhance `/create-pr` to automatically build the PR title, description, and context from the spec README (why), the story (what), the acceptance criteria (scope), and verification evidence (proof it works). This produces better PR descriptions than most humans write because the structured artifacts already contain all the information. Include a summary of files changed, tests added/modified, and standards followed. The existing skill already handles conventional commit titles and basic descriptions — this adds the artifact integration layer.
- [ ] **Profile-aware shipping behavior** — In `team` and `lean` profiles, `/create-pr` prepares the PR, presents a summary to the human, and waits for explicit approval before creating it. In `full` profile, it creates the PR but still requires human merge. In `autonomous` profile, it auto-creates the PR and can optionally auto-merge if two-stage review and verification both passed (configurable). The skill should make the current behavior clear: "This PR will be created but NOT merged — a human must approve" vs. "This PR will be auto-merged based on your autonomous profile settings."
- [ ] **Git hygiene** — Ensure the branch is clean, squash or organize commits per the project's git standard, handle rebasing against the target branch if needed, and set appropriate PR labels/reviewers if configured. Respect `git.md` and `git-worktrees.md` standards.
- [ ] **PR linkage to spec artifacts** — Include links to the spec, story, and ACs in the PR description so reviewers have full context. Optionally update `stories.yml` status to reflect the PR is open. When the PR is merged (detected on next `/start-session`), mark the story as `passing`.

### 3.6 — `/clean-install` skill

The adoption path is: clone the repo → run `/clean-install` → the skill resets all project-specific content and walks you through initial setup. For brownfield projects, `/clean-install` hands off to `/onboard-project`.

**Note:** Minimal AGENTS.md was delivered in SPEC-003 STORY-001 — it's now a generic boot loader that discovers project context from known locations.

- [ ] **Reset project-specific content** — Wipe product docs (mission, roadmap, domain) back to empty templates, clear all specs and session history, reset AGENTS.md `// TODO:` sections, remove any project-specific standards while preserving framework standards. The user clones the full repo (including this roadmap, SPEC-001, etc. as living examples) and the skill strips it down to a clean skeleton. Leverages the framework/project boundary convention from SPEC-003.
- [ ] **Interactive setup wizard** — After reset, walk the user through initial configuration: What languages does your project use? (remove irrelevant language-specific standards like `code-style/java.md` if it's a Go-only shop). What's your project structure? (populate the AGENTS.md project structure section). What's your git workflow? (configure git standards). What's your team size and review process? (set operating profile). This replaces the current manual `// TODO:` customization.
- [ ] **Greenfield vs. brownfield fork** — At the end of clean-install, ask: "Do you have existing documentation to import?" If yes, hand off to `/onboard-project`. If no, hand off to `/plan-product` for a fresh start.
- [ ] **Install validation** — Verify the resulting directory structure is correct using `tools/validate_install.py` from 3.2. All skill files present, standards index valid, product templates in place, AGENTS.md properly configured. Report any issues.

### 3.7 — `/onboard-project` skill (brownfield adoption)

Adopting Lit SDLC in an existing ("brownfield") project is currently painful. The framework assumes product docs, domain knowledge, and architecture context are populated — but real projects have this information scattered across tools like Confluence, Google Docs, Jira, and tribal knowledge of varying quality. There is no workflow for ingesting, vetting, and structuring this existing content.

- [ ] **Content ingestion** — Walk the user through identifying and pulling in existing documentation. Support content provided via copy/paste, file upload, or URL. Categorize each piece into the four Lit SDLC layers (product, standards, context, specs). Handle common sources: Confluence pages, Google Docs, markdown files, README files, wiki pages, Jira epics/stories.
- [ ] **Content quality assessment** — For each piece of ingested content, evaluate: is this a requirement, a solution design, domain knowledge, or a standard? Is it current or stale? Is it well-specified or vague? Is it complete or has gaps? Present a quality scorecard to the user so they can decide what to keep, rewrite, or discard. The goal is collaborative vetting — the agent proposes, the user decides.
- [ ] **Guided content transformation** — Interactive workflow to transform raw content (e.g., a messy Confluence requirements page with mixed quality) into properly structured Lit SDLC artifacts. Walk the user through each section: extract the mission from scattered vision docs, derive business rules from requirements, identify domain terminology, capture architectural decisions. Use the existing `/shape-spec` pattern of presenting drafts for approval rather than silently generating.
- [ ] **Existing feature mapping** — Features already exist but aren't tracked as specs. Provide a way to retroactively create specs from existing functionality — not to re-implement, but to document what exists so future work builds on a known baseline. This solves the "we have 50 features but no specs" problem.
- [ ] **Gap analysis after onboarding** — Once content is ingested and structured, automatically identify what's missing: does the project have a mission but no domain terminology? Architecture docs but no business rules? Standards for some languages but not others? Generate a prioritized onboarding backlog.

### 3.8 — Getting started guide and documentation

- [ ] **Getting started guide** — A walkthrough for new users covering: what Lit SDLC is (link to README), how to install it (link to `/clean-install` or manual steps), first session workflow (`/bootstrap` → `/start-session` → `/shape-spec`), and common patterns. Should be approachable for someone who has never used a context engineering framework.

## Phase 4: Advanced Workflows

- [ ] Deployment and release management (GAP-002)
- [ ] Hotfix / emergency workflow (GAP-003)
- [ ] Story dependency tracking with `depends_on` field in stories.yml (GAP-004)
- [ ] Refactoring / tech debt workflow (GAP-005)
- [ ] NFR tracking integration (GAP-007)
- [ ] External tool integration patterns (GAP-010)
- [ ] Component documentation skill (GAP-011)
- [ ] Enhanced `/start-session` with handoff resumption — Read YAML frontmatter from previous session summaries and resume from where the last agent left off. Support "Proposed Actions" from prior session.
- [ ] Enhanced `/end-session` with structured frontmatter — Produce YAML frontmatter (session_id, spec, tokens_used, cost_usd, status, exit_reason, stories_completed/remaining, files_modified, git_state) plus "Next Agent Should" and "Proposed Actions" sections.
- [ ] Additional unattended guardrails (GR-U07 through GR-U12) — Don't install new dependencies without rationale, don't modify files outside spec scope, don't bypass tests, don't retry failing approach >3 times, write handoff before 80% context budget, don't modify shared config without flagging.

## Phase 5: Autonomous Execution

The framework supports a spectrum from fully interactive to fully autonomous. Phase 5 builds the orchestration layer that reads Lit SDLC artifacts (roadmap, specs, stories) as a work queue and dispatches AI agents to execute stories on a schedule, with security isolation, cost controls, and audit trails. The orchestrator is built as Python tooling in the `tools/` directory — not a separate project.

Reference architecture: [autonomous-agents-plan-original.md](context/architecture/autonomous-agents-plan-original.md) (imported from the original ALIT-SDLC project)

### Phase 5.0: Core orchestrator

- [ ] **Artifact parsers** (`tools/orchestrator/parsers/`) — Parse roadmap.md, specs/index.yml, stories.yml (with `depends_on` and `claimed_by` fields), session summaries, and standards index. All parsers testable with pytest.
- [ ] **Task selection algorithm** (`tools/orchestrator/task_selector.py`) — Priority-ordered, story-level selection with dependency DAG. Only select stories whose dependencies are all `passing`. Mark selected stories as `claimed_by: <session_id>`.
- [ ] **Context builder** (`tools/orchestrator/context_builder.py`) — Assemble agent prompts from spec README, story ACs, relevant standards (via index tags), architecture docs, and previous session summaries. Keeps prompt focused and within context window limits.
- [ ] **Claude Code SDK driver** (`tools/orchestrator/drivers/claude_code.py`) — Wrap the Claude Code SDK. Inject `/start-session` at the beginning and `/end-session` before context budget exhaustion. Include token budget callback for cost enforcement.
- [ ] **Orchestrator core loop + CLI** (`tools/orchestrator/main.py`) — Click-based CLI with `run-cycle` command. One cycle: parse artifacts → select task → build context → dispatch agent → collect results → update story status. Idempotent — safe to run repeatedly.
- [ ] **Audit logging** (`tools/orchestrator/audit.py`) — Append-only JSON lines log. Record every cycle: timestamp, story selected, agent session_id, tokens_used, cost_usd, outcome, files_modified.
- [ ] **Cost enforcement** (`tools/orchestrator/cost_enforcer.py`) — Per-session, per-day, per-spec, and monthly token/cost budgets. Graceful handling when budget exhausted (complete current story, don't start new ones).
- [ ] **Git management** (`tools/orchestrator/git_manager.py`) — Create branch per session, commit agent work, push. No worktrees in Phase 5.0 (single agent at a time).
- [ ] **Systemd timer / cron scheduling** — Run `orchestrator run-cycle` on a schedule. Document setup for both systemd and cron.

### Phase 5.1: Security isolation + GitHub integration

- [ ] Docker container per session with resource limits
- [ ] Bash allowlist — restrict which commands agents can run
- [ ] Git worktree isolation per session
- [ ] Network policy per container
- [ ] Volume permissions (append-only for audit, read-only for standards)
- [ ] `/sync-github` skill — Automated PR creation, CI status monitoring, review feedback collection

### Phase 5.2: Multi-driver + enterprise integration

- [ ] **Cursor driver** (`tools/orchestrator/drivers/cursor.py`) — Cursor CLI headless mode (`cursor agent "prompt" --print --force --output-format stream-json`). Generate `.cursor/rules/` from lit-sdlc standards. Agent-agnostic: same orchestrator, different driver.
- [ ] `/sync-confluence` skill — Read docs from Confluence, publish updated specs back
- [ ] `/sync-jira` skill — Bi-directional ticket sync (Jira epic ↔ spec, Jira story ↔ lit-sdlc story)
- [ ] `/notify-teams` skill — Alerts, approval workflows, stuck agent notifications

### Phase 5.3: Multi-agent + approvals

- [ ] Concurrent agent execution with serialized merge strategy
- [ ] Three-tier file permissions: forbidden / propose_only / agent_writable
- [ ] Three-tier skill permissions: human_only / propose_only / autonomous
- [ ] Approval queue (Teams, Slack, or web UI) for proposed actions
- [ ] Stuck detection + kill switch for runaway agents

### Phase 5.4: Self-improving

- [ ] Auto-guardrail generation from failure patterns
- [ ] Automated standards discovery from successful sessions
- [ ] Adaptive scheduling based on historical cycle performance
- [ ] Cross-session learning — aggregate patterns across specs
- [ ] Cost ROI reporting per spec

## Blocked

_None currently._

## Ideas / Backlog

- Automated skill testing framework — pytest-based system for testing skills (expected inputs → expected outputs), enables regression testing for upgrades
- Multi-language BDD support beyond Go and Java
- CI/CD pipeline integration patterns
- Automated spec-to-issue-tracker sync
- Metrics dashboard for spec completion tracking
- Plugin system for custom skills
- Observability dashboard (Grafana or custom HTML) for autonomous execution
- `/rollback-spec` skill for reverting failed autonomous work
- Credential rotation with secrets sidecar for containerized agents
- Role-based permission tiers for team-scale autonomous execution
