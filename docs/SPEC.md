# ThreatLens — Specification

## 1. Problem
SOC and CTI analysts lose time jumping between MITRE ATT&CK, NVD, CISA KEV, CERT-FR advisories and detection-rule repos to understand an alert or a vulnerability. Generic LLMs hallucinate CVE details and technique IDs. ThreatLens answers analyst questions **grounded in authoritative public sources, with citations**.

## 2. Users and example queries
| User | Example |
|---|---|
| SOC analyst | "This alert shows `powershell -enc ...` spawned by winword.exe — what is it and how do I detect it?" |
| Vuln manager | "Is CVE-2024-3400 exploited in the wild? What should I patch first?" |
| CTI analyst | "Which ATT&CK techniques relate to credential dumping from LSASS, and which Sigma rules cover them?" |
| French context | "Quels avis CERT-FR récents concernent Fortinet ?" |

## 3. Architecture
```
            ┌──────────── offline ────────────┐
 sources ─► ingest/* ─► Document JSONL ─► chunking ─► index/build ─► Qdrant (dense) + BM25 (sparse)
            └─────────────────────────────────┘
            ┌──────────── online ─────────────┐
 query ─► guard (injection check)
       ─► hybrid retrieval (dense + BM25, fused with RRF, top 30)
       ─► cross-encoder rerank (top 6) ─► NVD live lookup for unknown CVE ids
       ─► guard (sanitise retrieved text)
       ─► router (small vs large LLM — uses retrieval confidence, so it runs after retrieval)
       ─► LLM generate (cited answer) ─► Answer {text, citations, model, cost, latency, flags}
            └─────────────────────────────────┘
```

## 4. Components
| Component | Choice (MVP) | Why | Later options |
|---|---|---|---|
| Embeddings | `BAAI/bge-small-en-v1.5` (384-d) | fast on CPU, strong MTEB score | bge-m3 (multilingual FR/EN), e5 |
| Vector store | Qdrant local mode (file) | no server for MVP, same API as prod | Qdrant server in Docker / cloud |
| Sparse | `rank_bm25` | exact matches on IDs (CVE-, T1059) matter a lot here | Qdrant sparse vectors / SPLADE |
| Fusion | Reciprocal Rank Fusion (k=60) | parameter-free, robust | learned weights |
| Reranker | `BAAI/bge-reranker-base` cross-encoder | big precision gain on top-k | none / smaller reranker (ablation) |
| LLM | LiteLLM → Ollama `llama3.1:8b` (small) + one API model (large) | one interface, swap providers | vLLM self-hosting |
| API / UI | FastAPI / Streamlit | standard, quick | Next.js |

## 5. Interfaces
```python
pipeline.answer(question: str, *, force_model: str | None = None) -> Answer
Answer = {answer: str, citations: list[RetrievedChunk], model: str,
          route_reason: str, cost_usd: float, latency_ms: int, guard_flags: list[str]}
```
`POST /ask {"question": "..."}` → `Answer` JSON. `GET /health`.

## 6. The four differentiators (each must produce a result in the README)
1. **Retrieval evaluation** — `eval/questions.jsonl` (target: 100+ questions with gold doc ids).
   Metrics: Recall@5, Recall@10, MRR@10, nDCG@10. Ablations: dense / BM25 / hybrid / hybrid+rerank; chunk size 256 vs 512 tokens; 2 embedding models.
   Answer quality: faithfulness + answer relevancy (RAGAS or LLM-as-judge), citation accuracy.
2. **Cost-aware routing (decision-making)** — features: query length, # of entities (CVE/Txxxx), retrieval confidence (top rerank score, score gap), query type. Policy v1: rules; v2: logistic regression predicting "small model is good enough" trained on eval labels. Output: quality-vs-cost Pareto plot, % cost saved at ≤ X% quality loss.
3. **AI security** — attack set: direct prompt injection, indirect injection via a poisoned document in the corpus, data-exfiltration prompts. Defences: input classifier/heuristics, retrieved-text sanitisation + delimiting, instruction hierarchy in system prompt, output check. Metric: attack success rate (ASR) before/after, false-positive rate on benign queries.
4. **Production** — Docker image, GitHub Actions (lint + tests), deployed on Azure Container Apps or AWS (ECS/App Runner), per-query logs (latency, tokens, cost, model) → dashboard (Streamlit page or Power BI).

## 7. Non-goals
Real-time SIEM integration, fine-tuning, private/customer data, autonomous response actions.

## 8. Definition of done (v1.0)
Public GitHub repo with: one-command local run, live demo URL, architecture diagram, benchmark tables + plots for the 4 differentiators, a 60-90 s demo GIF/video, tests passing in CI.
