# Product Mission

## Problem

AI coding agents (Claude, Cursor, Copilot) are powerful but unreliable without structure. They forget context between sessions, ignore project conventions, skip testing, rationalize away good practices, and declare work "done" without verification. Teams adopting AI-assisted development face a paradox: the agent can write code fast, but without guardrails the code is wrong, inconsistent, or incomplete.

## Target Users

Software developers and teams using AI coding agents (primarily Claude Code and Cursor) who want to:
- Maintain engineering discipline while leveraging AI speed
- Preserve knowledge across sessions so agents don't start from scratch
- Enforce consistent conventions without manual oversight
- Scale from solo developer to multi-agent workflows

## Solution

Lit SDLC provides a lightweight, file-based framework that structures the entire software development lifecycle for AI agents. It separates **declarative standards** (conventions the agent must follow) from **procedural skills** (step-by-step workflows the agent executes), layered on top of **persistent product context** (mission, roadmap, domain knowledge) and **session memory** (learnings, decisions, component knowledge that survives across conversations).

The framework is self-reinforcing: agents that follow the process produce better results, which builds trust, which justifies giving agents more autonomy.

## Key Differentiators

- **Drop-in, file-based**: No runtime dependencies. Just markdown and YAML files in your repo.
- **Standards + Skills separation**: Conventions are independently managed, tagged, and selectively injectable.
- **Session continuity**: Structured session summaries bridge knowledge across conversations.
- **Spec-driven development**: Features flow from specs through acceptance criteria to BDD test scaffolding.
- **Discipline enforcement**: Anti-rationalization tables, hard gates, and verification requirements prevent agents from cutting corners.
- **Self-documenting**: The framework uses itself to manage its own development (this repo is a working example).
