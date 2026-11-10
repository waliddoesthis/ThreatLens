# ThreatLens 🔎

**Agentic RAG copilot for SOC & CTI analysts** — ask about an alert, a log line or a CVE and get a cited answer grounded in MITRE ATT&CK, CISA KEV, NVD, CERT-FR and SigmaHQ.

> Status: 🚧 work in progress — see [docs/ROADMAP.md](docs/ROADMAP.md)

## Highlights
Built and measured:
- **Hybrid retrieval**: BM25 + dense embeddings fused with RRF, cross-encoder reranking
- **A small knowledge graph from the sources' own links**: Sigma rule → ATT&CK technique → mitigation. A pasted command line is matched to detection rules, and the rules' tags lead to the technique (Recall@5 on 107 real command lines: 0.15 → 0.33)
- **Agent mode**: retrieval always runs first, then the model chooses tools (exact id lookup, KEV status, linked rules and mitigations, NVD, another search); every call is shown in the UI
- **Cited answers**: every claim points to its source (`[attack:T1059.001]`, `[kev:CVE-2024-3400]`); citations of documents the model was never given are flagged
- **French questions** are searched in both languages (Recall@5 0 → 5 of 5)
- **Measured, with error bars**: two retrieval benchmarks (117 questions, 107 real alerts), ablations, bootstrap confidence intervals, pinned data versions ([results](#results))
- **Runs anywhere**: FastAPI, Streamlit, Docker Compose, CI (ruff + pytest)

Planned ([roadmap](docs/ROADMAP.md)), not claimed yet:
- **Cost-aware LLM routing** (M3): a rule-based router exists; the learned router and the quality-vs-cost numbers do not
- **Prompt-injection defences** (M4): a heuristic guard and a delimited prompt exist; the attack/defence benchmark does not
- **Cloud deployment and monitoring** (M5)

## Architecture
```
            ┌─ exact id lookup (CVE / technique / advisory named in the question)
query ─► guard ─► hybrid retrieval (BM25 + dense, RRF; French also searched in English) ─► rerank
            └─ link expansion (alerts: techniques tagged by the matching Sigma rules)
      ─► sanitise ─► router ─► LLM ─► cited answer ─► citation check

agent mode: the same retrieval runs first, then the LLM may call tools
            (lookup · kev_status · related · nvd · search) before it answers
```
Details: [docs/SPEC.md](docs/SPEC.md)

## Quickstart
```bash
git clone https://github.com/waliddoesthis/threatlens && cd threatlens
python -m venv .venv && source .venv/bin/activate
make install
cp .env.example .env          # set your model names / API key; VECTOR_STORE=qdrant|chroma
ollama pull llama3.1:8b       # local small model (https://ollama.com); use the ollama_chat/ prefix
make ingest                   # download ATT&CK, KEV, Sigma, CERT-FR at pinned versions
make index                    # build indexes
make ui                       # http://localhost:8501
```

## Results
Every number below comes from a pinned corpus (ATT&CK v20.1, Sigma r2026-07-01, a fixed KEV snapshot, pinned CERT-FR advisories: [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)), 5,711 documents / 6,094 chunks. Raw numbers in [eval/results/](eval/results/), reasoning in [docs/DECISIONS.md](docs/DECISIONS.md).

### Retrieval, 117 questions
[eval/questions.jsonl](eval/questions.jsonl): ATT&CK technique paraphrases, mitigations, CVE nicknames, "which Sigma rule detects X", alerts, CERT-FR advisories and French questions.

![Retrieval ablation](docs/img/retrieval.png)

| Retrieval | Recall@5 | 95% CI | MRR@10 | Δ Recall@5 vs hybrid (95% CI) |
|---|---|---|---|---|
| BM25 | 0.746 | 0.665–0.821 | 0.618 | −0.141 (−0.218 to −0.073) |
| Dense (bge-small-en-v1.5) | 0.875 | 0.813–0.929 | 0.734 | −0.013 (−0.051 to +0.026) |
| Hybrid (RRF) | 0.887 | 0.825–0.943 | 0.729 | – |
| Hybrid + cross-encoder rerank | 0.845 | 0.778–0.906 | 0.711 | −0.043 (−0.103 to +0.009) |
| Hybrid + rerank, RRF-fused | 0.905 | 0.848–0.956 | **0.741** | +0.017 (−0.017 to +0.051) |
| + link expansion and id lookup | 0.900 | 0.843–0.952 | 0.723 | +0.013 (−0.017 to +0.047) |
| + French query translation (default) | **0.943** | 0.900–0.983 | 0.739 | **+0.056 (+0.013 to +0.107)** |

Takeaways:
- **Most differences here are inside the noise.** With 117 questions, hybrid vs dense and the reranker's +0.017 have intervals that contain zero. Only "BM25 alone is worse" and "the full path beats plain hybrid" are supported. Earlier versions of this README called the reranker a win; the intervals say "not shown".
- **A reranker is not a free win.** On its own the cross-encoder ranks narrow Sigma rules above the ATT&CK technique a question is about, and scores below no reranker at all.
- **French went from 0 to 5 of 5** by translating the question with the small model and searching both wordings. A multilingual encoder alone had reached 0.2–0.4.
- **Per-type scores show what an average hides** ([by type](eval/results/retrieval.md)).

### Retrieval, 107 real alerts
The 5 alert questions above were written by hand and score 0.70. [eval/questions_alerts.jsonl](eval/questions_alerts.jsonl) is built from **Atomic Red Team**: real command lines, each labelled with the technique it exercises, never indexed ([how](eval/build_alert_questions.py)).

![Alert benchmark](docs/img/retrieval-alerts.png)

| Retrieval | Recall@5 | 95% CI |
|---|---|---|
| BM25 | 0.159 | 0.093–0.234 |
| Dense | 0.056 | 0.019–0.103 |
| Hybrid (RRF) | 0.103 | 0.047–0.168 |
| Hybrid + rerank, RRF-fused | 0.150 | 0.084–0.215 |
| + link expansion (default) | **0.327** | 0.243–0.411 |

- **The hand-written alerts were flattering.** On real command lines the retriever finds the right technique 15% of the time: `vssadmin.exe delete shadows /all /quiet` shares almost no words with a technique description.
- **Following links beats matching text.** Command lines do match Sigma rules, and each rule is tagged with its technique. Giving the last 3 places of the context to the techniques those rules point to doubles Recall@5 (paired Δ vs fused rerank +0.178, 95% CI +0.093 to +0.262; on the half of the questions not used to choose the setting: 0.132 → 0.302).
- **One alert in three is still weak**, and the gold label is strict (one sub-technique, no credit for its parent). This is the main retrieval gap left.
- A first design that re-ranked every question with the graph raised alerts but cut MRR on the 117 questions from 0.74 to 0.47. It was dropped ([decision](docs/DECISIONS.md)).

### Agent mode
`pipeline.answer(question, mode="agent")`, or the toggle in the UI. Retrieval and a KEV check on every CVE in the question run first; then the model may call `lookup`, `kev_status`, `related`, `nvd` or `search` (at most 4 turns) before it writes the answer. No framework: [agent.py](src/threatlens/agent.py) is a 150-line loop over tool calling.

**Not benchmarked yet.** It has unit tests with a scripted model and a 4-question trial with `llama3.1:8b` on CPU, which is a smoke test, not a result:
- Without the forced first retrieval, the 8B model made one tool call and then answered from memory: it looked up `T1505` for Kerberoasting (the technique is T1558.003) and cited a Sigma rule id that does not exist. That is why retrieval is no longer the model's choice.
- With it, the same question led to `related("T1558.003")` and an answer listing that technique's real Sigma rules and mitigations (M1026, M1027, M1041), and no invented citation was flagged in the 4 answers.
- It still mislabels technique names from memory and sometimes drops the `[source:id]` format. `make eval-answers-agent` scores it on the full benchmark; that run needs a GPU.

### Chunk size and embedding model
![Ablation](docs/img/ablation.png)

- **Chunk size (120 / 220 / 400 words) changes the scores by at most 0.014**, because most ATT&CK, KEV and Sigma records fit in one chunk at any of these sizes.
- **bge-base-en-v1.5 gains +0.015 Recall@5** (0.925) for 4× the build time and twice the vector size, so bge-small stays the default for CPU hosting. A bigger or multilingual encoder lifts French from 0 to only 0.2–0.4, so cross-lingual queries need query translation, not just a new model ([full table](eval/results/ablation.md)).

### Answer quality
Every answer is scored by an LLM judge (faithfulness = supported claims / claims, relevancy 1–5) **and** by deterministic checks: does it cite only ids it was given, does it cite the gold document, how many statements carry a citation, and does it state CVE / ATT&CK ids that appear in no source ([eval/run_answer_eval.py](eval/run_answer_eval.py)).

These numbers predate M2.5: they were measured before the corpus was pinned and through LiteLLM's `ollama/` route, which flattens the system prompt into plain text ([decision](docs/DECISIONS.md)); they are kept as measured and are due a re-run. Full run on 112 questions (the 5 CERT-FR questions were skipped because their advisories had rolled off that machine's feed). Generator `llama3.1:8b`, judge `qwen2.5:7b`, both on an 8 GB RTX 2070 via Ollama, at about 41 s per answer ([results](eval/results/answers-llama3.1-8b.md)):

| Generator | n | Faithfulness (judge) | Relevancy | Citation validity | Gold doc cited | Statements with a citation | Unsupported ids / answer |
|---|---|---|---|---|---|---|---|
| **llama3.1:8b** (GPU) | 112 | **0.875** | **4.61** | **0.974** | **0.765** | **0.444** | **0.14** |
| llama3.2:3b (CPU sample) | 10 | 0.929 | 4.50 | 1.000 (2 answers) | 0.200 | 0.068 | 1.20 |

- **The judge alone would have picked the wrong model.** It rated the 3B model *more* faithful (0.93 vs 0.88) while the 3B model cited the gold document 4× less often and stated 8× more ATT&CK / CVE ids that appear in no source. That is why the deterministic citation checks sit next to the judge.
- **llama3.1:8b grounds technique questions well** (faithfulness 0.95, gold cited 0.94) **but not detections** (gold Sigma rule cited 0.40). It cites the ATT&CK technique and skips the rule, which is the gap the M4 prompt work targets.
- **French is the weak spot end to end**: retrieval finds nothing, so faithfulness falls to 0.47 and relevancy to 2.8, even though the model honestly says the sources don't cover the question.
- These per-question rows ([jsonl](eval/results/answers-llama3.1-8b.jsonl)) are the training labels for the M3 router.

## Data
Public sources only — see [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md). ATT&CK® is a registered trademark of The MITRE Corporation.

## Author
Walid Ichchou — [walidichchou.dev](https://walidichchou.dev)
