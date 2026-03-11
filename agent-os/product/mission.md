# Product Mission

## Problem

Information scatter across large teams and sub-teams. Vital engineering knowledge, architectural decisions, and technical artifacts become quickly outdated because teams move fast and document systems like Confluence become messy. Currently, there is no single, prioritized source of truth for AI agents or engineers to retrieve accurate, high-utility enterprise knowledge efficiently.

## Target Users

1. **Strike Teams / Individual Engineers:** Starting small as an intelligent, local memory assistant.
2. **AI Agents / LLMs:** Seeking token-optimized, high-signal context for automated coding and answering.
3. **Enterprise Teams:** Scaling to support large engineering organizations with secure, cross-team knowledge sharing and integrations (e.g., MS Teams).

## Solution

An intelligent, "learning" knowledge base (a Team Mind) that goes beyond standard RAG. It features:
- **Usage-Based Reliability:** An organic truth system where information value decays over time or increases based on positive usage (RLHF-style weighting).
- **Token Optimization:** Efficiently serves only the most relevant, high-quality context to AI agents.
- **Multi-Source Ingestion:** Seamlessly consumes Markdown (human-editable) and meeting transcripts.
- **Validation Gates:** Prevents the "misinformation domino effect" by vetting ingested facts against established "golden docs."

## Key Differentiators

Unlike a static wiki or a simple vector store, this system has a **Memory Weighting Strategy**. It acts as a Librarian rather than just a Searcher—automatically promoting high-utility facts, tracking source authority, detecting contradictions upon ingestion, and decaying outdated information.
