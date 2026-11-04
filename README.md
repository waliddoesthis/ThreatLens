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
cp .env.example .env          # set your model names / API key; VECTOR_STORE=qdrant|chroma
ollama pull llama3.1:8b       # local small model (https://ollama.com)
make ingest                   # download ATT&CK, KEV, Sigma, CERT-FR
make index                    # build indexes
make ui                       # http://localhost:8501
```

## Results
Retrieval on a **117-question benchmark** ([eval/questions.jsonl](eval/questions.jsonl)): ATT&CK technique paraphrases, mitigations, CVE nicknames, "which Sigma rule detects X", raw alerts / log lines, CERT-FR advisories and French questions. Corpus: 5,718 documents / 6,153 chunks from ATT&CK, CISA KEV, SigmaHQ and CERT-FR. Raw numbers in [eval/results/](eval/results/), reasoning in [docs/DECISIONS.md](docs/DECISIONS.md).

![Retrieval ablation](docs/img/retrieval.png)

| Retrieval | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|
| BM25 | 0.754 | 0.843 | 0.598 | 0.652 |
| Dense (bge-small-en-v1.5) | 0.869 | 0.912 | 0.742 | 0.779 |
| Hybrid (RRF) | 0.868 | **0.936** | 0.740 | 0.785 |
| Hybrid + cross-encoder rerank | 0.842 | 0.902 | 0.700 | 0.746 |
| Hybrid + rerank, RRF-fused (default) | **0.893** | 0.927 | **0.759** | **0.799** |

Takeaways:
- **Hybrid beats either retriever alone**, and fusing the cross-encoder with the hybrid order (instead of replacing it) gives the best top 5. The choice was made on 35 questions in M1 and **held on 82 new ones**.
- **A reranker is not a free win.** On its own the cross-encoder ranks narrow Sigma rules above the ATT&CK technique a question is about, and scores below no reranker at all.
- **Per-type scores show what an average hides:** detection questions reach R@5 1.00 and CVE nicknames 0.92, but raw alerts sit at 0.70 and **French questions score 0** with an English embedding model ([by type](eval/results/retrieval.md)).
- **Qdrant or Chroma** gave the same scores in M1 (35 questions): set `VECTOR_STORE=chroma` and rebuild ([results](eval/results/retrieval-chroma.md)).

### Chunk size and embedding model
![Ablation](docs/img/ablation.png)

- **Chunk size (120 / 220 / 400 words) changes the scores by at most 0.012**, because most ATT&CK, KEV and Sigma records fit in one chunk at any of these sizes.
- **bge-base-en-v1.5 gains +0.023 Recall@5** (0.916) for 2.8× the build time and twice the vector size. bge-small stays the default for CPU hosting. `multilingual-e5-small` lifts French from 0 to 0.4 but loses on English ([full table](eval/results/ablation.md)).

### Answer quality
ANSWER_SECTION

## Data
Public sources only — see [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md). ATT&CK® is a registered trademark of The MITRE Corporation.

## Author
Walid Ichchou — [walidichchou.dev](https://walidichchou.dev)
