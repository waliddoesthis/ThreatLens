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

## 2026-10-29 — Lazy-load the dense side of the retriever
- **Decision:** `HybridRetriever` loads the embedding model and Qdrant on the first dense query; `index.build --sparse-only` and `run_retrieval_eval.py --modes bm25` skip them.
- **Alternatives:** always load both.
- **Why:** BM25 runs (CI, quick baselines, machines without model access) shouldn't need a ~130 MB model download. Hybrid behaviour is unchanged.
- **BM25 baseline (15 seed questions; 750 ATT&CK + 1,762 KEV docs, 2,785 chunks):** Recall@5 0.800, Recall@10 0.933, MRR@10 0.672, nDCG@10 0.733.
