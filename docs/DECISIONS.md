# Design decisions log

One entry per non-trivial choice. These are your interview answers.

## 2026-10-29 — Hybrid retrieval (BM25 + dense) fused with RRF
- **Decision:** combine BM25 and dense retrieval with Reciprocal Rank Fusion.
- **Alternatives:** dense only; weighted score sum.
- **Why:** security queries contain exact identifiers (CVE-2024-3400, T1003.001, product names) that embeddings handle poorly, while natural-language questions need semantic search. RRF needs no score calibration between the two systems.
- **To verify:** M2 ablation table.

## 2026-10-29 — No LangChain/LlamaIndex in the core
- **Decision:** plain Python pipeline.
- **Why:** every step stays readable and explainable; easier to instrument cost/latency and insert the guard and router.

## 2026-10-29 — Qdrant local mode for the MVP
- **Decision:** `QdrantClient(path=...)`, switch to server mode for deployment.
- **Why:** zero infrastructure on day 1, same client API in production.

## 2026-10-29 — Validate benchmark gold ids against the corpus
- **Finding:** the current ATT&CK release renumbered "Clear Windows Event Logs" (T1070.001 → T1685.005); a stale gold label silently counts as a miss.
- **Decision:** `eval/run_retrieval_eval.py` warns when a gold id is absent from the index. Re-check labels after each ATT&CK update.
- **First baseline (BM25 only, 15 seed questions, ATT&CK + KEV):** Recall@5 ≈ 0.73–0.80, MRR@10 ≈ 0.60. Misses are paraphrases with no shared keywords (e.g. "Log4Shell", "Citrix Bleed") — exactly what dense retrieval should fix.
