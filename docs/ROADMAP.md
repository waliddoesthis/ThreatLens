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
- [x] Generation with citations (Ollama small model) — llama3.1:8b on a local GPU, cites ATT&CK + Sigma ids
- [x] FastAPI `/ask` + Streamlit UI with clickable sources
- [x] Dockerfile + docker-compose (CPU torch, health checks)
**Deliverable:** demo GIF of 3 queries answered with sources.

## M2 — Evaluation (week 2)
- [x] 100+ benchmark questions with gold ids (`eval/questions.jsonl`) — 117 q across 7 types (technique, mitigation, CVE, detection, alert, CERT-FR, French)
- [x] Retrieval metrics script + ablation table (dense / BM25 / hybrid / +rerank) — fused rerank best: R@5 0.910, MRR 0.741; per-type breakdown
- [x] Chunk-size and embedding-model ablations — chunk size ±0.014; bge-base +0.015 R@5 at 4× build time; French 0 → 0.2–0.4 with bigger/multilingual encoders
- [x] Answer faithfulness + citation accuracy — llama3.1:8b on 112 q: faithfulness 0.875, citation validity 0.974, gold doc cited 0.765 (detections only 0.40); LLM judge alone ranked a 3B model higher
**Deliverable:** results table + bar chart in README.

## M2.5 — Review fixes, graph and agent mode
- [x] Pin every data source + ingest manifest — ATT&CK v20.1, Sigma r2026-07-01, KEV snapshot, 6 CERT-FR advisories by reference (all 6 had rolled off the RSS feed); pinning moved Recall@5 0.910 → 0.905
- [x] Bootstrap confidence intervals + paired differences in the retrieval eval — hybrid vs dense and the reranker's +0.017 are not distinguishable from zero on 117 questions
- [x] Alert benchmark from Atomic Red Team — 107 real command lines; fused rerank Recall@5 0.150 (hand-written alerts: 0.70)
- [x] Knowledge graph (Sigma → technique → mitigation, id → document) + link expansion for alerts — Recall@5 0.150 → 0.327 on the 107 alerts (held-out half 0.132 → 0.302); core set unchanged within noise
- [x] French query translation — French Recall@5 0.0 → 1.0 (5 questions); full path 0.943 vs 0.887 for plain hybrid (Δ +0.056, 95% CI +0.013 to +0.107)
- [x] Router low-confidence rule fixed (it could never fire); threshold 0.3 from data
- [x] Agent mode: seeded retrieval + 5 tools, bounded loop, citation check, UI trace — unit-tested; 4-question trial with llama3.1:8b on CPU only
- [x] Agent vs pipeline on the full answer benchmark — faithfulness 0.910 vs 0.885 (Δ +0.026, CI −0.012 to +0.062: not shown), gold cited 0.726 vs 0.779 (not shown), latency 55.0 s vs 40.7 s (+14.3 s, CI +12.0 to +16.2). First agent left 81 of 117 answers uncited; gather-then-write brought that to 24. Pipeline stays the default
- [x] Re-run the M2 answer eval through `ollama_chat/` on the pinned corpus — 117 questions: faithfulness 0.885, gold cited 0.779 (M2: 0.875 / 0.765 on 112); French faithfulness 0.47 → 0.95
**Deliverable:** alert benchmark chart + "follow the links" result in README.

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
- [x] GitHub Actions CI (ruff + pytest) — runs on every push and PR (light install, model-free tests)
- [x] Streamed answers (`POST /ask/stream`, live UI) — first token 18.9 s vs full answer 27.8 s on the 8 GB GPU (−9.0 s, CI −10.2 to −7.9); 13.1 s of the wait is retrieval + reranking on a CPU build of PyTorch
- [ ] Reranker on the GPU (or a lighter one): the measured bottleneck before the first token
- [x] Demo image for a Hugging Face Space (`deploy/space/`, [guide](DEPLOY.md)): corpus and index built into the image from the pinned sources (6,094 chunks, about 9 minutes on 4 CPUs), hosted model by configuration, questions capped per visit and per day
- [ ] Record the demo on the local GPU following [DEMO.md](DEMO.md) and embed it at the top of the README (chosen over hosting: a Docker Space needs a paid plan)
- [ ] Public URL (open: Azure for Students or Streamlit Community Cloud are the free candidates)
- [ ] Monitoring dashboard (Streamlit page or Power BI)
- [ ] README final: diagram, results, demo video, "how to run"
- [ ] CV bullet + LinkedIn post
