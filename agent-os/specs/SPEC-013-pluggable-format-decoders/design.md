# SPEC-013: Raw Content By-Value Ingestion — Design

> **Status: DEFERRED / future.** No detailed design until scheduled. This file intentionally stays a stub; see `README.md` for scope and the rejected-design rationale.

## Summary

Raw content by-value ingestion is a **small delta** over the existing raw/extract path:

- Today: `ingest_documents(uris)` → the pipeline **fetches** each URI → the matching plugin(s) (by `semantic_type`) decode + refine.
- Added here: an item may carry `{uri, content, media_type}`; when `content` is present the pipeline uses it **directly** (no fetch). `uri` stays the identity key. Everything downstream — decode, interpret, write — is unchanged and stays **in the plugin**.

## Rejected direction (recorded so we don't rediscover it)

A framework-owned `ContentDecoder`/`DecoderRegistry` producing a canonical structure for plugins was **dropped**: there is no universal intermediate representation, and a framework decoder is either a valueless wrapper over an existing library or a smuggled-in intermediate format. Decode and interpret both remain the plugin's responsibility, using standard Python libraries. The framework only **delivers bytes and routes** (by `semantic_type`).

## Execution Plan

To be written when the spec is scheduled. Anticipated surface is small: extend the `ingest_documents` item shape to accept `{uri, content?, media_type?}`, thread inline content through the bundle so plugins receive it instead of fetching, and require `media_type` when `content` is present.
