# Future: Operating Profiles

> How operating profiles will enhance the Developer Workflow skills once implemented. This document is **informational only** — none of this is in scope for SPEC-002.

---

## What Are Operating Profiles?

Operating profiles are a configuration mechanism that lets teams tune Lit SDLC's behavior to match their workflow. A single `operating_profile` setting in AGENTS.md controls how skills behave:

| Profile | Target Audience | Behavior |
|---------|----------------|----------|
| **full** | Solo dev or AI-heavy teams | Subagent per story, two-stage agent review, full verification ritual, auto-create PRs (human merges) |
| **team** | Teams with human PR review | Single agent, skip agent-to-agent review (humans review PRs), full verification |
| **lean** | Experienced teams with strong CI | Single agent, no agent review, lighter verification (tests pass + build succeeds) |

Anti-rationalization tables and hard gates remain enforced in **all** profiles. Profiles only affect optional quality layers.

## How Profiles Would Enhance /commit

- **full**: Could enable auto-commit (skip human review of commit message) since the two-stage review catches issues later
- **team/lean**: Commit message always presented for review (current behavior) since there's less agent oversight downstream

## How Profiles Would Enhance /ship-pr

- **full**: Auto-create PR without waiting for approval; human must review and merge
- **team/lean**: Prepare PR but present summary and wait for explicit human approval before creating
- **autonomous** (Phase 5): Auto-create PR; auto-merge may be enabled with CI integration

## How Profiles Would Affect Existing Skills

- `/dispatch-subagents`: In team/lean, execute stories inline (no fresh subagent per story)
- `/request-code-review`: In team/lean, skip agent-to-agent review entirely
- `/verify-completion`: In lean, perform lighter verification (confirm tests pass, skip evidence-gathering ritual)

## Configuration Design

Added to AGENTS.md:

```yaml
## Operating Profile
# Options: full | team | lean
# See agent-os/product/domain/terminology.md for profile descriptions
operating_profile: full
```

Skills read this at the start of their workflow. The profile is a simple string match — no complex configuration needed. Defaults to `full` if not specified.

## Implementation Path

Operating profiles will be implemented as a separate spec (likely SPEC-004 or later). The work breaks into:

1. **Profile configuration** — Define the setting in AGENTS.md, document in terminology.md, establish a consistent reading pattern for all skills
2. **Profile-aware skill updates** — Update dispatch-subagents, request-code-review, and verify-completion to check profile and adjust behavior
3. **Profile-aware shipping** — Add profile checks to /ship-pr for auto-create vs wait-for-approval

## Design Decisions (Preserved)

| Decision | Options Considered | Rationale |
|----------|-------------------|-----------|
| Profile config in AGENTS.md | AGENTS.md vs separate config file vs env var | AGENTS.md is already the project-specific config file agents read first; adding a profile setting there keeps everything in one place |
| Three profiles (full/team/lean) | Two (full/lean) vs three vs continuous slider | Three covers the main use cases cleanly: solo dev, team with PR review, experienced team with strong CI |
| Simple string vs granular toggles | String vs individual feature flags | String is simpler to configure and understand; granular toggles create combinatorial complexity |

---

_This document preserves intent from the SPEC-002 shaping session. It is not an active spec._
