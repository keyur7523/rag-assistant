# Northwind Support Agent

An AI customer-support agent that answers questions by **choosing and chaining its own tools** — querying an orders database, searching policy documents with retrieval-augmented generation (RAG), and drafting customer replies for human review.

The agent decides which tools it needs and in what order. Given *"A customer emailed saying order 12345 never arrived — handle it,"* it looks up the order, discovers it's 19 days overdue, searches the shipping policy for the late-delivery rule, and drafts a reply citing that policy — without being told to take any of those steps.

Everything is grounded in real data from its tools. It cites the policy documents it relies on, and says "I don't know" rather than inventing an answer.

The data is a fictional company — **Northwind Supply Co.** — with an orders database and four policy documents (returns, refunds, shipping, warranty).

## The agent

The core is a hand-written **tool-calling loop**: the agent is given a task and a set of tools, Claude decides which tool to call, the loop executes it, feeds the result back, and repeats until the task is done.

| Tool | What it does |
| --- | --- |
| `get_order_status` | Looks up an order in the SQLite database — customer, item, status, order and delivery dates. |
| `search_policies` | Semantic search over the policy documents (RAG), returning the most relevant excerpts with their sources. |
| `draft_reply` | Composes a customer reply and saves it for human review. Drafts are never sent automatically. |

The two lookup tools are deliberately different in kind: one is an **exact-key query** against structured data, the other is **semantic retrieval** over unstructured text. Answering a question like *"can I still return this?"* requires both — the delivery date from the database, the return window from the policy documents — plus date arithmetic the agent performs itself.

## The RAG pipeline

`search_policies` is backed by a retrieval pipeline built from first principles rather than an off-the-shelf framework:

**Ingestion** (run once): load the policy documents → chunk them with a hand-written word-based sliding window (configurable size and overlap) → embed each chunk locally with `sentence-transformers` → store vectors, text, and source metadata in a persistent Chroma database.

**Retrieval**: embed the query with the same model → return the nearest chunks with their source files.

Retrieval returns *evidence*, not conclusions — the agent does the reasoning and citing. `query.py` also runs standalone as a plain document-Q&A demo.

## Tech stack

- **Python**
- **Anthropic Claude API** (`claude-opus-4-8`) — agent reasoning and tool selection
- **sentence-transformers** (`all-MiniLM-L6-v2`) — local embeddings, no API cost
- **ChromaDB** — persistent vector store
- **SQLite** — orders database (standing in for a CRM / system of record)

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here
```

The API key is read from the environment only and is never committed.

**1. Build the data stores** (run once):

```bash
python ingest.py        # chunks and embeds the policy documents into Chroma
python seed_orders.py   # creates and seeds the SQLite orders database
```

**2. Run the agent:**

```bash
python agent.py
```

The customer message is set inside `agent.py`; edit it to try other scenarios.

## Examples

**Tool selection** — *"How long do I have to return something?"*
> Searches the policy documents only. Answers *30 days from the delivery date*, citing `returns_policy.md`.

**Chaining two tools with reasoning** — *"I got order 12346 last week — can I still return it?"*
> Looks up the order (delivered 2026-07-18), searches the return policy (30-day window), then computes: the window runs to 2026-08-17, so 9 days in — still eligible.

**The same question, opposite answer** — *"I got order 12347 in June — can I still return it?"*
> Delivered 2026-06-08, so the window closed 2026-07-08 — no longer returnable. It offers to check the warranty policy instead.

Neither answer is stored anywhere. Both require combining a date from the database with a rule from the documents.

**Taking an action** — *"A customer emailed saying order 12345 never arrived — handle it."*
> Finds the order 19 days overdue, retrieves the shipping policy's late-delivery and lost-package rules, and drafts a reply offering a reshipment or a full refund — saved to `email_drafts/` for a human to review.

## Roadmap

- **Evaluation harness** — a test set of agent tasks with automatic scoring of whether each was completed correctly.
- **Retrieval quality tuning** — chunk sizing and cosine-normalized embeddings, measured with before/after retrieval tests.
- **HTTP API** — expose the agent over FastAPI.
- **Self-hosted inference** — run an open model locally alongside the Claude API.

## Notes

The company, orders, and policy documents are entirely fictional. No credentials or secrets are stored in this repository; the Anthropic API key is supplied via an environment variable at runtime. Generated artifacts — the vector store, the orders database, and email drafts — are excluded from version control and rebuilt by the setup scripts.
