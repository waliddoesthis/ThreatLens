# ThreatLens — Roadmap

Tick boxes as you go. Each milestone ends with something measurable for the README.

## M0 — Setup (½ day)
- [x] Repo scaffold, CLAUDE.md, SPEC, roadmap
- [x] `make install` works, `make test` green
- [x] GitHub repo created (public), first commit

## M1 — MVP RAG (days 1–4)
- [x] Ingest MITRE ATT&CK (techniques, sub-techniques, mitigations)
- [x] Ingest CISA KEV
- [x] BM25-only index + baseline eval (`--sparse-only`, `--modes bm25`)
- [x] Ingest SigmaHQ rules — 3,161 rules (archive, git-clone fallback)
- [x] Ingest CERT-FR advisories (RSS) — 40 recent advisories; feed moved to cert.cyber.gouv.fr
- [x] NVD lookup on demand for CVE ids not in KEV
- [x] Chunking + dense index (Qdrant local) + BM25 index — 6,150 chunks, ~3 min on 4 CPUs
- [x] Hybrid retrieval with RRF + reranker — R@5 0.686 (BM25) → 0.943 (hybrid), MRR 0.547 → 0.801 (hybrid + fused rerank)
- [ ] Generation with citations (Ollama small model)
- [ ] FastAPI `/ask` + Streamlit UI with clickable sources
- [x] Dockerfile + docker-compose (CPU torch, health checks)
**Deliverable:** demo GIF of 3 queries answered with sources.

## M2 — Evaluation (week 2)
- [ ] 100+ benchmark questions with gold ids (`eval/questions.jsonl`)
- [ ] Retrieval metrics script + ablation table (dense / BM25 / hybrid / +rerank)
- [ ] Chunk-size and embedding-model ablations
- [ ] Answer faithfulness + citation accuracy
**Deliverable:** results table + bar chart in README.

## M3 — Cost-aware router (week 2)
- [ ] Log cost/latency per query
- [ ] Rule-based router v1
- [ ] Learned router v2 (logistic regression on query + retrieval features)
- [ ] Pareto plot quality vs cost
**Deliverable:** "X% cheaper at Y% of the quality" headline.

## M4 — AI security (week 3)
- [ ] Attack set (direct, indirect/poisoned doc, exfiltration)
- [ ] Defences in `guard.py` + prompt hardening
- [ ] ASR before/after + false-positive rate
**Deliverable:** attack/defence table + one poisoned-doc example in README.

## M5 — Ship it (week 3)
- [ ] GitHub Actions CI (ruff + pytest)
- [ ] Cloud deployment (Azure Container Apps or AWS App Runner) + live URL
- [ ] Monitoring dashboard (Streamlit page or Power BI)
- [ ] README final: diagram, results, demo video, "how to run"
- [ ] CV bullet + LinkedIn post
