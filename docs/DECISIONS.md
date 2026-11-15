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

## 2026-11-10 — Pin every data source; the benchmark was silently losing questions
- **Finding:** ATT&CK and Sigma were fetched from their default branches, KEV from the live feed and CERT-FR from an RSS feed that keeps ~40 items. On a fresh ingest **all 6 CERT-FR advisories the benchmark uses had rolled off the feed**, so those questions were dropped (the eval skips gold ids missing from the corpus) and nothing failed.
- **Decision:** `ingest/pins.py` holds one version per source: ATT&CK `ATT&CK-v20.1`, Sigma `r2026-07-01`, KEV at a `cisagov/kev-data` commit. CERT-FR advisories named in `CERTFR_PINNED` are fetched by reference (JSON endpoint, HTML page for CTI reports) and anything ingested earlier is kept. `DATA_PIN=latest` tracks upstream for a demo corpus. Every ingest writes `data/processed/manifest.json`; eval reports print it.
- **Cost of pinning, measured:** same 117 questions, fused rerank: Recall@5 0.910 → 0.905, MRR@10 0.741 → 0.741. The corpus changed slightly (Sigma release vs master: 3,142 vs 3,164 rules), the conclusions did not.
- **Alternatives:** committing the corpus to the repo (licences, 12 MB of churn); a hash check only (detects drift, does not prevent it).

## 2026-11-10 — Confidence intervals: two M1/M2 conclusions were stated too strongly
- **Decision:** the retrieval eval reports a 95% bootstrap interval per mode (2,000 resamples of the questions, seeded) and a **paired** difference to plain hybrid.
- **What it changes (117 questions, pinned corpus):**

  | Mode | Recall@5 | 95% CI | Δ vs hybrid (95% CI) |
  |---|---|---|---|
  | BM25 | 0.746 | 0.665–0.821 | −0.141 (−0.218 to −0.073) |
  | Dense | 0.875 | 0.813–0.929 | −0.013 (−0.051 to +0.026) |
  | Hybrid | 0.887 | 0.825–0.943 | – |
  | Hybrid + rerank | 0.845 | 0.778–0.906 | −0.043 (−0.103 to +0.009) |
  | Hybrid + rerank, RRF-fused | 0.905 | 0.848–0.956 | +0.017 (−0.017 to +0.051) |

  Only "BM25 alone is worse" survives. **Hybrid vs dense and the fused reranker's gain are not distinguishable from zero on 117 questions.** The earlier entries say "hybrid beats either retriever" and "fused rerank is best"; the honest wording is "consistently ahead, not significantly". The reranker stays on because its score is the router's confidence signal, not because of +0.017.
- **Why paired:** both systems answer the same questions, so resampling questions and differencing removes the question-difficulty variance. Unpaired intervals overlap even when one system wins on every resample.

## 2026-11-10 — Alert benchmark from Atomic Red Team: the 5 hand-written alerts were flattering
- **Decision:** `eval/build_alert_questions.py` builds `eval/questions_alerts.jsonl` from Atomic Red Team (MIT, commit `a0e3f9bc`): Windows tests run from cmd or PowerShell, **single-command tests only** (multi-line tests start with setup lines such as TLS settings, which would be mislabelled), input arguments replaced by defaults, one test per technique, commands naming a technique id dropped (label leak). **107 questions, one gold technique each.** Atomic Red Team is evaluation-only and never indexed.
- **Result:** the 5 alert questions I wrote in M2 score Recall@5 0.70. Real command lines score **0.15** with the same retrieval (BM25 0.159, dense 0.056, hybrid 0.103, fused rerank 0.150). Alerts are the first use case in the SPEC, and the benchmark had 5 of them, written by the person who built the retriever.
- **Why it is this low:** a command line (`vssadmin.exe delete shadows /all /quiet`) shares almost no vocabulary with a technique description, dense retrieval was not trained on command lines, and the cross-encoder agrees with the retrievers. The gold is also strict: one sub-technique, no credit for the parent or a sibling.
- **Alternatives:** more hand-written alerts (same author bias); Sigma rule test data (the rules are in the corpus: leak); Splunk attack_data logs (heavier, kept for later).

## 2026-11-10 — Knowledge graph: follow the Sigma rules' tags; reserved places, not re-ranking
- **Decision:** `graph.py` derives three kinds of edges from data already ingested: Sigma rule → technique (rule tags), technique → mitigation (STIX `mitigates`, now kept at ingest) and id → document. `pipeline.retrieve` uses two of them:
  - **link expansion** for pasted alerts / command lines (`router.looks_like_log`): the techniques tagged by the Sigma rules among the 30 candidates, voted with weight 1/(60+rank), take the last 3 places of the context;
  - **exact lookup**: documents whose id the question names go first.
- **First design, rejected by measurement:** fusing the vote order into the ranking as a third RRF list, for every question. Alerts went up, but the core benchmark fell from MRR@10 0.741 to 0.473: detection and CVE questions also retrieve Sigma rules, and the voted techniques jumped above the gold document. Adding the voted techniques to the reranker's pool without the third list did nothing at all: the cross-encoder ranks a technique description below the rules for a raw command line.
- **Chosen on half the data:** the number of reserved places (1, 2 or 3) was picked on the odd-numbered alert questions and checked on the even ones.

  | 5-chunk context, Recall@5 | Fused rerank | + link expansion | Paired Δ (95% CI) |
  |---|---|---|---|
  | Alerts, odd half (used to choose, n=54) | 0.167 | 0.352 | +0.185 (+0.056 to +0.315) |
  | Alerts, even half (held out, n=53) | 0.132 | 0.302 | +0.170 (+0.057 to +0.302) |
  | Alerts, all 107 | 0.150 | 0.327 | +0.178 (+0.093 to +0.262) |
  | Core 117 questions | 0.905 | 0.900 | within noise |

- **Still weak, stated plainly:** one alert in three. On the core set the 20 detection questions lose one hit (0.967 → 0.917): a question such as "Detect bitsadmin /transfer…" looks like a log line, and three places go to techniques. Next levers: an encoder that has seen command lines, ATT&CK procedure examples as extra documents, a better "is this a log line" test than six substrings.
- **Alternatives:** a graph database (three dictionaries are enough at 5,700 documents); LLM-extracted entities (the links here are published by the sources, not guessed).

## 2026-11-10 — French: translate the query, search both wordings
- **Decision:** `retrieval/translate.py` detects French with function-word counts (no model), has the small LLM translate the question once, and fuses four rankings: BM25 and dense for the original and for the English wording. The cross-encoder reads the English wording. Without a running model it falls back to the original question.
- **Result (pinned corpus):** French questions Recall@5 **0.0 → 1.0** (5 of 5), CERT-FR questions stay at 1.0, and the full path (link expansion + translation) reaches **Recall@5 0.943 vs 0.887 for plain hybrid, paired Δ +0.056 (95% CI +0.013 to +0.107)**: the first retrieval change in this project whose interval excludes zero. Translation costs one small-model call (about 3 s on 4 CPUs).
- **Two bugs found on the way:** the first run made French *worse*. (1) The detector counted single letters, so `regsvr32 /s /n /u` was "French". (2) Translations came back as "### System:"; see the next entry.
- **Caveat:** 5 French questions. The interval on the whole benchmark is honest; "French is solved" would not be.
- **Alternatives:** multilingual encoder (measured in M2: French 0.2–0.4 and English drops); translating the corpus (CERT-FR is the only French source and its questions already score 1.0).

## 2026-11-10 — `ollama_chat/`, not `ollama/`: the system prompt was not a system prompt
- **Finding:** with `SMALL_MODEL=ollama/llama3.1:8b`, LiteLLM calls Ollama's generate endpoint and flattens the messages into one text ("### System: … ### User: …"). The model's chat template never sees a system turn, some replies start with "### System:", and tool calling is unavailable. `ollama_chat/llama3.1:8b` uses the chat endpoint.
- **Decision:** the default small model is `ollama_chat/llama3.1:8b`.
- **Consequence:** the M2 answer-quality numbers (faithfulness 0.875, gold cited 0.765) were measured through the flattened route. They are kept as measured and must be re-run through the chat route before being compared with anything new.

## 2026-11-10 — Agent mode: retrieval is seeded, the model chooses what to look up next
- **Decision:** `agent.py` is a bounded tool-calling loop over LiteLLM (no framework). Five tools in `tools.py`, each a plain function over the index and the graph: `search`, `lookup` (exact id), `kev_status`, `related` (a technique's Sigma rules and mitigations) and `nvd`. Before the model says anything, the system runs the production retrieval on the question and `kev_status` on every CVE it names; the model then gets at most `AGENT_MAX_STEPS` (4) tool turns and a final turn without tools. Tool output passes through the guard, repeated calls are not executed twice, every call lands in `Answer.steps`, and citations of documents no tool returned are reported as `invalid_citation:` flags (also in the fixed pipeline).
- **Why seeded — what the first trial showed:** with free tool choice, `llama3.1:8b` (4 questions, CPU) made exactly one call per question and then wrote from memory. For "How do I detect and mitigate Kerberoasting?" it called `lookup("T1505")` (Kerberoasting is T1558.003) and cited a Sigma rule id that does not exist. The fixed pipeline answered the same questions better. An 8B model is a poor planner but a usable follow-up caller: seeded with the retrieved sources, the same question led to `related("T1558.003")` and an answer listing that technique's real rules and mitigations (M1026, M1027, M1041), and no invalid citation was flagged in the 4 answers.
- **What is not shown:** this is a 4-question smoke test, not a result. The seeded agent still mislabelled a technique name from memory ("T1036: Data Encrypted") and dropped the `[source:id]` format in places, and on 4 CPUs it takes 2–4 minutes per answer. Whether agent mode beats the pipeline on faithfulness and citations is the job of `make eval-answers-agent` on a GPU. Until then the pipeline stays the default (`ANSWER_MODE=pipeline`).
- **Why "agentic" is back in the README:** the model does choose and call tools. The claim is limited on purpose: retrieval first, the model second.
- **Alternatives:** LangGraph or another agent framework (CLAUDE.md keeps frameworks out of the core; the loop is 160 lines); ReAct text parsing (native tool calls are more reliable on small models); letting the model plan freely (measured above, worse).

## 2026-11-11 — Agent mode gathers with tools, then the pipeline's prompt writes the answer
- **Finding (full benchmark, 117 questions, llama3.1:8b on GPU, judge qwen2.5:7b, pinned corpus):** the first agent, where one turn could either call a tool or answer, was as grounded as the pipeline but stopped citing. Faithfulness 0.879 against 0.885; answers with no citation at all 81 of 117 against 18 of 117; gold document cited 0.239 against 0.779. It chose 0.8 tools per question, almost always `related`. Rows are kept in `eval/results/answers-llama3.1-8b-agent-oneturn.*`.
- **Why:** the citation rule was in the agent's system prompt, word for word. An 8B model offered tools in the same turn follows the tool instructions and lets the output format go. The pipeline prompt, without tools, gets cited answers from the same model.
- **Decision:** two phases. *Gather*: the model sees the seeded sources and replies with tool calls or the single word `DONE` (200 tokens at most, so it cannot drift into an answer). *Write*: one call with the pipeline's own system prompt, no tools, over the seeded sources followed by what the tools returned. A 3-question CPU check on questions that were uncited before gave 6, 9 and 8 citations, the gold document cited each time.
- **Sources are capped at `AGENT_MAX_SOURCES` (8).** In the first run the judge returned no usable verdict for 14 answers, all of them with 10 or more sources (10 of the 12 answers with 15 or 16 sources, none below 10): the prompt outgrew the local model's context window. Those 14 are missing from the 0.879 above. Citations are checked against the capped list, because that is what the model was shown.
- **Cost:** one more LLM call per answer than the first agent when no tool is needed (a short one: `DONE`).
- **Alternatives:** repeat the citation rule in a last user turn (keeps one prompt doing two jobs, and the trial already had the rule); retry only uncited answers (hides the cause, doubles latency on most questions); raise Ollama's `num_ctx` instead of capping (changes VRAM use on an 8 GB card and would make the pipeline numbers not comparable).
- **Result (same 117 questions, 2026-11-11):** uncited answers 81 → 24 (pipeline 18), gold cited 0.239 → 0.726, judge failures 14 → 1. Against the pipeline, paired bootstrap: faithfulness +0.026 (−0.012 to +0.062), relevancy +0.05 (−0.07 to +0.17), gold cited −0.053 (−0.133 to +0.035), statements with a citation +0.008 (−0.053 to +0.067): none shown. Latency +14.3 s per answer (+12.0 to +16.2): shown. The agent made 1.1 tool calls per question (`related` 95, `search` 33, `lookup` 4, `kev_status` 2, `nvd` 0) and 91 of 117 answers were written from exactly 8 sources.
- **Conclusion:** with `llama3.1:8b` the agent buys nothing measurable and costs 35% more time, so `ANSWER_MODE=pipeline` stays the default. The extra sources do not turn into citations: on detection questions the gold Sigma rule is cited in 0.30 of answers (pipeline 0.40) although `related` fetched rules for most of them. The planner is the limit, which makes agent mode a question for the large model in M3.
- **Context window, checked:** Ollama 0.40.15 loads both models with a 4096-token window and the code does not set `num_ctx`. Pipeline prompts measured on 30 of the questions are 3.7k to 9.7k characters; the two tokenised with `llama3.1:8b` came to 1743 and 1963 tokens (4.1 and 4.9 characters per token), so six sources plus an 800-token answer fit. Eight sources is about a third more and still fits on that estimate; the 10 to 16 of the first agent did not, which is what broke the judge. The window is an Ollama default, not a project setting: making it one (`num_ctx` through LiteLLM) is open, and needs both modes re-run.

## 2026-11-11 — Streaming: one generator of events, server-sent events on the wire
- **Decision:** `pipeline.answer_events()` is a generator that yields `sources`, `step` (agent mode), `token` and a final `done` event carrying the `Answer`. `answer()` is the same generator run with `stream=False`, so the evals and the streamed path cannot drift apart. `POST /ask/stream` writes each event as one server-sent `data:` line; the Streamlit app reads the same events from the API or in-process. In agent mode only the written answer is streamed; the gather turns are tool calls or `DONE` and are shown as steps.
- **Why SSE and not WebSockets:** the flow is one request, then one-way text. SSE is plain HTTP, passes proxies, needs no extra dependency in FastAPI and can be read with `curl`. WebSockets would buy a back-channel nothing here uses.
- **Result (30 questions, llama3.1:8b, 8 GB GPU):** first token after 18.9 s, full answer after 27.8 s, paired difference −9.0 s (95% CI −10.2 to −7.9). Sources are shown after 13.1 s.
- **What the measurement found:** most of the wait is before the model starts. The PyTorch in that environment is a CPU build, so embedding and above all the cross-encoder over 30 candidates run on the CPU (13 s); prompt reading adds 5.8 s. Streaming was the cheap win; moving the reranker to the GPU, or a smaller reranker, is the larger one and is now on the roadmap. It will move the latency numbers, not the retrieval numbers.
- **Trade-off for M4:** text that has been streamed cannot be taken back. The citation check, and any future output guard, sees the whole answer only at the end, so it can flag a streamed answer but not block it. If M4 needs a blocking output check, the options are to buffer the answer (losing the streaming benefit) or to check per sentence before releasing it.
- **Not explained:** the full answer took 27.8 s here and 40.7 s in the answer eval. The eval alternates generator and judge on one 8 GB card, which likely reloads a model on every question; that was not verified.
- **Alternatives:** a callback argument on `answer()` (needs a thread and a queue to feed an HTTP stream); a separate streaming code path (two implementations to keep equal).

## 2026-11-11 — Live demo: a Hugging Face Docker Space with a hosted model
- **Decision:** the demo is a Docker Space on free CPU hardware. `deploy/space/Dockerfile` clones the public repository at a chosen ref, builds the corpus and the index from the pinned sources at image build time, and starts the Streamlit app, which runs the pipeline in-process. The language model is a hosted one: `SMALL_MODEL`, `LARGE_MODEL` and the provider's key come from the Space's variables and secrets.
- **Why the index is built in the image:** a Space's disk is reset at every restart, so an index built at start-up would cost every cold start several minutes of embedding. Built into the image it costs the build once, and the demo answers from exactly the pinned corpus the benchmarks used. A build step checks that all four sources are in the index and fails the build otherwise, so a source that was down cannot ship a partial demo silently.
- **Why a hosted model and not Ollama in the Space:** an 8B model on 2 shared vCPUs takes minutes per answer (5 minutes measured here on 4). The hosted model is reached through LiteLLM, so the provider is one environment variable. Free tiers moved twice while this was written (the Llama models older guides recommend are gone from Groq's rate-limit table), which is the argument for configuration over code.
- **Why Streamlit alone, without the API container:** one process and one port is what a Space runs; the UI already calls the same `answer_events()` the API serves.
- **Protecting the key:** it is a Space secret, injected at run time, absent from the image and the repository. A free-tier key bounds the damage to a spent quota. On top, `limits.py` caps questions per browser session and per UTC day (defaults 10 and 300 in the image). The counters are in memory and reset with the process: they bound a burst of visitors or a script, they are not accounting, and a visitor who opens a new session gets a new allowance while the daily cap still holds.
- **Privacy:** the page tells visitors not to paste confidential data. A SOC tool invites pasting real logs, the demo is public, and a free tier may use what it receives to improve the provider's products.
- **Known cost:** no GPU, so embedding and reranking dominate the wait, as measured in the streaming run. A lighter reranker for the demo would need its own retrieval numbers first.
- **Alternatives:** Azure Container Apps or AWS App Runner (the original roadmap item; they need a paid account and can bill while idle); a Space that mirrors the whole repository (the Space README needs a YAML header that would be rendered as a table on GitHub); building the index at start-up (slow cold starts, and it would track upstream instead of the pins if a download changed).

## 2026-11-11 — Correction: the Hugging Face Space is not free; the demo is a recording
- **What was wrong:** the entry above and the first deployment guide called a Docker Space "free CPU hardware". The hardware is free, creating the Space is not: Hugging Face's Spaces overview says Gradio and Docker Spaces "require a paid plan to create: PRO for personal accounts" ($9 a month). The claim came from memory and was not checked against the pricing page before it was written down. Walid found it when he tried to create the Space.
- **Decision:** no paid hosting. The demo is a screen recording of the local app on the GPU, made with the shot list in `docs/DEMO.md`, next to the measured numbers. The Space image, the usage caps and the guide stay in the repository, marked as not deployed and not free.
- **Why a recording is acceptable:** it shows the real latency of the real system on the hardware the numbers were measured on, and costs nothing to keep online. What it cannot do is let a reader try their own question, so the README says there is no public URL.
- **Free hosting candidates, checked on the providers' pages the same day, not tried:** Streamlit Community Cloud (free, about 2.7 GB of RAM per app, sleeps after 12 hours, would need a prebuilt index because its disk is not kept); Azure for Students ($100 credit without a card for eligible students, Container Apps has a monthly free grant and scales to zero, would run the existing image).
- **Lesson kept:** a price or a limit of a third-party service goes into the docs only with the page and the date it was read on.
