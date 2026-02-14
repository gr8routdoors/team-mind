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

## Phase 3: Distribution (Up Next)

The adoption path is: clone the repo → run `/clean-install` → the skill resets all project-specific content and walks you through initial setup. For brownfield projects, `/clean-install` hands off to `/onboard-project` which guides content ingestion and vetting from existing documentation sources.

### `/clean-install` skill

- [ ] **Reset project-specific content** — Wipe product docs (mission, roadmap, domain) back to empty templates, clear all specs and session history, reset AGENTS.md `// TODO:` sections, remove any project-specific standards while preserving framework standards. The user clones the full repo (including this roadmap, SPEC-001, etc. as living examples) and the skill strips it down to a clean skeleton.
- [ ] **Minimal AGENTS.md** — Redesign AGENTS.md as a pure boot loader rather than a reference document. Current AGENTS.md duplicates content that belongs in standards, skills, and architecture docs. The new AGENTS.md should contain only: a one-paragraph project description, the Lit SDLC directory structure, the single rule "run `/start-session` first (or `/bootstrap` if new)," project-specific configuration (tech stack, build commands, project structure), and the operating profile setting. All framework documentation (workflow tables, discipline enforcement explanations, standards references) should be removed — the skills and standards already contain that information, and `/start-session` loads what's needed. This also makes `/clean-install` simpler since there's less to separate.
- [ ] **Interactive setup wizard** — After reset, walk the user through initial configuration: What languages does your project use? (remove irrelevant language-specific standards like `code-style/java.md` if it's a Go-only shop). What's your project structure? (populate the AGENTS.md project structure section). What's your git workflow? (configure git standards). What's your team size and review process? (set operating profile). This replaces the current manual `// TODO:` customization.
- [ ] **Greenfield vs. brownfield fork** — At the end of clean-install, ask: "Do you have existing documentation to import?" If yes, hand off to `/onboard-project`. If no, hand off to `/plan-product` for a fresh start.
- [ ] **Install validation** — Verify the resulting directory structure is correct: all skill files present, standards index valid, product templates in place, AGENTS.md properly configured. Report any issues.

### `/onboard-project` skill (brownfield adoption)

Adopting Lit SDLC in an existing ("brownfield") project is currently painful. The framework assumes product docs, domain knowledge, and architecture context are populated — but real projects have this information scattered across tools like Confluence, Google Docs, Jira, and tribal knowledge of varying quality. There is no workflow for ingesting, vetting, and structuring this existing content.

- [ ] **Content ingestion** — Walk the user through identifying and pulling in existing documentation. Support content provided via copy/paste, file upload, or URL. Categorize each piece into the four Lit SDLC layers (product, standards, context, specs). Handle common sources: Confluence pages, Google Docs, markdown files, README files, wiki pages, Jira epics/stories.
- [ ] **Content quality assessment** — For each piece of ingested content, evaluate: is this a requirement, a solution design, domain knowledge, or a standard? Is it current or stale? Is it well-specified or vague? Is it complete or has gaps? Present a quality scorecard to the user so they can decide what to keep, rewrite, or discard. The goal is collaborative vetting — the agent proposes, the user decides.
- [ ] **Guided content transformation** — Interactive workflow to transform raw content (e.g., a messy Confluence requirements page with mixed quality) into properly structured Lit SDLC artifacts. Walk the user through each section: extract the mission from scattered vision docs, derive business rules from requirements, identify domain terminology, capture architectural decisions. Use the existing `/shape-spec` pattern of presenting drafts for approval rather than silently generating.
- [ ] **Existing feature mapping** — Features already exist but aren't tracked as specs. Provide a way to retroactively create specs from existing functionality — not to re-implement, but to document what exists so future work builds on a known baseline. This solves the "we have 50 features but no specs" problem.
- [ ] **Gap analysis after onboarding** — Once content is ingested and structured, automatically identify what's missing: does the project have a mission but no domain terminology? Architecture docs but no business rules? Standards for some languages but not others? Generate a prioritized onboarding backlog.

### Operating profiles (token optimization)

The discipline enforcement features (subagent-per-story, two-stage code review, full verification) are valuable but token-heavy. Teams with strong human review processes don't need the agent reviewing its own work before a human reviews it again. Operating profiles let teams choose their tradeoff between agent autonomy and token cost.

- [ ] **Profile configuration** — A setting in AGENTS.md or a config file that skills read at startup. Skills adjust their behavior based on the active profile. Profiles are: `full` (default), `team`, and `lean`.
- [ ] **Full discipline profile** (default) — Current behavior. Subagent per story, two-stage agent code review, full verify-completion with evidence gathering. Best for solo developers, small teams, or unattended work where the agent's output needs to be right the first time.
- [ ] **Team profile** — Single agent executes stories sequentially (no subagent dispatch), skip agent-side code review (humans handle that via PR), still enforce verify-completion and all hard gates. Anti-rationalization tables and spec discipline remain. Estimated ~40-50% token reduction vs. full profile.
- [ ] **Lean profile** — Single agent, no agent code review, lighter verification (confirm tests pass but skip the full evidence-gathering ritual). For experienced teams with strong CI pipelines and review culture who primarily want the spec structure and session memory. Minimal token overhead beyond baseline.
- [ ] **Profile-aware skill behavior** — `/dispatch-subagents` checks profile: in `full` mode it spawns fresh subagents; in `team`/`lean` mode it executes stories inline. `/request-code-review` checks profile: in `full` mode it dispatches reviewers; in `team`/`lean` mode it skips. `/verify-completion` checks profile: in `full`/`team` mode it does full evidence gathering; in `lean` mode it does a lighter check. Anti-rationalization tables and hard gates remain active in all profiles — they're essentially free (just text the agent reads).

### Other distribution items

- [ ] Getting started guide and documentation
- [ ] Automated skill testing framework

## Phase 4: Advanced Workflows (Future)

- [ ] Deployment and release management (GAP-002)
- [ ] Hotfix / emergency workflow (GAP-003)
- [ ] Story dependency tracking (GAP-004)
- [ ] Refactoring / tech debt workflow (GAP-005)
- [ ] NFR tracking integration (GAP-007)
- [ ] External tool integration patterns (GAP-010)
- [ ] Component documentation skill (GAP-011)

## Blocked

_None currently._

## Ideas / Backlog

- Multi-language BDD support beyond Go and Java
- CI/CD pipeline integration patterns
- Automated spec-to-issue-tracker sync
- Metrics dashboard for spec completion tracking
- Plugin system for custom skills
