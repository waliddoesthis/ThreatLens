# CLAUDE.md — ThreatLens

Context for Claude (Claude Code, Cowork, or a Claude Project) working on this repo.

## What this is
ThreatLens is an **agentic RAG copilot for SOC / CTI analysts**. Input: a question, an alert, a log line or a CVE ID.
Output: a cited answer, the related MITRE ATT&CK techniques, exploitation status (CISA KEV) and suggested Sigma detection rules.

It is a **portfolio project** (author: Walid Ichchou). Every feature must be demoable and **measured**.

## Source of truth
- `docs/SPEC.md` — architecture, components, interfaces, metrics
- `docs/ROADMAP.md` — milestones and current status (update the checkboxes)
- `docs/DATA_SOURCES.md` — corpora, URLs, licences
- `docs/DECISIONS.md` — design decisions log (append one entry per non-trivial choice)

## Layout
```
src/threatlens/
  config.py          settings from .env (pydantic-settings)
  schema.py          Document / Chunk / RetrievedChunk dataclasses
  ingest/            one module per source -> data/processed/<source>.jsonl
  chunking.py        document -> chunks
  index/build.py     dense index (Qdrant local) + BM25 index
  retrieval/         hybrid search (RRF) + cross-encoder reranker
  llm/               LiteLLM client, prompts, cost-aware router
  guard.py           prompt-injection detection / sanitisation
  pipeline.py        answer(question) -> Answer   (the main entry point)
  api.py             FastAPI app
app/streamlit_app.py UI
eval/                benchmark questions + evaluation scripts
tests/               pytest
```

## Commands
```bash
make install      # pip install -e ".[dev]"
make ingest       # download + normalise all sources
make index        # build dense + BM25 indexes
make api          # uvicorn on :8000
make ui           # streamlit on :8501
make eval         # retrieval benchmark -> eval/results/
make test         # pytest
```

## Conventions
- Python 3.11+, type hints everywhere, `ruff` for lint/format, `pytest` for tests.
- Every ingested record is normalised to `schema.Document` (id, source, title, text, url, metadata).
- Document ids are stable and source-prefixed: `attack:T1059.001`, `kev:CVE-2024-3400`, `sigma:<uuid>`, `certfr:CERTFR-2026-AVI-0001`.
- Answers MUST cite chunk ids as `[source:id]`; the UI turns them into links.
- No secrets in code. Read from `.env` via `config.settings`.
- Raw downloads go to `data/raw/`, normalised JSONL to `data/processed/`, indexes to `data/index/` (all git-ignored).
- Each new feature: code + test + a number in `eval/results/` + a line in `docs/ROADMAP.md`.
- Log design choices in `docs/DECISIONS.md` (date, decision, alternatives, why).

## Things not to do
- Don't fine-tune models; this is a retrieval / systems project.
- Don't add a heavy framework (LangChain, LlamaIndex) to the core pipeline — keep it readable and explainable in interviews. They may be used in a comparison notebook.
- Don't fetch anything outside the sources in `docs/DATA_SOURCES.md` without updating it.
