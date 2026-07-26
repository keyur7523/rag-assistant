# RAG Assistant

A retrieval-augmented generation (RAG) pipeline built from scratch — chunk → embed → vector search → cited answers from Claude — over an enterprise policy knowledge base. This is the foundation for a planned multi-agent tool-calling system.

## Overview

Enterprise document Q&A: ingest policy documents, retrieve the most relevant passages by semantic similarity, and have Claude answer grounded in those passages with source citations. The knowledge base is a fictional company's (**Northwind Supply Co.**) returns, refund, shipping, and warranty policies.

Built deliberately from first principles — the chunker, embedding flow, and vector-store wiring are hand-written rather than pulled from a higher-level framework — as a learning and portfolio project.

## Architecture

**Ingestion (offline, run once):**
1. **Load** — read policy markdown from `docs/`
2. **Chunk** — hand-written word-based sliding window (configurable chunk size and overlap)
3. **Embed** — `sentence-transformers` (`all-MiniLM-L6-v2`, 384-dim), runs locally, no API cost
4. **Store** — persistent Chroma vector database (`db/`), with source metadata attached for citations

**Query (online):**
1. **Embed** the question with the same model
2. **Retrieve** the top-k nearest chunks from Chroma
3. **Augment** a prompt with the retrieved chunks
4. **Generate** a cited answer with Claude

## Tech stack

- Python
- Anthropic Claude API (`claude-opus-4-8`)
- `sentence-transformers` — local embeddings
- ChromaDB — persistent vector store

## Project structure

```
docs/               Fictional Northwind Supply Co. policy documents (the corpus)
stage0_hello.py     Stage 0 — a single Claude API call
stage1_ingest.py    Stage 1 — load, chunk, embed, and store the corpus
requirements.txt    Dependencies
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here
```

The API key is read from the environment only — it is never committed (`.env` is gitignored).

## Usage

```bash
python stage1_ingest.py
```

This loads the policy documents, chunks and embeds them, and populates the local Chroma vector store.

## Status & roadmap

- [x] **Stage 0** — Claude API hello
- [x] **Stage 1 (ingestion)** — chunk, embed, and store the corpus
- [ ] **Stage 1 (query)** — retrieval + cited generation
- [ ] **Stage 2** — multi-tool agent (SQLite CRM lookup, document search, action tool)
- [ ] **Stage 3** — evaluation harness + FastAPI deployment
- [ ] **Stage 4** — self-hosted open model + local fine-tune

## Notes

The document corpus is entirely fictional. No credentials or secrets are stored in this repository; the Anthropic API key is supplied via an environment variable at runtime.
