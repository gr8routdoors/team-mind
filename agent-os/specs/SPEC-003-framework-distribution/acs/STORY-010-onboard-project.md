# STORY-010: /onboard-project skill — Acceptance Criteria

## AC-001: Content ingestion

**Given** a user has existing documentation (Confluence pages, Google Docs, markdown files, etc.)
**When** the user runs `/onboard-project`
**Then** the skill walks the user through identifying their documentation sources
**And** accepts content via copy/paste, file upload, or URL
**And** categorizes each piece into the four Lit SDLC layers (product, standards, context, specs)

## AC-002: Content quality assessment

**Given** content has been ingested
**When** the skill assesses each piece
**Then** it evaluates: is this a requirement, solution design, domain knowledge, or standard?
**And** evaluates: is it current or stale? well-specified or vague? complete or has gaps?
**And** presents a quality scorecard to the user
**And** the user decides what to keep, rewrite, or discard

## AC-003: Guided content transformation

**Given** the user has approved content for transformation
**When** the skill transforms content
**Then** it extracts mission from vision docs into `product/mission.md`
**And** derives business rules from requirements into `product/domain/business-rules.md`
**And** identifies domain terminology into `product/domain/terminology.md`
**And** captures architectural decisions into `context/architecture/`
**And** presents each draft for user approval before writing

## AC-004: Existing feature mapping

**Given** the project has existing features not tracked as specs
**When** the user describes existing features
**Then** the skill creates retroactive spec stubs documenting what exists
**And** marks them as `complete` (already built, just documenting)

## AC-005: Gap analysis

**Given** content ingestion and transformation are complete
**Then** the skill identifies what's missing (e.g., mission but no terminology, architecture but no business rules)
**And** generates a prioritized onboarding backlog
**And** suggests next steps for filling gaps
