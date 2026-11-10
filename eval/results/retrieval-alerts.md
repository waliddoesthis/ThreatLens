n = 107 questions, vector store: qdrant, embeddings: BAAI/bge-small-en-v1.5, reranker: BAAI/bge-reranker-base, chunks: 220/40 words

Corpus: attack ATT&CK-v20.1 (750 docs); kev 2db0708eb3cd (1773 docs); sigma r2026-07-01 (3142 docs); certfr rss + 6 pinned advisories + local archive (46 docs)

| Mode | N | Recall@5 | Recall@10 | Mrr@10 | Ndcg@10 |
|---|---|---|---|---|---|
| bm25 | 107 | 0.159 | 0.159 | 0.078 | 0.098 |
| dense | 107 | 0.056 | 0.075 | 0.028 | 0.039 |
| hybrid | 107 | 0.103 | 0.168 | 0.056 | 0.082 |
| hybrid+rerank+rrf | 107 | 0.150 | 0.159 | 0.067 | 0.089 |
| graph | 107 | 0.327 | 0.355 | 0.109 | 0.168 |

## Uncertainty (2,000 bootstrap resamples of the questions)

| Mode | Recall@5 95% CI | MRR@10 95% CI | Δ Recall@5 vs hybrid (95% CI) |
|---|---|---|---|
| bm25 | 0.093–0.234 | 0.043–0.118 | +0.056 (-0.009 to +0.121) |
| dense | 0.019–0.103 | 0.009–0.057 | -0.047 (-0.093 to +0.000) |
| hybrid | 0.047–0.168 | 0.027–0.093 | – |
| hybrid+rerank+rrf | 0.084–0.215 | 0.036–0.108 | +0.047 (+0.009 to +0.093) |
| graph | 0.243–0.411 | 0.079–0.146 | +0.224 (+0.140 to +0.318) |

## By question type

| Mode | Type | N | Recall@5 | Recall@10 | Mrr@10 | Ndcg@10 |
|---|---|---|---|---|---|---|
| bm25 | alert_atomic | 107 | 0.159 | 0.159 | 0.078 | 0.098 |
| dense | alert_atomic | 107 | 0.056 | 0.075 | 0.028 | 0.039 |
| hybrid | alert_atomic | 107 | 0.103 | 0.168 | 0.056 | 0.082 |
| hybrid+rerank+rrf | alert_atomic | 107 | 0.150 | 0.159 | 0.067 | 0.089 |
| graph | alert_atomic | 107 | 0.327 | 0.355 | 0.109 | 0.168 |
