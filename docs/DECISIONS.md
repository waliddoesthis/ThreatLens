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

## 2026-11-04 — Benchmark grows to 117 questions, scored per question type
- **Decision:** add 82 questions (q036–q117): 35 ATT&CK paraphrases, 6 mitigations, 16 CVE nicknames (Spring4Shell, Follina, ProxyNotShell, noPac…), 10 detection questions, 5 raw alerts / log lines, 5 CERT-FR questions and 5 French paraphrases of English ATT&CK questions. Four questions have 2–3 gold docs (ProxyNotShell, the Ivanti chain, noPac, DCSync rules). Every gold id was checked against the corpus before committing.
- **Why these types:** CLAUDE.md promises "a question, an alert, a log line or a CVE id"; alerts and French queries were not measured at all before. `run_retrieval_eval.py` now reports metrics per type, because an average over 117 questions hides a type that fails completely.
- **Stale labels:** CERT-FR's feed keeps only ~40 recent advisories and ATT&CK renumbers techniques, so the eval drops gold ids that are no longer in the corpus (with a warning) instead of counting them as misses. The CERT-FR questions are tied to the 2026-11-03 snapshot.

## 2026-11-04 — Strip ATT&CK "(Citation: …)" markers at ingest
- **Finding:** the first answer-eval run showed llama3.2:3b citing `([Citation: TechNet PowerShell])` instead of `[attack:T1059.001]`. ATT&CK descriptions carry STIX citation markers (679 of 750 docs) and markdown links, and a small model copies the format it sees in its sources over the one in the system prompt.
- **Decision:** `ingest.clean_stix_text()` removes `(Citation: X)` and unwraps `[text](url)` in ATT&CK descriptions/detections and Sigma descriptions.
- **Side effect on retrieval (117 q, hybrid + fused rerank):** R@5 0.893 → 0.910, MRR@10 0.759 → 0.741. The markers were noise for BM25 and the embeddings; the MRR drop is a few gold docs moving from rank 1 to 2. All numbers below are on the cleaned corpus.

## 2026-11-04 — Fused reranking confirmed on the 117-question set
- **Finding (117 q, 5,718 docs, cleaned corpus):**

  | Mode | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
  |---|---|---|---|---|
  | bm25 | 0.742 | 0.843 | 0.615 | 0.665 |
  | dense | 0.877 | 0.903 | 0.738 | 0.773 |
  | hybrid (RRF) | 0.893 | 0.936 | 0.738 | 0.783 |
  | hybrid + rerank | 0.850 | 0.919 | 0.711 | 0.758 |
  | hybrid + rerank, RRF-fused | **0.910** | **0.936** | **0.741** | **0.787** |

- The October choice (made on 35 questions) holds on 82 unseen ones: the fused reranker is the best or tied-best mode on every metric, and the pure cross-encoder is still worse than no reranker. The margin over plain hybrid is small (+0.017 R@5, ≈2 questions), so the reranker earns its latency mostly on the top 5 the LLM sees.
- **Where it fails:** French questions score **0** in every mode. The corpus is English except CERT-FR, BM25 shares no tokens with "rançongiciel" or "hameçonnage", and bge-small-en is English-only. Raw alerts (R@5 0.70) are the next weakest: a command line like `rundll32 comsvcs.dll, MiniDump` is matched to Sigma rules but not to the ATT&CK technique. Both feed the embedding ablation below.

## 2026-11-04 — Chunk size and embedding model: keep 220 words and bge-small
- **Setup:** `eval/run_ablation.py` builds one index per config under `data/index-ablation/` and scores dense, hybrid and hybrid + fused rerank on the 117 questions (cleaned corpus). Results: `eval/results/ablation.md`.
- **Chunk size (bge-small, overlap ~18%), hybrid + fused rerank:** 120 words R@5 0.897 / MRR 0.760 (7,293 chunks); 220 words 0.910 / 0.741 (6,100); 400 words 0.910 / 0.755 (5,803). The spread is ≤0.014 on every metric, about 1–2 questions. Most ATT&CK, KEV and Sigma records fit in one chunk at any of these sizes (5,718 docs → 5,803–7,293 chunks), so the window only changes the long ATT&CK pages. 400 words also gets close to bge-small's 512-token limit for text full of paths and ids. Keep 220.
- **Embedding model (220 words), hybrid + fused rerank:**

  | Model | Dim | Build (4 CPUs) | R@5 | MRR@10 | French R@5 |
  |---|---|---|---|---|---|
  | bge-small-en-v1.5 (default) | 384 | ~3 min | 0.910 | 0.741 | 0.0 |
  | bge-base-en-v1.5 | 768 | 13 min | **0.925** | 0.758 | 0.4 |
  | multilingual-e5-small | 384 | 5 min | 0.906 | **0.761** | 0.2 |

- **Decision:** keep bge-small as the default. bge-base's gain (+0.015 R@5, ≈2 questions of 117) is within what one relabelled question moves, and it costs 4× build time, 2× vector size and slower CPU queries on the App Runner / Container Apps target. It stays one `EMBEDDING_MODEL=BAAI/bge-base-en-v1.5` away. Each model gets its own query/passage instruction prefix (`index.embedding_prefixes`); e5 without `query:`/`passage:` is a known recall loss.
- **French is not solved by a multilingual encoder alone:** multilingual-e5-small reaches only 0.2 on the French paraphrases after fusion, and its dense English scores drop (R@5 0.822 vs 0.877). The hybrid also mixes in a BM25 list that has no French tokens to match. Next options: translate the query to English with the small LLM before retrieval, or bge-m3. Logged for after M4.
- **Removed `ragas` from the `eval` extra:** its current release fails to import (`langchain_community` API change) and it pulls LangChain, which CLAUDE.md keeps out of the core. Faithfulness uses a 40-line LLM-as-judge instead (`eval/judge.py`).

## 2026-11-04 — Answer eval: deterministic citation checks next to an LLM judge
- **Decision:** `eval/run_answer_eval.py` runs each question through the real pipeline (only the router is bypassed) and scores the answer two ways:
  - **LLM judge** (`eval/judge.py`, plain prompt + JSON): splits the answer into claims, marks each supported or not by the sources → *faithfulness*; plus a 1–5 *relevancy*.
  - **Deterministic** (`eval/metrics.py`, unit-tested): *citation validity* (cited ids that were really provided), *gold cited* (cites a gold doc when one was retrieved), *statement coverage* (statements carrying a citation), *unsupported ids* (CVE / Txxxx / Mxxxx ids stated in prose that appear in no source). The citation parser is shared with the UI (`threatlens.citations`).
- **Why both:** a judge model is cheap to run but lenient and biased; regex checks can't judge meaning but never drift. Where they disagree, the deterministic number wins the argument.
- **Alternatives:** RAGAS (broken import, pulls LangChain); judge-only; human labels (best, kept for a small audit set later).
- **First run — CPU sample only (10 questions, every 12th; generator llama3.2:3b, judge qwen2.5:7b, 4 CPUs, ~66 s per answer):**

  | Faithfulness (judge) | Relevancy | Citation validity | Gold cited | Statement coverage | Unsupported ids / answer |
  |---|---|---|---|---|---|
  | 0.93 | 4.5 / 5 | 1.00 (2 answers cite) | 0.20 | 0.07 | 1.2 |

  The judge says the answers are faithful; the citation checks say a 3B model mostly ignores the citation format (8 of 10 answers cite nothing) and lists ATT&CK ids from memory (q025 labels "T1059.001: Path Traversal"; the judge still gave it 1.0). **A 3B model is not good enough for ThreatLens, and a 7B judge is too lenient to be trusted alone.**
- **Next:** run the full 117 questions with the production small model (`ollama/llama3.1:8b`, GPU) and a stronger judge (`JUDGE_MODEL`, defaults to `LARGE_MODEL`). Those per-question rows are also the training labels for the M3 router ("was the small model good enough?").

## 2026-11-04 — Rebuild the vector store from an empty folder
- **Finding:** on Windows, rebuilding the index after re-ingest left the Qdrant collection with 6,150 points while `chunks.jsonl` had 6,097, so dense search returned ids past the end of the chunk list and the answer eval crashed with an `IndexError`.
- **Decision:** `index.build` deletes `data/index/<store>/` before writing vectors, and `dense_search` raises a clear "out of sync, run `make index`" error if the store ever returns an id beyond the chunk list.
- **Why both:** the first removes the cause; the second turns any future mismatch (manual copy, partial build) into an actionable message instead of a crash deep in retrieval.

## 2026-11-04 — Full answer eval: llama3.1:8b on 112 questions
- **Setup:** generator `ollama/llama3.1:8b`, judge `ollama/qwen2.5:7b` (the largest judge that fits next to it on an 8 GB RTX 2070), cleaned corpus with 6,097 chunks, 7,029 s total (~41 s per answer at generation). It ran on 112 of 117 questions: that machine's CERT-FR feed had rolled past the 5 benchmark advisories, and the eval drops gold ids missing from the corpus by design.
- **Result:**

  | Scope | n | Faithfulness | Relevancy | Citation validity | Gold cited | Stmt coverage | Unsupported ids |
  |---|---|---|---|---|---|---|---|
  | all | 112 | 0.875 | 4.61 | 0.974 | 0.765 | 0.444 | 0.14 |
  | technique | 50 | 0.950 | 4.94 | 1.000 | 0.938 | 0.621 | 0.00 |
  | cve | 25 | 0.842 | 4.32 | 0.899 | 0.783 | 0.521 | 0.60 |
  | detection | 20 | 0.837 | 4.58 | 1.000 | 0.400 | 0.130 | 0.00 |
  | mitigation | 7 | 0.964 | 4.86 | 1.000 | 0.571 | 0.148 | 0.00 |
  | alert | 5 | 0.739 | 4.40 | 1.000 | 0.750 | 0.258 | 0.20 |
  | french | 5 | 0.467 | 2.80 | 1.000 | – | 0.140 | 0.00 |

- **Takeaways:** (1) Compared with the 3B sample, the judge's faithfulness barely moves (0.93 → 0.88) while gold-cited goes 0.20 → 0.77 and unsupported ids 1.2 → 0.14: model choice shows up in the citation checks, not in the judge score. (2) Detection questions retrieve the right Sigma rule (R@5 1.0) but the answer cites it only 40% of the time; the prompt asks for "Sigma rules when available" and the model prefers the ATT&CK page. (3) Some answers name ids in prose ("source id: sigma:…") instead of brackets. The parser deliberately does not accept that, because the UI can't link it.
- **Next:** stricter citation instructions plus one few-shot example in the system prompt (M4 prompt hardening), then re-measure; the per-question rows become router labels in M3.

## 2026-11-10 — Router: the low-confidence rule was dead code; use the best cross-encoder score
- **Finding (project review):** `router.route` sent a query to the large model when `chunks[0].score < 0.0`. `bge-reranker-base` scores come out of a sigmoid (checked: 0.994 for a relevant pair, 0.00004 for an unrelated one), so the rule could never fire. Two more problems hid behind it: with fused reranking the first chunk is not always the best-scored one, and a live NVD record is put first with a fixed score of 1.0 and stage `nvd`.
- **Decision:** confidence = the **highest cross-encoder score among reranked chunks**; route to the large model when it is below `ROUTER_MIN_CONFIDENCE` (default 0.3). No reranked chunks (reranker off) means no signal, and the rule stays out of the way.
- **Why 0.3 — measured on the 117 questions, top 6 chunks, fresh corpus:**

  | Threshold | Flags among the 15 questions whose gold doc is not in the top 6 | Flags among the 102 where it is |
  |---|---|---|
  | 0.05 | 8 | 0 |
  | 0.1 | 8 | 3 |
  | **0.3** | **9** | **4** |
  | 0.5 | 11 | 7 |
  | 0.7 | 12 | 16 |

  Eight off-topic questions ("How do I bake sourdough bread?") all score below 0.02. The 6 misses it cannot catch score 0.39–0.94: the reranker is confidently wrong there, which a score threshold will never see.
- **Limit, kept honest:** a bigger model cannot answer from sources that are not there. For the French and rolled-off CERT-FR questions the right behaviour is to fix retrieval (query translation, M2.5) or to abstain; "low confidence" is one input to the M3 learned router, not the final policy. The threshold was picked on the same 117 questions it is reported on, so M3 must re-check it on held-out questions.
- **Alternatives:** score gap between rank 1 and 2 (kept as a feature, not a rule); calibrating on RRF scores (not comparable across queries).
