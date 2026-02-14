# Autonomous Agents Platform — Architecture Plan

**Author**: Devon + Claude (co-authored)
**Date**: 2026-02-07
**Status**: DRAFT v3 — Iterating

---

## 1. Vision & Goals

Build a secure, self-hosted platform that runs Claude Code and Cursor autonomously against a product roadmap, using lit-sdlc as the workflow kernel. The system picks up the next piece of work, executes it inside a sandboxed container, commits results to git, and integrates with enterprise tooling — all on a schedule or triggered by events.

**Core goals:**

- **Autonomous roadmap execution** — Agent reads `roadmap.md`, picks next priority, shapes specs, writes code, runs tests, opens PRs — without human babysitting.
- **Security by design** — Sandboxed Docker containers, bash allowlisting, network restrictions, and approval queues. A compromised skill can't wreck the host or other work.
- **Agent-agnostic** — Same workflow whether the driver is Claude Code (home) or Cursor (work). Swap the runtime, keep the kernel.
- **Iterative hardening** — Ship value early with basic isolation, then layer on security controls across phases.
- **Enterprise integration** — GitHub for PRs/CD, Confluence for artifact access, Jira for work tracking, Teams for notifications and approval workflows.

**Non-goals (for now):**

- Multi-tenant / SaaS deployment
- Custom model fine-tuning
- Real-time pair programming (that's what interactive mode is for)

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    HOST (Dedicated Server)                     │
│                                                                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐  │
│  │  Scheduler    │──▶│ Orchestrator  │──▶│  Audit Logger    │  │
│  │  (cron/event) │   │  (Python)     │   │  (append-only)   │  │
│  └──────────────┘   └──────┬───────┘   └──────────────────┘  │
│                            │                                   │
│              ┌─────────────┼─────────────┐                    │
│              ▼             ▼             ▼                     │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐    │
│  │ Agent Container │ │ Agent Container │ │ Agent Container │    │
│  │ (Spec-012)     │ │ (Spec-015)     │ │ (Spec-018)     │    │
│  │                │ │                │ │                │    │
│  │ Claude Code    │ │ Cursor CLI     │ │ Claude Code    │    │
│  │ + lit-sdlc     │ │ + lit-sdlc     │ │ + lit-sdlc     │    │
│  │ + workspace    │ │ + workspace    │ │ + workspace    │    │
│  └────────────────┘ └────────────────┘ └────────────────┘    │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Shared Volumes (controlled access)          │  │
│  │  /lit-sdlc (RO: skills, standards) │ /repos (RW: code)  │  │
│  │  /secrets (RO: API keys, tokens)   │ /audit (append)     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Enterprise Integration Layer                │  │
│  │  GitHub Skill │ Confluence Skill │ Jira Skill │ Teams    │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Key components:**

- **Scheduler** — Triggers work via cron schedules or external events (webhooks, Jira transitions, manual CLI).
- **Orchestrator** — The brain. Reads lit-sdlc artifacts, determines next work item, builds task context, dispatches to a container, validates results.
- **Agent Container** — Ephemeral Docker container running either Claude Code or Cursor against a specific spec/story. Destroyed after the session.
- **Enterprise Integration Layer** — lit-sdlc skills that sync with GitHub, Confluence, Jira, and Teams.
- **Audit Logger** — Append-only log of every action, decision, and outcome for traceability.

---

## 3. lit-sdlc as Kernel

The existing lit-sdlc framework already provides the core workflow primitives. The autonomous platform wraps an orchestration layer around them.

### What lit-sdlc provides (the kernel):

| Capability | Artifact/Skill | Role in Automation |
|---|---|---|
| Work queue | `roadmap.md` + `specs/index.yml` | Orchestrator reads these to pick next task |
| Task definition | `SPEC-NNN/README.md`, `design.md` | Context for the agent session |
| Progress tracking | `stories.yml` + story status | Orchestrator tracks completion |
| Executable specs | `acs/*.md` → BDD tests | Verification that work is correct |
| Session management | `/start-session`, `/end-session` | Agent lifecycle with context preservation |
| Workflow steps | `/shape-spec`, `/derive-acs`, `/generate-bdd-tests`, `/continue-spec` | The actual work the agent does |
| Safety rails | `guardrails.md` + unattended mode (GR-U01–U06) | Prevent agents from going off the rails |
| Self-healing | Session failure tables → guardrail updates | System learns from mistakes |
| Standards | `standards/index.yml` + tag-based filtering | Context-aware constraints |

### What we build on top (the platform):

| Capability | New Component | Why Needed |
|---|---|---|
| Task dispatch | Orchestrator | Reads kernel state, decides what to do, launches agents |
| Scheduling | Scheduler | Triggers work on cadence or events |
| Isolation | Docker containers | Security boundary per agent session |
| Agent abstraction | Driver layer | Swap Claude Code / Cursor without changing workflow |
| Enterprise sync | Integration skills | GitHub, Confluence, Jira, Teams |
| Observability | Audit log + dashboard | Know what happened, when, and why |

### Orchestrator ↔ Kernel interaction loop:

```
1. Scheduler triggers orchestrator
2. Orchestrator reads roadmap.md → picks highest-priority spec
3. Orchestrator reads specs/index.yml → checks spec state
4. Orchestrator reads stories.yml → finds next pending/failing story
5. Orchestrator loads recent session summaries for context
6. Orchestrator builds task prompt with all relevant context
7. Orchestrator launches container with agent + task
8. Agent runs: /start-session → [appropriate skill] → /end-session
9. Agent commits work to feature branch
10. Orchestrator validates: tests pass? artifacts updated? story status changed?
11. Orchestrator triggers integration skills: create PR, update Jira, notify Teams
12. Orchestrator logs everything to audit trail
13. Loop back to step 2 (or wait for next schedule trigger)
```

---

## 4. Agent Runtime & Security Model

### 4.1 Container Architecture

Each agent session runs in an ephemeral Docker container with strict boundaries:

```dockerfile
# Base image with agent tooling pre-installed
FROM ubuntu:22.04 AS agent-base

# Install: git, language runtimes, build tools
# Install: claude-code-sdk OR cursor-cli (based on build arg)
# Install: lit-sdlc skills (copied in)

# Non-root user
RUN useradd -m agent
USER agent

# Entrypoint: orchestrator-provided task script
ENTRYPOINT ["/usr/local/bin/agent-runner.sh"]
```

### 4.2 Volume Mounts & Permissions

| Mount | Container Path | Permission | Purpose |
|---|---|---|---|
| lit-sdlc skills + standards | `/lit-sdlc/` | **Read-only** | Agent can use skills but can't modify them |
| Project repo (worktree) | `/workspace/` | **Read-write** | Agent works on code here |
| API credentials | `/secrets/` | **Read-only, tmpfs** | Keys loaded as env vars, never written to disk |
| Audit log | `/audit/` | **Append-only** | Agent writes logs but can't read/delete them |

**Audit log immutability enforcement:** The host uses `chattr +a` (Linux append-only file attribute) on log files before mounting them into containers. Once set, even root cannot truncate, delete, or modify existing content — only append new lines. The orchestrator creates and configures log files on the host; agents in containers (running as non-root) can only write new entries.

```bash
# Host-side: orchestrator creates log file with append-only attribute
touch /var/log/agent-audit/session-${SESSION_ID}.jsonl
chattr +a /var/log/agent-audit/session-${SESSION_ID}.jsonl
# Mount into container as /audit/session.jsonl
```

Simple, zero-dependency, built into Linux. Revisit with named-pipe or sidecar architecture if we hit enterprise scale.

### 4.3 Network Policy

```yaml
# Docker network policy
# Each agent container gets its own isolated network — no inter-container traffic
agent-networks:
  isolation: per-container       # Each container on its own Docker network
  inter_container: deny          # Agents cannot talk to each other

  # Egress allowlist (per container)
  egress:
    # Claude Code driver
    claude-code:
      - api.anthropic.com        # Claude API
      - github.com               # Git push/pull
      - registry.npmjs.org       # Package installs (if needed)
      - pypi.org                 # Package installs (if needed)

    # Cursor driver (additional endpoints)
    cursor:
      - api.anthropic.com        # Claude API (via Cursor)
      - api2.cursor.sh           # Cursor's API endpoint
      - cursor.sh                # Cursor service
      - github.com               # Git push/pull
      - registry.npmjs.org
      - pypi.org

  # DENY: everything not listed above
  default: deny
```

**Inter-container isolation**: Each agent container runs on its own Docker bridge network. Even if one container is compromised, it cannot reach other agent containers, the orchestrator's internal ports, or any host services.

### 4.4 Bash Allowlisting

Inspired by Anthropic's autonomous-coding quickstart, each container runs with a bash allowlist:

```python
ALLOWED_COMMANDS = [
    "git *",
    "go *", "java *", "mvn *", "gradle *",  # Build tools
    "npm *", "npx *", "pip *",               # Package managers
    "make *",
    "cat *", "ls *", "find *", "grep *",     # Read-only fs
    "mkdir *", "cp *", "mv *",               # Workspace only
    "pytest *", "go test *",                   # Test runners
]

DENIED_COMMANDS = [
    "rm -rf /",                               # Obviously
    "curl *", "wget *",                       # No arbitrary downloads
    "sudo *",                                 # No privilege escalation
    "docker *",                               # No container escape
    "ssh *", "scp *",                         # No lateral movement
    "chmod *", "chown *",                     # No permission changes
]
```

### 4.5 Defense-in-Depth Layers

```
Layer 1: lit-sdlc Guardrails (GR-U01–U12)
  ↓  Agent's own behavioral constraints (in-prompt)
Layer 2: Bash Allowlist
  ↓  Only approved commands can execute
Layer 3: Docker Container Isolation
  ↓  No host access, resource limits, non-root user
Layer 4: Network Policy (per-container)
  ↓  Only approved endpoints reachable, no inter-container traffic
Layer 5: Volume Permissions + chattr +a
  ↓  Read-only skills, append-only immutable audit log
Layer 6: Git Worktree Isolation
  ↓  Agent works on isolated copy, can't touch canonical state
Layer 7: Three-Tier File/Skill Permissions
  ↓  Forbidden changes reverted, propose_only routed to approval
Layer 8: Serialized Merge + PR Review
  ↓  Orchestrator is single writer, all output goes through PRs
Layer 9: Cost Budgets
  ↓  Per-session, per-day, per-spec, monthly caps
Layer 10: Approval Queue (Phase 3)
  ↓  Sensitive actions pause for human sign-off
Layer 11: Stuck Detection + Kill Switch
  ↓  Runaway agents detected and terminated
Layer 12: Audit Trail (immutable)
  ↓  Full record of every action for post-hoc review
```

### 4.6 Resource Limits

```yaml
# docker-compose per agent container
deploy:
  resources:
    limits:
      cpus: "4"
      memory: 8G
    reservations:
      cpus: "2"
      memory: 4G
  # Auto-kill after max session duration
  stop_grace_period: 30s
  # Max runtime enforced by orchestrator
```

### 4.7 Iterative Security Hardening Path

| Phase | Security Level | What's Added |
|---|---|---|
| Phase 0 | Basic | Non-root user, git-gated output, audit logging |
| Phase 1 | Moderate | Docker isolation, volume permissions, bash allowlist |
| Phase 2 | Strong | Network policy, resource limits, secret rotation |
| Phase 3 | Full | Approval queues, anomaly detection, kill switches |

---

## 5. Agent Abstraction Layer

The system must support both Claude Code and Cursor interchangeably. The abstraction sits between the orchestrator and the actual agent binary.

### 5.1 Driver Interface

```python
class AgentDriver(ABC):
    """Abstract interface for agent execution."""

    @abstractmethod
    async def start_session(self, task: TaskContext) -> SessionHandle:
        """Launch an agent session with the given task context."""
        ...

    @abstractmethod
    async def monitor(self, session: SessionHandle) -> SessionStatus:
        """Check session progress and health."""
        ...

    @abstractmethod
    async def stop(self, session: SessionHandle) -> SessionResult:
        """Gracefully stop a session and collect results."""
        ...
```

### 5.2 Claude Code Driver

```python
class ClaudeCodeDriver(AgentDriver):
    """Uses claude-code-sdk for headless execution."""

    async def start_session(self, task: TaskContext) -> SessionHandle:
        # Build prompt from task context
        prompt = self._build_prompt(task)

        # Launch via SDK with allowlisted tools
        session = await claude_sdk.create_session(
            prompt=prompt,
            model="claude-sonnet-4-5-20250929",
            tools=task.allowed_tools,
            max_turns=task.max_turns,
            working_directory=task.workspace_path,
        )
        return SessionHandle(driver="claude-code", session_id=session.id)
```

### 5.3 Cursor Driver

Research confirms Cursor CLI supports full headless execution (as of Jan 2026):
`cursor agent "prompt" --print --force --output-format json`

```python
class CursorDriver(AgentDriver):
    """Uses Cursor's CLI for headless execution."""

    async def start_session(self, task: TaskContext) -> SessionHandle:
        # Write project rules from lit-sdlc standards
        # NOTE: .cursorrules is deprecated — use .cursor/rules/*.mdc
        self._write_project_rules(task)
        # Also write AGENTS.md for Cursor's native agent instructions
        self._write_agents_md(task)

        prompt = self._build_prompt(task)

        # Launch Cursor agent in headless mode
        process = await asyncio.create_subprocess_exec(
            "cursor", "agent", prompt,
            "--print",                        # Non-interactive / headless
            "--force",                        # Allow direct file changes
            "--output-format", "stream-json", # Structured output for monitoring
            cwd=task.workspace_path,
            env={
                **os.environ,
                "CURSOR_API_KEY": task.api_key,  # Service account key
            },
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return SessionHandle(driver="cursor", pid=process.pid,
                             stream=process.stdout)

    def _write_project_rules(self, task: TaskContext):
        """Generate .cursor/rules/ from lit-sdlc standards."""
        rules_dir = task.workspace_path / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        # Convert lit-sdlc standards to .mdc format
        for standard in task.standards:
            mdc_content = self._to_mdc(standard)
            (rules_dir / f"{standard.name}.mdc").write_text(mdc_content)

    def _write_agents_md(self, task: TaskContext):
        """Generate AGENTS.md with session context and lit-sdlc workflow."""
        agents_md = task.workspace_path / "AGENTS.md"
        agents_md.write_text(self._build_agents_md(task))
```

**Cursor-specific capabilities we can leverage:**

- **`--output-format stream-json`** — Real-time progress monitoring from orchestrator
- **Background agents** — Prefix with `&` to offload to Cursor's cloud VMs (optional, for work environments with Cursor Pro)
- **Service accounts** — Enterprise feature for team-scale automation without personal credentials
- **MCP support** — Cursor's MCP servers can provide enterprise integrations (GitHub, Jira, etc.) natively
- **`cursor agent resume`** — Resume previous conversations (complementary to lit-sdlc handoffs)

### 5.4 Configuration

```yaml
# config.yml
agents:
  default_driver: claude-code
  drivers:
    claude-code:
      model: claude-sonnet-4-5-20250929
      max_turns: 200
      sdk_path: /usr/local/bin/claude
    cursor:
      binary: /usr/local/bin/cursor
      model: claude-sonnet-4-5  # via Anthropic provider in Cursor settings
      output_format: stream-json
      # Modern rules location (NOT .cursorrules — deprecated)
      rules_dir: .cursor/rules/
      agents_md_template: /lit-sdlc/agents-md-template.md
```

---

## 6. Orchestrator Design

The orchestrator is the central brain — a Python process running on the host (not in a container) that reads lit-sdlc state and dispatches work.

### 6.1 Core Logic

```python
class Orchestrator:
    async def run_cycle(self):
        """One orchestration cycle: pick work, dispatch, validate."""

        # 1. Read current state from lit-sdlc artifacts
        roadmap = self.read_roadmap()
        spec_index = self.read_spec_index()
        recent_sessions = self.read_recent_sessions(limit=3)

        # 2. Determine next work item
        task = self.pick_next_task(roadmap, spec_index)
        if not task:
            self.log("No actionable work found. Sleeping.")
            return

        # 3. Build task context
        context = self.build_context(task, recent_sessions)

        # 4. Launch container with agent
        container = await self.launch_container(
            driver=self.config.default_driver,
            task=context,
            timeout=self.config.max_session_duration,
        )

        # 5. Monitor until complete or timeout
        result = await self.monitor_until_done(container)

        # 6. Validate results
        validation = self.validate_results(result, task)

        # 7. Post-processing: PR, Jira, notifications
        if validation.passed:
            await self.run_integrations(result, task)

        # 8. Audit log
        self.audit.log(task=task, result=result, validation=validation)
```

### 6.2 Task Selection Algorithm

Task selection operates at the **story level** (not spec level) to maximize parallelism. Multiple agents can work on different stories within the same spec simultaneously, provided dependency constraints are satisfied.

#### Story-Level Dependency DAG

The `stories.yml` format is extended with `depends_on` and `claimed_by` fields:

```yaml
# agent-os/specs/SPEC-012-order-processing/stories.yml
stories:
  - id: STORY-001
    title: Create user model
    status: pending          # pending | claimed | passing | failing | deferred
    depends_on: []
    claimed_by: null         # session_id when claimed, null when free

  - id: STORY-002
    title: Create order model
    status: pending
    depends_on: []
    claimed_by: null

  - id: STORY-003
    title: Order validation logic
    status: pending
    depends_on: [STORY-001, STORY-002]  # Can't start until both pass
    claimed_by: null

  - id: STORY-004
    title: Order API endpoint
    status: pending
    depends_on: [STORY-003]
    claimed_by: null
```

Stories 001 and 002 have no dependencies and can run **in parallel** on separate agents. Story 003 blocks until both are `passing`. This addresses lit-sdlc GAP-004 (story dependencies).

#### Selection Logic

```python
def pick_next_task(self, roadmap, spec_index) -> Optional[Task]:
    """Priority-ordered task selection with story-level granularity."""

    # Priority 1: Unclaimed stories with satisfied dependencies
    for spec in spec_index.by_status("in_progress"):
        story = self._next_available_story(spec)
        if story:
            self._claim_story(spec, story)  # Set claimed_by
            return Task(type="continue", spec=spec, story=story,
                        skill="/continue-spec")

    # Priority 2: Specs in_design needing stories
    for spec in spec_index.by_status("in_design"):
        if not spec.has_stories():
            return Task(type="derive", spec=spec,
                        skill="/derive-acs")

    # Priority 3: Specs in_requirements needing shaping
    for spec in spec_index.by_status("in_requirements"):
        return Task(type="shape", spec=spec,
                    skill="/shape-spec")

    # Priority 4: Roadmap items without specs
    for item in roadmap.unspecced_priorities():
        return Task(type="new_spec", item=item,
                    skill="/shape-spec")

    return None  # Nothing to do

def _next_available_story(self, spec: Spec) -> Optional[Story]:
    """Find next story that is unclaimed and has all dependencies met."""
    for story in spec.stories:
        if story.status in ("pending", "failing") \
                and story.claimed_by is None \
                and self._deps_satisfied(spec, story):
            return story
    return None

def _deps_satisfied(self, spec: Spec, story: Story) -> bool:
    """All depends_on stories must be 'passing'."""
    for dep_id in story.depends_on:
        dep = spec.get_story(dep_id)
        if dep.status != "passing":
            return False
    return True

def _claim_story(self, spec: Spec, story: Story):
    """Mark story as claimed by this session. Orchestrator holds the lock."""
    story.claimed_by = self.current_session_id
    story.status = "claimed"
    spec.save_stories()  # Write to stories.yml on canonical branch
```

**Claim lifecycle:** The orchestrator claims stories before launching containers and releases them when the session completes (either by updating status to `passing`/`failing`, or clearing `claimed_by` on session failure). If a container is killed, the orchestrator clears the claim during cleanup.

### 6.3 Context Building

The orchestrator assembles a rich prompt for the agent that includes:

```python
def build_context(self, task, recent_sessions) -> TaskContext:
    return TaskContext(
        # What to do
        task_description=task.describe(),
        skill_to_invoke=task.skill,

        # lit-sdlc context
        roadmap=self.read_file("agent-os/product/roadmap.md"),
        spec_readme=task.spec.readme if task.spec else None,
        spec_design=task.spec.design if task.spec else None,
        stories=task.spec.stories if task.spec else None,
        recent_sessions=recent_sessions,

        # Standards (filtered by activity tags)
        standards=self.load_standards(tags=task.relevant_tags()),

        # Operating mode
        mode="unattended",
        guardrails=self.load_guardrails(),
    )
```

---

## 7. Scheduler

### 7.1 Schedule Types

```yaml
# schedules.yml
schedules:
  # Nightly roadmap execution
  nightly-build:
    cron: "0 2 * * *"           # 2 AM daily
    action: run_cycle
    max_concurrent: 2
    description: "Pick up next roadmap items and execute"

  # Continuous: check for work every 30 minutes
  continuous:
    cron: "*/30 * * * *"
    action: run_cycle
    max_concurrent: 1
    condition: "has_pending_work"  # Skip if nothing to do

  # Event-driven: respond to external triggers
  on-pr-merged:
    trigger: github_webhook
    event: pull_request.merged
    action: run_cycle
    description: "PR merged → pick up next story"

  on-jira-ready:
    trigger: jira_webhook
    event: issue.transitioned
    condition: "status == 'Ready for Dev'"
    action: create_spec_from_jira
```

### 7.2 Implementation

Phase 0–1: Simple systemd timer or cron calling the orchestrator CLI.

```bash
# /etc/systemd/system/agent-orchestrator.timer
[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Service]
ExecStart=/usr/local/bin/orchestrator run-cycle
User=orchestrator
```

Phase 2+: Lightweight event loop (Python asyncio) that handles both cron and webhooks.

```python
class Scheduler:
    async def run(self):
        # Start webhook listener
        webhook_server = await self.start_webhook_listener()

        # Start cron scheduler
        for schedule in self.config.schedules:
            if schedule.cron:
                self.cron.add(schedule.cron, self.orchestrator.run_cycle)

        # Run forever
        await asyncio.gather(webhook_server, self.cron.run())
```

---

## 8. Session Continuity (Agent-Agnostic)

A spec may take multiple agent sessions to complete. Since we support both Claude Code and Cursor, we can't rely on any SDK's session memory. Instead, we use **structured handoff artifacts** within lit-sdlc — extending the existing session summary system into a full "save game" format.

### 8.1 Design Principles

- **Agent-agnostic** — Handoff artifacts are markdown/YAML files. Any agent (Claude Code, Cursor, or a future tool) reads them on startup.
- **Git-native** — All handoff state is committed, providing history and rollback.
- **Builds on lit-sdlc** — Extends `/end-session` and `/start-session` rather than inventing parallel state.
- **Human-readable** — An engineer can read a handoff artifact and understand exactly where things stand.

### 8.2 Enhanced Session Summary Format

The current lit-sdlc `/end-session` produces a dated session summary. We extend it with structured YAML frontmatter for machine parsing:

```yaml
# agent-os/context/sessions/2026-02-07-order-processing.md
---
session_id: "sess_20260207_143000"
spec: SPEC-012-order-processing
story_focus: STORY-003-payment-validation
agent_driver: claude-code
model: claude-sonnet-4-5-20250929
mode: unattended
duration_minutes: 45
tokens_used: 182000
cost_usd: 0.73

status: partial          # complete | partial | blocked | failed
exit_reason: session_budget_reached

stories_completed:
  - STORY-001-order-submission    # was failing → now passing
  - STORY-002-inventory-check     # was failing → now passing

stories_remaining:
  - STORY-003-payment-validation  # in progress, 2/5 tests passing
  - STORY-004-confirmation-email  # not started

files_modified:
  - src/orders/payment.go         # created
  - src/orders/payment_test.go    # created
  - src/orders/inventory.go       # modified (added validation)

git_state:
  branch: feat/SPEC-012-order-processing
  last_commit: "a3f2e91"
  uncommitted: false
---

## Session Summary

Implemented order submission and inventory check stories. Payment
validation is partially complete — Stripe webhook handler is written
but signature verification is failing on test fixtures.

## Key Decisions

- Using idempotency keys for Stripe calls (prevents duplicate charges)
- Inventory check is synchronous for now (async optimization deferred to SPEC-015)

## Blockers & Issues

- Payment test fixtures need real Stripe test-mode webhook signatures
- Consider: should we mock Stripe or use their test endpoint?

## Next Agent Should

1. Fix Stripe webhook signature verification in payment_test.go
2. Complete remaining 3 tests for STORY-003
3. Start STORY-004 (confirmation email) if time permits

## Failures (GOTCHA Self-Healing)

| What Failed | Why | Lesson | Added to Guardrails? |
|---|---|---|---|
| Direct Stripe API call in test | Test hit real API, got rate-limited | Always mock external APIs in unit tests | Pending |
```

### 8.3 Session Resumption Protocol

The `/start-session` skill is enhanced to read handoff artifacts:

```
Session Start (Unattended Mode):
1. Read most recent session summary for this spec
2. Parse YAML frontmatter → know exactly which story, which files, what's left
3. Read "Next Agent Should" section → immediate action plan
4. Run tests to verify current state matches summary
5. If state diverges (e.g., someone merged other work) → re-assess
6. Continue from where previous session left off
```

This works identically whether the agent is Claude Code or Cursor, because both read the same markdown files.

### 8.4 Handoff Integrity Validation

The orchestrator validates handoff artifacts before launching the next session:

```python
def validate_handoff(self, session_summary: Path) -> HandoffStatus:
    """Ensure the handoff artifact is trustworthy."""
    meta = parse_yaml_frontmatter(session_summary)

    # Verify git state matches what the summary claims
    actual_commit = git.get_head(meta.branch)
    if actual_commit != meta.git_state.last_commit:
        return HandoffStatus.STALE  # Someone else pushed

    # Verify test state matches claimed story statuses
    test_results = run_tests(meta.spec)
    for story in meta.stories_completed:
        if not test_results.passing(story):
            return HandoffStatus.REGRESSION  # Tests regressed

    return HandoffStatus.VALID
```

---

## 9. Cost Management

### 9.1 Budget Hierarchy

```yaml
# config.yml
budgets:
  per_session:
    max_tokens: 500000          # ~$2 per session at Sonnet rates
    max_duration_minutes: 60
    max_turns: 200              # Claude Code SDK turns

  per_day:
    max_total_usd: 50.00        # Hard daily cap
    max_sessions: 20
    alert_threshold_usd: 30.00  # Notify at 60% of daily cap

  per_spec:
    max_sessions: 15            # If a spec takes >15 sessions, it's stuck
    max_total_usd: 100.00       # Hard cap per spec

  monthly:
    max_total_usd: 500.00       # Monthly ceiling
    alert_threshold_usd: 350.00
```

### 9.2 Enforcement

```python
class CostEnforcer:
    """Runs in the orchestrator, gates every session launch."""

    async def check_budget(self, task: Task) -> BudgetDecision:
        today_spend = self.audit.total_spend_today()
        spec_spend = self.audit.total_spend_for_spec(task.spec.id)
        monthly_spend = self.audit.total_spend_this_month()

        if monthly_spend >= self.config.monthly.max_total_usd:
            return BudgetDecision.BLOCKED_MONTHLY
        if today_spend >= self.config.per_day.max_total_usd:
            return BudgetDecision.BLOCKED_DAILY
        if spec_spend >= self.config.per_spec.max_total_usd:
            return BudgetDecision.BLOCKED_SPEC_CAP
        if today_spend >= self.config.per_day.alert_threshold_usd:
            await self.notify("Daily spend at ${today_spend}, approaching limit")
        return BudgetDecision.APPROVED

    def session_token_callback(self, tokens_used: int, session: SessionHandle):
        """Called periodically during agent execution."""
        if tokens_used >= self.config.per_session.max_tokens:
            self.orchestrator.graceful_stop(session, reason="token_budget")
```

### 9.3 Cost Tracking in Audit Log

Every session records token usage and estimated cost in both the audit log and the lit-sdlc session summary (see Section 8.2 frontmatter: `tokens_used`, `cost_usd`). This enables per-spec ROI analysis: how much did it cost to implement SPEC-012, and was it worth it?

---

## 10. Stuck Spec Detection & Human Escalation

### 10.1 Stuck Detection Heuristics

```python
class StuckDetector:
    """Identifies specs that aren't making progress."""

    def check(self, spec: Spec) -> Optional[StuckReason]:
        sessions = self.get_sessions_for_spec(spec.id)

        # No progress across N sessions
        if len(sessions) >= 3:
            recent = sessions[-3:]
            stories_before = recent[0].stories_remaining
            stories_after = recent[-1].stories_remaining
            if stories_before == stories_after:
                return StuckReason.NO_PROGRESS

        # Same failure repeated
        recent_failures = [f for s in sessions[-3:] for f in s.failures]
        if self._has_repeated_failure(recent_failures):
            return StuckReason.REPEATED_FAILURE

        # Session keeps hitting budget cap before completing a story
        if all(s.exit_reason == "session_budget_reached" for s in sessions[-3:]):
            if not any(s.stories_completed for s in sessions[-3:]):
                return StuckReason.OVER_BUDGET

        # Spec has been in same state for > configured days
        days_in_state = (now() - spec.last_state_change).days
        if days_in_state > self.config.max_days_in_state:
            return StuckReason.STALE

        return None  # Not stuck
```

### 10.2 Escalation & Push Notifications

When a spec is stuck, the orchestrator pauses further sessions and notifies:

```python
async def handle_stuck_spec(self, spec: Spec, reason: StuckReason):
    # Stop scheduling this spec
    self.spec_queue.pause(spec.id)

    # Build diagnostic summary
    diagnostic = self.build_stuck_diagnostic(spec, reason)

    # Push notification via configured channels
    if self.config.notifications.teams_enabled:
        await self.teams.post_alert(
            channel=self.config.notifications.alert_channel,
            title=f"🚨 Spec {spec.id} is stuck: {reason.value}",
            body=diagnostic,
            actions=["Investigate", "Skip Story", "Abort Spec"]
        )

    if self.config.notifications.email_enabled:
        await self.email.send_alert(
            to=self.config.notifications.escalation_email,
            subject=f"Agent stuck on {spec.id}",
            body=diagnostic
        )

    # Log to audit
    self.audit.log_stuck(spec=spec, reason=reason, diagnostic=diagnostic)
```

### 10.3 Human Intervention Actions

After notification, humans can:

- **Investigate** — Read session summaries to understand the blocker, then adjust the spec
- **Add a guardrail** — If the agent keeps hitting the same problem, add a `GR-U*` guardrail
- **Skip story** — Mark a story as deferred and let the agent continue with the next one
- **Abort spec** — Move spec to `blocked` status with a reason
- **Adjust budget** — Increase per-session token budget if the stories are genuinely complex
- **Resume** — After fixing the issue, un-pause the spec for the next orchestrator cycle

---

## 11. Workspace Isolation Strategy

### 11.1 The Problem

If agents write directly to canonical lit-sdlc files (`roadmap.md`, `specs/index.yml`, `stories.yml`), a misbehaving agent could corrupt shared state. This is especially dangerous with multi-agent concurrency.

### 11.2 Copy-on-Write via Git Worktrees (Recommended)

Each agent session gets its own **git worktree** — an independent checkout of the repo. The agent reads and writes freely within its worktree. Changes only reach the canonical repo through a git merge (via PR).

```python
async def prepare_workspace(self, task: Task) -> Path:
    """Create an isolated worktree for the agent session."""
    branch = f"agent/{task.spec.slug}/{task.session_id}"
    worktree_path = self.workspaces / task.session_id

    # Create fresh branch from main
    git.branch(branch, from_ref="main")

    # Create worktree — full independent checkout
    git.worktree_add(worktree_path, branch)

    # Agent works entirely within this worktree
    return worktree_path

async def collect_results(self, worktree_path: Path, task: Task):
    """After session: commit, push, clean up worktree."""
    git.add_all(cwd=worktree_path)
    git.commit(f"agent: {task.describe()}", cwd=worktree_path)
    git.push(cwd=worktree_path)
    git.worktree_remove(worktree_path)
```

**Why worktrees?**

- Agents get full read-write access to their own copy — no permission juggling
- Canonical `main` branch is never directly written by an agent
- Multiple agents can work simultaneously on different branches without conflicts
- Standard git merge/PR flow for review and integration
- If an agent corrupts its worktree, discard it — no damage to canonical state

### 11.3 Phased Approach to Isolation

| Phase | Isolation Level | How |
|---|---|---|
| Phase 0 | Branches only | Agent works on a branch, commits and pushes. Simple but shared working directory. |
| Phase 1 | Git worktrees | Each agent gets its own worktree (independent filesystem checkout). |
| Phase 2 | Worktrees + Docker volumes | Worktree mounted as the container's `/workspace/`. Host repo untouched. |
| Phase 3 | Full isolation | Worktree created inside an ephemeral Docker volume. Agent never touches host filesystem. |

### 11.4 Serialized Merge Strategy

When multiple agents complete work concurrently (e.g., STORY-001 and STORY-002 in the same spec), the orchestrator **serializes merges** to prevent conflicts:

```python
async def merge_agent_work(self, result: SessionResult):
    """Orchestrator merges agent branch after validation.
    Serialized: only one merge at a time via asyncio.Lock."""

    async with self.merge_lock:
        # Only the orchestrator writes to canonical files
        if not result.validation.passed:
            self._release_story_claim(result)
            return

        # Attempt merge into main
        try:
            git.merge(result.branch, into="main", no_ff=True)
        except MergeConflict:
            # Rebase agent branch onto updated main and retry
            try:
                git.rebase(result.branch, onto="main")
                git.merge(result.branch, into="main", no_ff=True)
            except RebaseConflict:
                # Rebase failed — re-dispatch agent to fix
                await self._redispatch_for_conflict(result)
                return

        # Update spec index (orchestrator does this, not agent)
        self.update_spec_index(result.spec, result.new_status)

        # Update roadmap if spec completed
        if result.new_status == "complete":
            self.update_roadmap(result.spec)

async def _redispatch_for_conflict(self, result: SessionResult):
    """Re-dispatch an agent to resolve merge conflicts."""
    task = Task(
        type="resolve_conflict",
        spec=result.spec,
        story=result.story,
        skill="/continue-spec",
        context_extra=f"Your previous branch {result.branch} has merge "
                      f"conflicts with main. Rebase onto main and resolve.",
    )
    await self.dispatch(task)

    # If re-dispatch also fails → spec gets stuck → human notified
```

**Merge flow for concurrent stories:**

```
Agent A finishes STORY-001 → orchestrator merges to main ✓
Agent B finishes STORY-002 → orchestrator rebases B onto main (now includes 001)
  → If rebase succeeds → merge ✓
  → If rebase fails → re-dispatch Agent B with conflict context
    → If re-dispatch fails → spec stuck → human notified
```

This ensures agents never directly modify `specs/index.yml` or `roadmap.md` on the canonical branch — the orchestrator is the single writer.

---

## 12. Guardrail Architecture

### 12.1 Two-Layer Guardrail System

Guardrails operate at two levels, because some constraints are behavioral (the agent should follow them) and others are mechanical (the harness must enforce them regardless of agent behavior).

**Layer 1: lit-sdlc Guardrails (behavioral, in-prompt)**

These are the existing `GR-*` rules in `agent-os/standards/guardrails.md`. The agent receives them as part of its system prompt and is expected to follow them. They're "soft" in the sense that a misbehaving agent could ignore them.

Proposed additions to the existing unattended-mode guardrails:

```markdown
## Unattended Mode Guardrails (Extended)

### Existing (from lit-sdlc)
- GR-U01: Don't modify database schemas unattended
- GR-U02: Don't change spec requirements without approval
- GR-U03: Don't assume business logic — flag and document
- GR-U04: Don't make destructive changes
- GR-U05: Don't skip session summary
- GR-U06: Don't exceed scope of current story

### Proposed Additions
- GR-U07: Don't install new dependencies without documenting rationale
- GR-U08: Don't modify files outside your assigned spec's scope
- GR-U09: Don't bypass or disable tests to make stories "pass"
- GR-U10: Don't make more than 3 retry attempts on a failing approach
         — if it fails 3 times, document the failure and move on
- GR-U11: Write handoff summary before context budget reaches 80%
- GR-U12: Don't modify shared configuration files (CI configs,
         Dockerfiles, shared libraries) without flagging for review
```

**Layer 2: Harness Guardrails (mechanical, enforced by orchestrator)**

These are enforced by the orchestrator and container runtime regardless of agent behavior. The agent can't bypass them because they operate outside its execution context.

```python
class HarnessGuardrails:
    """Enforced by orchestrator — agent cannot bypass these."""

    # Pre-session checks
    BUDGET_CHECK = True          # Block launch if budget exceeded
    STUCK_CHECK = True           # Block launch if spec is stuck
    CONCURRENT_LIMIT = 3         # Max simultaneous agent sessions

    # Runtime enforcement
    BASH_ALLOWLIST = True        # Container-level command filtering
    NETWORK_POLICY = True        # Container-level network restrictions
    SESSION_TIMEOUT_MIN = 60     # Kill container after timeout
    TOKEN_BUDGET = 500000        # Graceful stop at token limit

    # Post-session validation
    REQUIRE_SESSION_SUMMARY = True   # Reject if no handoff artifact
    REQUIRE_TESTS_RUN = True         # Reject if tests weren't executed
    REQUIRE_CLEAN_GIT = True         # Reject if uncommitted changes
    MAX_FILES_MODIFIED = 50          # Flag if agent touched too many files

    # Three-tier file permissions (see Section 12.4)
    # Replaces a flat "forbidden" list with nuanced control
```

### 12.2 Guardrail Violation Handling

```python
async def handle_violation(self, violation: Violation):
    match violation.severity:
        case "warning":
            # Log and continue — review later
            self.audit.log_violation(violation)

        case "error":
            # Stop session, notify human
            await self.stop_session(violation.session)
            await self.notify(f"Guardrail violation: {violation}")
            self.audit.log_violation(violation)

        case "critical":
            # Kill container immediately, pause all work on this spec
            await self.kill_container(violation.session)
            self.spec_queue.pause(violation.spec_id)
            await self.notify(f"🚨 CRITICAL: {violation}", urgent=True)
            self.audit.log_violation(violation)
```

### 12.3 Self-Healing Guardrail Pipeline

When a session produces failures, the existing lit-sdlc "GOTCHA Self-Healing" table captures them. The autonomous platform adds an automated pipeline:

```
1. Agent session ends → /end-session produces failure table
2. Orchestrator reads failure table from session summary
3. For each failure:
   a. Check if a matching guardrail already exists
   b. If not, draft a new GR-U* rule
   c. Stage it for human review (don't auto-commit to guardrails.md)
   d. If human approves → add to guardrails.md, increment version
4. Next session automatically loads updated guardrails
```

This keeps humans in the loop for guardrail creation while automating the discovery and drafting process.

### 12.4 Three-Tier File Permission Model

Instead of a flat "forbidden files" list, files are classified into tiers that control how the orchestrator handles agent modifications:

```yaml
# config.yml — file permission tiers
file_permissions:
  # Tier 1: FORBIDDEN — Agent changes to these files are rejected outright
  forbidden:
    - agent-os/product/mission.md       # Mission is human-set
    - .github/workflows/*               # CI config is sensitive
    - Dockerfile*                        # Container config is sensitive
    - docker-compose*

  # Tier 2: PROPOSE ONLY — Agent can modify in its worktree, but
  # orchestrator routes changes to a separate approval PR instead
  # of auto-merging
  propose_only:
    - agent-os/standards/guardrails.md   # Guardrail changes need human review
    - agent-os/standards/best-practices.md
    - agent-os/product/roadmap.md        # Roadmap changes need human sign-off
    - agent-os/specs/index.yml           # Spec index is orchestrator-managed

  # Tier 3: AGENT WRITABLE — Normal PR flow, auto-merge if tests pass
  agent_writable:
    - agent-os/specs/SPEC-*/stories.yml  # Status field updates
    - agent-os/context/sessions/*        # Session summaries
    - agent-os/context/component-details/*
    - src/**                              # Source code
    - tests/**                            # Test code
```

**Orchestrator enforcement after session:**

```python
async def process_file_changes(self, result: SessionResult):
    """Route file changes through the appropriate tier."""
    for file in result.files_modified:
        tier = self.classify_file(file)

        match tier:
            case "forbidden":
                # Reject — revert this file, log violation
                git.checkout(file, ref="main", cwd=result.worktree)
                self.audit.log_violation(
                    type="forbidden_file", file=file, session=result.session_id)

            case "propose_only":
                # Extract change to a separate approval PR
                self._create_approval_pr(file, result)

            case "agent_writable":
                # Normal flow — included in the main merge
                pass
```

### 12.5 Three-Tier Skill Permission Model

The same pattern extends to skill/action permissions. Skills don't need to know about permissions — the orchestrator gates dispatch based on config:

```yaml
# config.yml — skill autonomy tiers
skill_permissions:
  # Human-only: never dispatched autonomously
  human_only:
    - /discover-standards            # Human convenience tool
    - /plan-product                  # Strategic direction is human-driven
    - /bootstrap                     # Onboarding is interactive

  # Propose-only: agent prepares the action, orchestrator holds
  # for human approval before executing
  propose_only:
    - /sync-confluence:publish       # Publishing docs needs review
    - /sync-jira:create-epic         # New work items need approval
    - /sync-github:auto-merge        # Auto-merging needs approval

  # Autonomous: agent and orchestrator can execute freely
  autonomous:
    - /start-session
    - /end-session
    - /shape-spec
    - /derive-acs
    - /generate-bdd-tests
    - /continue-spec
    - /investigate
    - /sync-github:create-pr         # PR itself is the review gate
    - /sync-jira:update-status       # Status updates are safe
    - /notify-teams:alert            # Sending alerts is safe
```

**Default tier for new skills:** `propose_only`. When you add a new skill, it starts gated until you've seen it work and promote it to `autonomous`. Safe by default.

**Colon notation for granularity:** `/sync-github:create-pr` is autonomous while `/sync-github:auto-merge` requires approval. A single skill can have mixed autonomy levels. The orchestrator does a prefix match.

**Proposed action artifacts:** For `propose_only` skills, the agent doesn't get API access. Instead, it writes a proposed action in its session output:

```yaml
# In the agent's handoff summary
proposed_actions:
  - skill: /sync-confluence:publish
    target: "SPEC-012 Design Doc"
    space: "Engineering"
    reason: "Spec complete, ready for team visibility"

  - skill: /sync-jira:create-epic
    target: "Automated Testing Framework"
    reason: "Identified during investigation, not on roadmap yet"
```

The orchestrator reads these, routes them to the approval queue (Teams/email), and only executes after human approval. The agent never had API access for these actions — it just expressed intent.

**Autonomy progression over time:**

| Phase | Model |
|---|---|
| Phase 0–1 | Only `autonomous` skills exist. No approval queue needed. |
| Phase 2 | Enterprise skills arrive as `propose_only`. Promote the safe ones after observation. |
| Phase 3 | Approval queue built for Teams. `propose_only` skills get their execution path. |
| Future | If conditional permissions (per-spec, time-based, role-based) become necessary, extend with an optional `scope` or `condition` field. Defer until a concrete need arises. |

---

## 13. Enterprise Integration Skills

New lit-sdlc skills that bridge between the kernel and enterprise tooling. Each is a standalone skill file in `.claude/skills/agent-os/`.

### 13.1 GitHub Integration (Priority 1)

**Skill: `/sync-github`**

```
Capabilities:
- Create feature branches from spec slugs (e.g., feat/SPEC-012-order-processing)
- Open PRs with spec context as description
- Link PRs to specs and stories
- Parse CI/CD results and update story status
- Handle review comments → feed back into next agent session
- Auto-merge when approved (configurable)

Trigger points in orchestrator loop:
- After agent session completes → create/update PR
- After CI passes → mark stories as passing
- After PR merged → update spec status, trigger next work
```

### 13.2 Confluence Integration (Priority 2)

**Skill: `/sync-confluence`**

```
Capabilities:
- Read existing architecture docs and domain knowledge
- Pull page content into lit-sdlc artifacts (component-details, domain/)
- Publish completed specs and design docs to Confluence spaces
- Update component documentation after implementation
- Maintain links between Confluence pages and lit-sdlc specs

Trigger points:
- At session start → pull latest Confluence context
- After spec completion → publish to Confluence
- After /investigate → update component docs
```

### 13.3 Jira Integration (Priority 3)

**Skill: `/sync-jira`**

```
Capabilities:
- Read Jira epics/stories → create matching lit-sdlc specs
- Map Jira ticket fields to spec metadata
- Update Jira status as stories pass/fail/complete
- Create sub-tasks in Jira for each lit-sdlc story
- Bi-directional sync: Jira changes → lit-sdlc updates
- Comment on Jira tickets with session summaries

Trigger points:
- On Jira webhook → create/update spec
- After story status change → update Jira
- After session end → comment summary on Jira ticket
```

### 13.4 Teams Integration (Priority 4)

**Skill: `/notify-teams`**

```
Capabilities:
- Post session summaries to configured channel
- Send approval requests for sensitive actions
- Alert on failures or stuck agents
- Daily digest of progress across all specs
- Interactive approval: team member replies "approve" → agent proceeds

Approval workflow:
1. Agent encounters sensitive action (e.g., schema change, new dependency)
2. Orchestrator pauses agent, posts approval request to Teams
3. Designated approver responds in Teams
4. Orchestrator resumes or aborts based on response
5. Timeout → abort and log
```

---

## 14. Phased Rollout

### Phase 0 — Foundation (Week 1–2)

**Goal**: Orchestrator can read lit-sdlc state and run a single Claude Code session on the host.

**Deliverables:**
- [ ] Orchestrator CLI in Python (`orchestrator run-cycle`)
- [ ] Roadmap parser + spec index reader
- [ ] Task selection algorithm
- [ ] Context builder (assembles prompt from lit-sdlc artifacts)
- [ ] Claude Code SDK integration (direct, no container yet)
- [ ] Basic audit logging (JSON lines to file)
- [ ] Simple cron trigger via systemd timer
- [ ] Git branch creation + commit per session
- [ ] Per-session token budget enforcement (graceful stop at limit)
- [ ] Enhanced `/end-session` with YAML frontmatter handoff format
- [ ] Enhanced `/start-session` with handoff resumption protocol

**Security**: Git-gated output, non-root execution, audit log, token budget.
**Value**: Agent autonomously picks up work and writes code overnight. Sessions resume cleanly.

### Phase 1 — Docker Isolation + GitHub (Week 3–4)

**Goal**: Agent runs in containers with proper isolation. PRs created automatically.

**Deliverables:**
- [ ] Dockerfile for agent runtime (Claude Code)
- [ ] Docker Compose setup with volume mounts
- [ ] Bash allowlist enforcement
- [ ] Volume permission model (RO skills, RW workspace, append-only audit)
- [ ] Git worktree isolation (each session gets its own checkout)
- [ ] `/sync-github` skill: branch → PR → CI status
- [ ] Session timeout and resource limits
- [ ] Per-day and per-spec cost budget enforcement
- [ ] Stuck spec detection (no-progress, repeated failure heuristics)
- [ ] Orchestrator validates test results before PR creation
- [ ] Harness guardrails: forbidden file patterns, max-files-modified check

**Security**: Container isolation, bash allowlist, resource limits, worktree isolation.
**Value**: Hands-off roadmap execution with PRs for review. Budgets prevent runaway costs.

### Phase 2 — Cursor + Confluence + Jira (Week 5–6)

**Goal**: Support Cursor as alternative driver. Enterprise integrations for context and tracking.

**Deliverables:**
- [ ] Cursor driver implementation (`cursor agent --print --force --output-format stream-json`)
- [ ] `.cursor/rules/` + `AGENTS.md` generation from lit-sdlc standards
- [ ] Agent selection in config (per-schedule or per-spec)
- [ ] `/sync-confluence` skill: read and publish docs
- [ ] `/sync-jira` skill: bi-directional ticket sync
- [ ] Network policy (Docker network with allowlisted endpoints + inter-container isolation)
- [ ] Secret management (tmpfs mounts, rotation)
- [ ] Monthly cost budgets with alerting
- [ ] Push notifications for stuck specs (Teams/email)

**Security**: Network restrictions (including inter-container), secret isolation.
**Value**: Works in both home (Claude) and work (Cursor) environments. Enterprise visibility.

### Phase 3 — Multi-Agent + Approvals (Week 7–8)

**Goal**: Multiple agents working concurrently with human-in-the-loop for sensitive actions.

**Deliverables:**
- [ ] Concurrent container orchestration (multiple specs in parallel)
- [ ] Story-level claiming with dependency DAG (addresses lit-sdlc GAP-004 + GAP-006)
- [ ] Full workspace isolation: worktrees inside ephemeral Docker volumes
- [ ] `/notify-teams` skill: notifications and approval queue
- [ ] Approval workflow: pause → request → resume/abort (with timeout handling)
- [ ] Event-driven scheduling (GitHub webhooks, Jira transitions)
- [ ] Serialized merge with re-dispatch on conflict
- [ ] Three-tier file permission model (forbidden / propose_only / agent_writable)
- [ ] Three-tier skill permission model with proposed action artifacts
- [ ] Anomaly detection (agent stuck, excessive failures, unusual commands)
- [ ] Self-healing guardrail pipeline (auto-draft GR-U* from failures)
- [ ] Dashboard / status page (simple HTML or CLI report)

**Security**: Approval queues, anomaly detection, full filesystem isolation, tiered permissions, kill switches.
**Value**: Full autonomous pipeline with human oversight where it matters. Story-level parallelism.

### Phase 4 — Self-Improving (Ongoing)

**Goal**: System learns and improves from its own operation.

**Deliverables:**
- [ ] Auto-guardrail generation from session failure tables
- [ ] Standards discovery from codebase patterns (`/discover-standards`)
- [ ] Complexity estimation for scheduling (small stories → batch, large → dedicated)
- [ ] Performance metrics: time-per-story, success rate, rework rate
- [ ] Adaptive scheduling: increase/decrease cadence based on backlog
- [ ] Cross-session learning: if approach X failed for Spec-012, don't repeat for Spec-015

---

## 15. Project File Structure

```
autonomous-agents-platform/
├── orchestrator/
│   ├── __init__.py
│   ├── main.py                 # CLI entrypoint
│   ├── orchestrator.py         # Core orchestration loop
│   ├── scheduler.py            # Cron + event scheduling
│   ├── task_selector.py        # Roadmap → task selection
│   ├── context_builder.py      # Assembles agent prompts
│   ├── container_manager.py    # Docker lifecycle
│   ├── validators.py           # Post-session validation
│   └── audit.py                # Append-only logging
│
├── drivers/
│   ├── __init__.py
│   ├── base.py                 # AgentDriver ABC
│   ├── claude_code.py          # Claude Code SDK driver
│   └── cursor.py               # Cursor CLI driver
│
├── integrations/
│   ├── __init__.py
│   ├── github_sync.py          # PR creation, CI status
│   ├── confluence_sync.py      # Doc read/publish
│   ├── jira_sync.py            # Ticket sync
│   └── teams_notify.py         # Notifications + approvals
│
├── docker/
│   ├── Dockerfile.claude-code  # Claude Code agent image
│   ├── Dockerfile.cursor       # Cursor agent image
│   ├── docker-compose.yml      # Container orchestration
│   ├── network-policy.yml      # Allowed endpoints
│   └── agent-runner.sh         # Container entrypoint
│
├── skills/                     # New lit-sdlc skills
│   ├── sync-github/
│   │   └── SKILL.md
│   ├── sync-confluence/
│   │   └── SKILL.md
│   ├── sync-jira/
│   │   └── SKILL.md
│   └── notify-teams/
│       └── SKILL.md
│
├── config/
│   ├── config.yml              # Main configuration
│   ├── schedules.yml           # Schedule definitions
│   ├── allowlist.yml           # Bash command allowlist
│   └── network-allowlist.yml   # Allowed network endpoints
│
├── tests/
│   ├── test_orchestrator.py
│   ├── test_task_selector.py
│   ├── test_drivers.py
│   └── test_integrations.py
│
└── docs/
    ├── architecture.md          # This document
    ├── security-model.md        # Detailed security docs
    └── runbook.md               # Operations guide
```

---

## 16. Key Design Decisions

### D1: Orchestrator runs on host, not in container

The orchestrator needs to manage Docker containers, read the full lit-sdlc artifact tree, and maintain state across sessions. Running it on the host keeps it simple and avoids container-in-container complexity. It's a thin Python process with minimal attack surface.

### D2: Ephemeral containers per session

Each agent session gets a fresh container. No state leaks between sessions. If an agent goes haywire, kill the container and the damage is contained. This is a core security property.

### D3: lit-sdlc artifacts are the source of truth

The orchestrator doesn't maintain its own database. It reads `roadmap.md`, `specs/index.yml`, and `stories.yml` directly. This means you can always `git log` to see the full history, and manual edits to lit-sdlc artifacts are immediately reflected in automation.

### D4: Git as the integration bus

All agent output goes through git branches and PRs. This provides natural review points, rollback capability, and audit trail. Enterprise integrations trigger off git events rather than custom APIs.

### D5: Two-layer guardrail system

Behavioral guardrails (GR-U01–U12 in lit-sdlc) are in-prompt — the agent should follow them. Mechanical guardrails (bash allowlist, network policy, forbidden file patterns) are enforced by the harness — the agent can't bypass them. Both layers are necessary because an agent could ignore soft guardrails.

### D6: Orchestrator is the single writer to canonical state

Agents never directly update `specs/index.yml`, `roadmap.md`, or other shared state on the main branch. The orchestrator merges agent work via PRs and updates canonical state itself. This prevents race conditions and corruption from concurrent agents.

### D7: Session continuity via structured artifacts, not SDK memory

Handoff artifacts (enhanced session summaries with YAML frontmatter) are the "save game" format. Any agent — Claude Code, Cursor, or future tools — can read them on startup and resume work. No vendor lock-in to a specific SDK's session management.

### D8: Three-tier permission model for files and skills

Files and skill actions are classified as `forbidden`, `propose_only`, or `autonomous` via config — not code. New skills default to `propose_only` (safe by default). The orchestrator enforces tiers: forbidden changes are reverted, propose_only changes route to approval PRs, autonomous changes merge normally. This avoids building a full permission framework while providing granular control that extends naturally as new skills are added.

### D9: Story-level parallelism with dependency DAG

Task selection operates at story granularity, not spec granularity. Stories declare `depends_on` relationships forming a DAG. The orchestrator dispatches independent stories in parallel and serializes merges. This maximizes throughput while preventing agents from stepping on each other's work.

### D10: Separate driver work tracks

Claude Code and Cursor drivers are developed and verified independently. Claude Code is the primary track, developed and tested on the dedicated host. Cursor is the secondary track, validated at work where the license is available. Both share everything except the driver layer — same orchestrator, same lit-sdlc kernel, same worktree isolation, same enterprise integrations. The `AgentDriver` interface (Section 5.1) is the abstraction boundary.

---

## 17. Open Questions

1. ~~**Cursor headless mode**~~ **RESOLVED** — Cursor CLI supports `cursor agent "prompt" --print --force --output-format stream-json` for full headless execution. Service accounts available for enterprise. Background agents provide cloud-based execution as an alternative path.

2. ~~**Session continuity**~~ **RESOLVED** — Agent-agnostic handoff via enhanced lit-sdlc session summaries with YAML frontmatter (Section 8). No SDK dependency.

3. ~~**Cost management**~~ **RESOLVED** — Budget hierarchy with per-session, per-day, per-spec, and monthly caps with alerting (Section 9).

4. ~~**Conflict resolution**~~ **RESOLVED** — Orchestrator serializes merges via `asyncio.Lock`. Second agent's branch is rebased onto updated main. If rebase fails, agent is re-dispatched with conflict context. If re-dispatch also fails, spec gets stuck and human is notified (Section 11.4).

5. **Rollback strategy** — If an agent produces bad work that gets merged, what's the recovery path? Git revert is mechanical, but how do we update lit-sdlc state to reflect the rollback? Need a `/rollback-spec` skill.

6. **Credential rotation** — API keys and tokens in container secrets need rotation. How often, and how to handle mid-session rotation? Could use a secrets sidecar that refreshes tokens without restarting the agent.

7. **Cursor in Docker** — While Cursor CLI works headless, it may have licensing or dependency requirements that complicate containerization. Need to test: does `cursor agent --print` work in a headless Ubuntu container without a display server? The `CURSOR_API_KEY` env var and service accounts suggest yes, but needs validation.

8. **Observability tooling** — Phase 3 dashboard needs more definition. Should we build a custom UI, use Grafana with structured logs, or keep it CLI-only?

---

## 18. Success Criteria

- **Phase 0**: Agent autonomously picks up a spec and produces a meaningful commit overnight.
- **Phase 1**: A full spec goes from `in_requirements` → `complete` with a merged PR, no human intervention during execution.
- **Phase 2**: Same workflow works with both Claude Code and Cursor drivers.
- **Phase 3**: Multiple stories executing in parallel across specs, with Teams approval for a `propose_only` skill action. Serialized merge handles a conflict without human intervention.
- **Phase 4**: System suggests a new guardrail based on a session failure, and the guardrail prevents the same failure in a subsequent session.
