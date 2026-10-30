n = 35 questions, vector store: chroma

| Mode | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|
| bm25 | 0.686 | 0.857 | 0.547 | 0.620 |
| dense | 0.914 | 0.971 | 0.750 | 0.804 |
| hybrid | 0.943 | 1.000 | 0.746 | 0.809 |
| hybrid+rerank | 0.857 | 0.943 | 0.686 | 0.747 |
| hybrid+rerank+rrf | 0.943 | 0.971 | 0.815 | 0.854 |
