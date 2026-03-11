# Tech Stack

> Approved technologies and infrastructure for this project.

---

## Architecture

At its core, the system acts as an **MCP (Model Context Protocol) Server**, providing a standardized toolset for AI agents to interact with the knowledge base.

## Backend / Core Language
**Python**
- **Why:** Python is the undisputed king of ML, embeddings, and NLP pipelines. While Go is incredibly fast and great for static binaries, Python provides zero-friction access to `sentence-transformers`, `langchain`, and local models (like Ollama). For an MVP that relies heavily on vector processing and LLM-as-a-judge validation, Python will drastically reduce development time.
- **Components:** `mcp` (official Python SDK for writing the server).

## Database / Storage
**Abstracted Storage Layer (Starting Embedded)**
- **MVP (Phase 1):** **SQLite (with `sqlite-vec` + JSON extensions)**. Modern SQLite is incredibly powerful. It provides native JSON document views (allowing us to store arbitrary, schema-less plugin metadata just like MongoDB) alongside specialized vector math extensions for semantic search. This provides a robust, zero-deployment relational/document hybrid database entirely in-process. 
- **Scale (Phase 3):** **MongoDB Community Edition (Self-Hosted)**. Once the abstraction layer is proven and the enterprise team scales, migrating from SQLite JSON to MongoDB provides identical document flexibility with the added benefits of distributed horizontal scaling and heavy concurrent write handling.

## Frontend (Future Phase)
**Lightweight JavaScript Framework**
- Vue.js or Svelte (TBD, prioritizing high developer velocity and low boilerplate).

## AI / Language Models
- **Embeddings:** Local embedding models (e.g., `sentence-transformers` / `all-mpnet-base-v2`) to maintain privacy and reduce api costs.
- **LLM / Critic:** Claude or local Ollama instances for the "Validation Gate" and extraction pipelines.

---

_Last updated: 2026-03-10_
