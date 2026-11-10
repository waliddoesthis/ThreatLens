# ThreatLens 🔎

**RAG copilot for SOC & CTI analysts** — ask about an alert, a log line or a CVE and get a cited answer grounded in MITRE ATT&CK, CISA KEV, NVD, CERT-FR and SigmaHQ.

> Status: 🚧 work in progress — see [docs/ROADMAP.md](docs/ROADMAP.md)

## Highlights
Built and measured:
- **Hybrid retrieval**: BM25 + dense embeddings fused with RRF, cross-encoder reranking
- **Cited answers**: every claim points to its source (`[attack:T1059.001]`, `[kev:CVE-2024-3400]`)
- **Measured**: retrieval and answer-quality benchmark with ablations ([results](#results))
- **Runs anywhere**: FastAPI, Streamlit, Docker Compose, CI (ruff + pytest)

Planned ([roadmap](docs/ROADMAP.md)), not claimed yet:
- **Cost-aware LLM routing** (M3): a rule-based router exists; the learned router and the quality-vs-cost numbers do not
- **Prompt-injection defences** (M4): a heuristic guard and a delimited prompt exist; the attack/defence benchmark does not
- **Cloud deployment and monitoring** (M5)

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
Retrieval on a **117-question benchmark** ([eval/questions.jsonl](eval/questions.jsonl)): ATT&CK technique paraphrases, mitigations, CVE nicknames, "which Sigma rule detects X", raw alerts / log lines, CERT-FR advisories and French questions. Corpus: 5,718 documents / 6,100 chunks from ATT&CK, CISA KEV, SigmaHQ and CERT-FR. Raw numbers in [eval/results/](eval/results/), reasoning in [docs/DECISIONS.md](docs/DECISIONS.md).

![Retrieval ablation](docs/img/retrieval.png)

| Retrieval | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|
| BM25 | 0.742 | 0.843 | 0.615 | 0.665 |
| Dense (bge-small-en-v1.5) | 0.877 | 0.903 | 0.738 | 0.773 |
| Hybrid (RRF) | 0.893 | **0.936** | 0.738 | 0.783 |
| Hybrid + cross-encoder rerank | 0.850 | 0.919 | 0.711 | 0.758 |
| Hybrid + rerank, RRF-fused (default) | **0.910** | **0.936** | **0.741** | **0.787** |

Takeaways:
- **Hybrid beats either retriever alone**, and fusing the cross-encoder with the hybrid order (instead of replacing it) gives the best top 5 (by a small margin, ≈2 questions). The choice was made on 35 questions in M1 and **held on 82 new ones**.
- **A reranker is not a free win.** On its own the cross-encoder ranks narrow Sigma rules above the ATT&CK technique a question is about, and scores below no reranker at all.
- **Per-type scores show what an average hides:** detection questions reach R@5 1.00 and CVE nicknames 0.92, but raw alerts sit at 0.70 and **French questions score 0** with an English embedding model ([by type](eval/results/retrieval.md)).
- **Qdrant or Chroma** gave the same scores in M1 (35 questions): set `VECTOR_STORE=chroma` and rebuild ([results](eval/results/retrieval-chroma.md)).

### Chunk size and embedding model
![Ablation](docs/img/ablation.png)

- **Chunk size (120 / 220 / 400 words) changes the scores by at most 0.014**, because most ATT&CK, KEV and Sigma records fit in one chunk at any of these sizes.
- **bge-base-en-v1.5 gains +0.015 Recall@5** (0.925) for 4× the build time and twice the vector size, so bge-small stays the default for CPU hosting. A bigger or multilingual encoder lifts French from 0 to only 0.2–0.4, so cross-lingual queries need query translation, not just a new model ([full table](eval/results/ablation.md)).

### Answer quality
Every answer is scored by an LLM judge (faithfulness = supported claims / claims, relevancy 1–5) **and** by deterministic checks: does it cite only ids it was given, does it cite the gold document, how many statements carry a citation, and does it state CVE / ATT&CK ids that appear in no source ([eval/run_answer_eval.py](eval/run_answer_eval.py)).

Full run on 112 questions (the 5 CERT-FR questions were skipped because their advisories had rolled off that machine's feed). Generator `llama3.1:8b`, judge `qwen2.5:7b`, both on an 8 GB RTX 2070 via Ollama, at about 41 s per answer ([results](eval/results/answers-llama3.1-8b.md)):

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
