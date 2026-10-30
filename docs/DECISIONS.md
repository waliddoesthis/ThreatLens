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

## 2026-10-30 — Sigma ingest falls back to `git clone`
- **Decision:** try the `master.zip` archive first; on an HTTP error, shallow-clone `SigmaHQ/sigma` into `data/raw/sigma` and read `rules/**.yml` from disk. Both paths feed the same `parse_files()`.
- **Alternatives:** archive only; GitHub API listing + raw file downloads (thousands of requests).
- **Why:** some egress proxies allow git but refuse `codeload.github.com`. A test checks the zip and the checkout produce identical documents.
- **Corpus at this step:** 750 ATT&CK + 1,764 KEV + 3,161 Sigma docs → 6,110 chunks. Only `rules/` is indexed; `rules-emerging-threats`, `rules-threat-hunting` and `deprecated/` are left out for now.

## 2026-10-30 — CERT-FR moved to cert.cyber.gouv.fr
- **Finding:** `www.cert.ssi.gouv.fr/feed/` now 302-redirects to `cert.cyber.gouv.fr/feed/`.
- **Decision:** point the ingester at the new host directly so allow-lists only need one domain.

## 2026-10-30 — Benchmark grows to 35 questions, incl. detection
- **Decision:** add 20 questions: 5 ATT&CK paraphrases, 5 CVE nicknames (ProxyLogon, EternalBlue, PrintNightmare, Zerologon, FortiOS path traversal) and 10 "which Sigma rule detects X" questions with a single gold rule each.
- **Why:** with Sigma in the index, ATT&CK questions now compete with hundreds of rules that repeat the same keywords, so detection questions are needed to measure that the right *kind* of document comes back.
- **Effect on BM25 (35 q, 6,110 chunks):** Recall@5 0.686, Recall@10 0.857, MRR@10 0.542, nDCG@10 0.617 — lower than the 15-question ATT&CK+KEV baseline (R@5 0.80) because a bigger corpus adds keyword-matching distractors (e.g. "LSASS" questions now rank 10 Sigma rules above T1003.001).
- **Results are committed** under `eval/results/` (no longer git-ignored) so each number in the README has a file behind it.

## 2026-10-30 — Docker image: CPU torch, no apt
- **Decision:** install torch from the CPU wheel index (`TORCH_INDEX_URL` build arg) and skip `apt-get`; health checks use Python's `urllib` instead of curl.
- **Why:** CUDA wheels make the image ~6 GB for no benefit on CPU hosts (App Runner / Container Apps). No apt keeps builds working behind proxies that block Debian mirrors. Ingest runs on the host or in a one-off `docker compose run`, writing to the mounted `./data` volume.

## 2026-10-30 — Fuse the reranker with the hybrid order instead of replacing it
- **Finding (35 q, 5,715 docs, 6,150 chunks):**

  | Mode | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
  |---|---|---|---|---|
  | bm25 | 0.686 | 0.857 | 0.547 | 0.620 |
  | dense (bge-small-en-v1.5) | 0.914 | 0.971 | 0.750 | 0.804 |
  | hybrid (RRF) | 0.943 | 1.000 | 0.746 | 0.809 |
  | hybrid + rerank (bge-reranker-base) | 0.857 | 0.914 | 0.683 | 0.739 |
  | hybrid + rerank, RRF-fused | 0.943 | 0.971 | 0.801 | 0.844 |

  Hybrid confirms the RRF decision above: BM25 misses paraphrases, dense misses some exact tool names, together they find every gold doc in the top 10. The pure cross-encoder *hurts*: for "How do attackers abuse PowerShell…" it ranks narrow Sigma PowerShell rules above T1059.001, and for "EternalBlue…" it prefers the SMBv1 mitigation over the KEV entry. It scores topical overlap, not "is this the canonical answer".
- **Decision:** `rerank()` RRF-fuses the cross-encoder order with the incoming hybrid order (`RERANK_FUSION=true`, default). Pure reranking stays available (`fuse=False`) and in the ablation.
- **Alternatives:** drop the reranker (simpler, MRR 0.746); a larger reranker (bge-reranker-v2-m3, ~2.3 GB, slower on CPU); per-source quotas in the final top-k.
- **Caveat:** 35 questions is small and this choice was made on the same set — re-check on the 100+ question benchmark in M2 before claiming it in the README.

## 2026-10-30 — Pluggable vector store: Qdrant (default) or Chroma
- **Decision:** `index/vectorstore.py` puts Qdrant and Chroma behind one 4-method interface (`reset/add/search/close`); `VECTOR_STORE=qdrant|chroma` picks one for both `make index` and the retriever. Chunk positions are the point ids, so BM25, RRF and the reranker are unchanged.
- **Why both:** Walid wants the project to run on Chroma too. Qdrant stays the default (same client for embedded and server mode, payload filters, sparse vectors for later).
- **Finding:** Chroma's HNSW is approximate while Qdrant's local mode searches exactly. With Chroma's defaults (ef_search 100) dense Recall@5 was 0.886 vs 0.914, because neighbours were missed (e.g. only 13 of the top 30 shared for "ProxyLogon…"). `ef_search=200` closes the gap.
- **Result (35 q):** dense and hybrid identical on both stores (R@5 0.914 / 0.943). Rerank modes differ by ≤0.014 MRR from tiny ordering differences deep in the 30 candidates. Files: `eval/results/retrieval.md` (Qdrant), `eval/results/retrieval-chroma.md`.
