# RAG Assistant

Ask natural-language questions over a company's policy documents and get answers **grounded in the source text, with citations** — powered by retrieval-augmented generation (RAG).

Instead of relying on a language model's training data (which can't know your documents and may hallucinate), this system retrieves the passages most relevant to a question and has Claude answer *only* from those passages — citing which document each answer came from, and saying "I don't know" when the answer isn't in the corpus.

The knowledge base is a fictional company's (**Northwind Supply Co.**) returns, refund, shipping, and warranty policies.

## How it works

**Building the knowledge base:**
1. **Load** policy documents from `docs/`.
2. **Chunk** each document into overlapping passages using a hand-written word-based sliding window.
3. **Embed** every chunk into a vector with a local `sentence-transformers` model — no API cost.
4. **Store** the vectors, chunk text, and source metadata in a persistent Chroma database.

**Answering a question:**
1. **Embed** the question with the same model.
2. **Retrieve** the most semantically similar chunks from the vector store.
3. **Assemble** the retrieved passages into a context block, labeled with their source files.
4. **Generate** an answer with Claude, constrained to the retrieved context and required to cite its sources.

The retrieval and embedding layers are built from first principles — a custom chunker and direct vector-store wiring — rather than an off-the-shelf RAG framework, to keep the internals transparent and under my control.

## Tech stack

- **Python**
- **Anthropic Claude API** (`claude-opus-4-8`) — grounded answer generation
- **sentence-transformers** (`all-MiniLM-L6-v2`) — local text embeddings
- **ChromaDB** — persistent vector store with metadata

## Getting started

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key-here
```

The API key is read from the environment only and is never committed.

**1. Build the vector store** (run once, ingests the documents):

```bash
python ingest.py
```

**2. Ask a question:**

```bash
python query.py
```

The question is set inside `query.py`; edit it to ask something else.

## Example

**In-corpus question** — *"How long do I have to return an item?"*
> You may return most items within **30 days** of the delivery date...
> Source: returns_policy.md

**Out-of-corpus question** — *"Who is Northwind's CEO?"*
> I don't know. The provided context only covers Northwind Supply Co.'s return and refund policies and does not contain that information.

The second case is the important one: the system refuses to invent an answer that isn't supported by the source documents.

## Planned improvements

- **Retrieval quality tuning** — chunk sizing and cosine-normalized embeddings, evaluated with before/after retrieval tests.
- **Tool-calling agent** — an agent that combines document search with structured data lookups (e.g. order/CRM records) to handle multi-step tasks.
- **Evaluation harness** — automatic scoring of answer correctness across a test set of questions.
- **API deployment** — expose the system over an HTTP API.

## Notes

The document corpus is entirely fictional. No credentials or secrets are stored in this repository; the Anthropic API key is supplied via an environment variable at runtime.
