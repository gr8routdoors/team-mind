# Future Work

> Ideas and deferred items for future specs. These were discussed and shaped but aren't prioritized yet.

---

## Adoption Experience

Skills and tooling for bringing new users and projects into Lit SDLC.

- **`/clean-install` skill** — Reset a cloned repo to a clean skeleton with an interactive setup wizard (language selection, project structure, git workflow). Forks to `/onboard-project` (brownfield) or `/plan-product` (greenfield). Validates install via Python tooling.
- **`/onboard-project` skill** — Brownfield content ingestion for existing projects. Copy/paste or file upload of docs from Confluence, Google Docs, Jira, etc. Quality assessment and scorecard. Guided transformation into Lit SDLC artifacts (mission, roadmap, specs). Feature mapping to retroactive specs. Gap analysis after onboarding.
- **Getting started guide** — User-facing walkthrough covering install, first session, and common workflows.

## Framework Maintenance

Tooling for managing the framework itself across versions and projects.

- **Framework manifest** (`framework-manifest.yml`) — Hash-based file tracking listing all framework-owned files with sha256 hashes. Enables validation, contribution detection, and richer upgrade reporting. Not needed for the current nuke-and-replace upgrade approach but useful for future sophistication.
- **Validator scripts** — `tools/validate_standards.py` (parse index.yml, verify files exist, validate tags, check for orphans), `tools/validate_install.py` (verify directory structure and completeness), `tools/parse_session.py` (parse session summaries with YAML frontmatter, feeds into Phase 5).
- **`/contribute-upstream` skill** — Identify local framework modifications and package them for upstream contribution as a PR-ready format.
- **Version tagging** — Semantic versioning convention, version integrated into manifest, changelog generation.

## Operating Profiles

A configuration mechanism for tuning Lit SDLC behavior to match a team's workflow. Detailed vision captured in `specs/SPEC-002-developer-workflow/future-profiles.md`.

- **Three profiles**: full (subagent per story, two-stage review), team (single agent, human PR review), lean (single agent, lighter verification)
- **Profile-aware skills**: dispatch-subagents, request-code-review, verify-completion adapt based on profile
- **Profile-aware shipping**: /ship-pr behavior changes per profile (auto-create vs wait-for-approval)
- Anti-rationalization tables and hard gates remain enforced in all profiles

## Autonomous Execution (Phase 5)

Full autonomous operation from the `autonomous-agents-plan-original.md` architecture blueprint.

- Session orchestrator in `tools/orchestrator/`
- 12-layer security model
- Agent driver abstraction
- Phased rollout from monitored to fully autonomous
- Enterprise integrations (Confluence, Jira, Teams)

## Backlog

- Automated skill testing framework
- Multi-language BDD support beyond Go and Java
- CI/CD integration patterns
- Observability dashboard
- `/rollback-spec` skill
- Credential rotation
- Role-based permissions

---

_Last updated: 2026-02-15_
