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
Retrieval on 35 benchmark questions (ATT&CK techniques, CVE nicknames, "which Sigma rule detects X"), over 5,715 documents / 6,150 chunks from ATT&CK, CISA KEV, SigmaHQ and CERT-FR. Raw numbers in [eval/results/](eval/results/), reasoning in [docs/DECISIONS.md](docs/DECISIONS.md).

| Retrieval | Recall@5 | Recall@10 | MRR@10 |
|---|---|---|---|
| BM25 | 0.686 | 0.857 | 0.547 |
| Dense (bge-small-en-v1.5) | 0.914 | 0.971 | 0.750 |
| Hybrid (RRF) | 0.943 | **1.000** | 0.746 |
| Hybrid + cross-encoder rerank | 0.857 | 0.914 | 0.683 |
| Hybrid + rerank, RRF-fused (default) | **0.943** | 0.971 | **0.801** |

Takeaways:
- **Hybrid beats either retriever alone.** BM25 misses paraphrases ("Citrix Bleed", "EternalBlue"); dense misses some exact tool names. Fused, every gold document is in the top 10.
- **A reranker is not a free win.** The cross-encoder alone ranks narrow Sigma rules above the ATT&CK technique a question is about. Fusing its order with the hybrid order keeps recall and lifts MRR by 0.055.
- Caveat: 35 questions, and the fusion choice was made on them. M2 re-checks it on a 100+ question set.

_Coming in M2–M4: answer faithfulness, router Pareto front, prompt-injection ASR._

## Data
Public sources only — see [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md). ATT&CK® is a registered trademark of The MITRE Corporation.

## Author
Walid Ichchou — [walidichchou.dev](https://walidichchou.dev)
