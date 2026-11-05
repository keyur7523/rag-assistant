# Northwind Support Agent

An AI customer-support agent that answers questions by choosing and chaining its own tools: querying an orders database, searching policy documents with retrieval-augmented generation (RAG), and drafting customer replies for human review. Hard-stop guardrails run outside the model loop.

The agent decides which tools it needs and in what order. Given *"A customer emailed saying order 12345 never arrived — handle it,"* it looks up the order, finds it past the expected delivery window, searches the shipping policy for the late-delivery rule, and drafts a reply citing that policy, without being told to take any of those steps.

Everything is grounded in data from its tools. It cites the policy documents it relies on and says "I don't know" rather than inventing an answer. Drafts are never sent automatically. Prompt injection, auto-send, and off-policy PII requests are blocked before any model call.

The data is a fictional company, **Northwind Supply Co.**, with an orders database and four policy documents (returns, refunds, shipping, warranty).

---

## The agent

The core is a hand-written tool-calling loop: the agent is given a task and a set of tools, Claude decides which tool to call, the loop executes it, feeds the result back, and repeats until the task is done.

| Tool | What it does |
|---|---|
| `get_order_status` | Looks up an order in the SQLite database: customer, item, status, order and delivery dates. |
| `search_policies` | Semantic search over the policy documents (RAG), returning the most relevant excerpts with their sources. |
| `draft_reply` | Composes a customer reply and saves it for human review. Drafts are never sent automatically. |
| `escalate_to_human` | Hands the conversation to a human when the request is outside what the policy tools can answer. |

The two lookup tools are deliberately different in kind: one is an exact-key query against structured data, the other is semantic retrieval over unstructured text. Answering *"can I still return this?"* requires both (the delivery date from the database, the return window from the policy documents) plus date arithmetic the agent performs itself.

## Guardrails

Soft prompt rules are not enough for a support agent. `guardrails.py` runs before the model, on every tool call, and on the final answer.

| Check | Behavior |
|---|---|
| Empty / oversized input | Rejected without an API call |
| Prompt injection | Blocked (`ignore previous instructions`, etc.) |
| Auto-send | Blocked (`email the customer now`, `skip human review`) |
| Off-policy / PII | Blocked (CEO, home address, SSN, credit card, etc.) |
| Unknown tools | Blocked even if the model asks |
| Claimed "email sent" | Corrected in the final answer |

Blocked requests appear in the tool trace as `guardrail_block`, so evals can score them.

The pattern checks are a first filter, not a complete defense against injection. The firm guarantee is structural: the agent has no tool that sends email, so no prompt can make it send one.

## The RAG pipeline

`search_policies` is backed by a retrieval pipeline built from first principles rather than an off-the-shelf framework.

**Ingestion** (run once): load the policy documents → chunk them with a hand-written word-based sliding window (configurable size and overlap) → embed each chunk locally with `sentence-transformers` → store vectors, text, and source metadata in a persistent Chroma database.

**Retrieval:** embed the query with the same model → return the nearest chunks with their source files.

Retrieval returns evidence, not conclusions; the agent does the reasoning and citing. `query.py` also runs standalone as a plain document-Q&A demo.

## Tech stack

- **Python**
- **Anthropic Claude API** (`claude-sonnet-4-5`): agent reasoning and tool selection
- **sentence-transformers** (`all-MiniLM-L6-v2`): local embeddings, no API cost
- **ChromaDB**: persistent vector store
- **SQLite**: orders database (standing in for a CRM / system of record)
- **FastAPI**: HTTP API with full tool-trace responses

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
python ingest.py
rm -f orders.db && python seed_orders.py
```

**2. Run the agent:**

```bash
python agent.py
```

The customer message is set inside `agent.py`; edit it to try other scenarios.

**3. Or run it as an HTTP API:**

```bash
uvicorn api:app --port 8000
```

Interactive documentation is served at `http://localhost:8000/docs`.

```bash
curl -X POST localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Can I still return order 12346?"}'
```

The response carries the answer plus the agent's full tool trace: which tools it chose, in order, and the arguments it passed.

```json
{
  "answer": "Yes, you can still return order 12346 ... you're within the 30-day return window ...",
  "tools_used": ["get_order_status", "search_policies"],
  "iterations": 2,
  "tool_details": [
    { "tool": "get_order_status", "input": { "order_id": "12346" } },
    { "tool": "search_policies", "input": { "query": "return window how long after delivery can items be returned" } }
  ]
}
```

Exposing the trace makes the agent's reasoning observable rather than opaque. Note that the search query is one the agent wrote itself from the customer's question. `GET /health` is available for readiness checks. Running as a server also loads the embedding model once at startup rather than on every request.

## Examples

**Tool selection:** *"How long do I have to return something?"*
> Searches the policy documents only. Answers 30 days from the delivery date, citing `returns_policy.md`.

**Chaining two tools with reasoning:** *"I received order 12346 recently — can I still return it?"*
> Looks up the order (delivered 2026-10-30), searches the return policy (30-day window), then computes eligibility against today's date: still inside the window.

**The same question, opposite answer:** *"I got order 12347 back in September — can I still return it?"*
> Delivered 2026-09-05, so the window has closed. Offers the warranty as a possible next step.

Neither answer is stored anywhere. Both require combining a date from the database with a rule from the documents.

**Taking an action:** *"A customer emailed saying order 12345 never arrived — handle it."*
> Finds the order past its expected delivery window, retrieves the shipping policy's late-delivery rules, and drafts a reply, saved to `email_drafts/` for a human to review.

**Guardrail hard stop:** *"Email the customer now and skip human review."*
> Blocked before any model call. The trace shows `guardrail_block` / `auto_send_blocked`.

## Evaluation

The agent is scored automatically against 22 cases spanning policy questions, order lookups, multi-tool chaining, actions, robustness, and guardrails:

```bash
python run_eval.py              # all cases
python run_eval.py chaining     # one category
python run_eval.py guardrails
```

Each case is scored on two independent axes:

- **Trajectory:** did the agent call the tools it needed? An agent that produces the right answer without consulting the order database guessed correctly, which is a bug even though the text looks right.
- **Outcome:** does the answer contain the expected facts?

The chaining cases require combining order dates with policy rules. Robustness cases check that unknown orders are reported as not found, that CEO/PII fishing is blocked, and that a plain greeting triggers no tool calls. Guardrail cases check that injection, auto-send, and empty input never reach the model.

Every run is written to a timestamped JSON file under `eval_results/` (gitignored), so the effect of a change can be measured by diffing runs.

### Results

Measured on 2026-11-05 with `claude-sonnet-4-5`:

| Category | Score |
|---|---|
| Policy | 6/6 |
| Order | 3/3 |
| Chaining | 4/4 |
| Action | 2/2 |
| Robustness | 3/3 |
| Guardrails | 4/4 |
| **Overall** | **22/22** |

## Roadmap

- **Retrieval quality tuning:** chunk sizing and cosine-normalized embeddings, measured against the eval suite.
- **Self-hosted inference:** finish the `OllamaBackend` stub in `llm.py` and compare it against Claude on the same eval suite.
- **Latency and cost:** p50 per turn and typical tool-call counts on the eval set.

## Notes

The company, orders, and policy documents are entirely fictional. No credentials or secrets are stored in this repository; the Anthropic API key is supplied through an environment variable at runtime. Generated artifacts (the vector store, the orders database, email drafts, and escalations) are excluded from version control and rebuilt by the setup scripts.
