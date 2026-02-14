# Business Rules

> Constraints and rules governing how the Lit SDLC framework operates. Non-negotiable unless explicitly changed by the project owner.

---

## Spec Rules

- **BR-S01**: All significant work must have a spec before implementation begins.
- **BR-S02**: Specs progress in order: `in_requirements` → `in_design` → `in_progress` → `complete` → `archived`.
- **BR-S03**: Agents can only modify `status` and `verified_by` in stories.yml. Cannot add or remove stories.
- **BR-S04**: A spec is `complete` only when all stories are `passing` and verification criteria are met.

## Standards Rules

- **BR-ST01**: Guardrails always apply (tagged `[all]`, never filtered out).
- **BR-ST02**: Standards are injected by tag; only matching standards are loaded.
- **BR-ST03**: Skill descriptions must follow CSO rules: triggering conditions only, no workflow summaries.

## Session Rules

- **BR-SE01**: Every working session begins with `/start-session`.
- **BR-SE02**: Significant work ends with `/end-session` for context preservation.
- **BR-SE03**: Unattended sessions require comprehensive summaries with all assumptions documented.

## Verification Rules

- **BR-V01**: No completion claims without fresh verification evidence.
- **BR-V02**: Code review requires two stages in order: spec compliance, then code quality.
- **BR-V03**: Spec compliance must pass before code quality review begins.

## Unattended Mode Rules

- **BR-U01**: No database schema modifications.
- **BR-U02**: No changes to spec requirements or acceptance criteria.
- **BR-U03**: Business logic must not be assumed; document and flag for review.
- **BR-U04**: No destructive changes.
- **BR-U05**: Session summary is mandatory.
- **BR-U06**: Agent must not exceed assigned scope.
