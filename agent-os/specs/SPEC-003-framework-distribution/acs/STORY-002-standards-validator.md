# STORY-002: Standards index validator — Acceptance Criteria

## AC-001: Detect missing standard files

**Given** `standards/index.yml` references `standards/nonexistent.md`
**When** `tools/validate_standards.py` is run
**Then** it reports the missing file with path and index entry name

## AC-002: Detect orphaned standard files

**Given** `standards/extra.md` exists but is not referenced in `index.yml`
**When** `tools/validate_standards.py` is run
**Then** it reports the orphaned file

## AC-003: Validate tag syntax

**Given** a standard entry in `index.yml` has tags: `[coding, invalid tag with spaces]`
**When** `tools/validate_standards.py` is run
**Then** it reports the invalid tag format

## AC-004: Clean validation pass

**Given** all standards in `index.yml` reference existing files with valid tags and no orphans exist
**When** `tools/validate_standards.py` is run
**Then** it exits with code 0 and reports "All standards valid"
