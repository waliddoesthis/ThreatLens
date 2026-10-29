# ThreatLens 🔎

**Agentic RAG copilot for SOC & CTI analysts** — ask about an alert, a log line or a CVE and get a cited answer grounded in MITRE ATT&CK, CISA KEV, NVD, CERT-FR and SigmaHQ.

> Status: 🚧 work in progress — see [docs/ROADMAP.md](docs/ROADMAP.md)

## Highlights
- **Hybrid retrieval**: BM25 + dense embeddings fused with RRF, cross-encoder reranking
- **Cited answers**: every claim points to its source (`[attack:T1059.001]`, `[kev:CVE-2024-3400]`)
- **Cost-aware LLM routing**: small local model vs large API model, chosen per query
- **Hardened against prompt injection**: attack/defence benchmark included
- **Measured**: retrieval & answer-quality benchmark with ablations
- **Production-ready**: FastAPI, Streamlit, Docker, CI, cloud deployment

## Architecture
```
query ─► guard ─► hybrid retrieval (BM25 + dense, RRF) ─► rerank ─► sanitise ─► router ─► LLM ─► cited answer
```
Details: [docs/SPEC.md](docs/SPEC.md)

## Quickstart
```bash
git clone https://github.com/waliddoesthis/threatlens && cd threatlens
python -m venv .venv && source .venv/bin/activate
make install
cp .env.example .env          # set your model names / API key
ollama pull llama3.1:8b       # local small model (https://ollama.com)
make ingest                   # download ATT&CK, KEV, Sigma, CERT-FR
make index                    # build indexes
make ui                       # http://localhost:8501
```

## Results
_Coming in M2–M4: retrieval ablations, router Pareto front, prompt-injection ASR._

| Retrieval | Recall@5 | MRR@10 |
|---|---|---|
| BM25 | – | – |
| Dense | – | – |
| Hybrid (RRF) | – | – |
| Hybrid + rerank | – | – |

## Data
Public sources only — see [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md). ATT&CK® is a registered trademark of The MITRE Corporation.

## Author
Walid Ichchou — [walidichchou.dev](https://walidichchou.dev)
