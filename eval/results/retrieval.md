n = 117 questions, vector store: qdrant, embeddings: BAAI/bge-small-en-v1.5, reranker: BAAI/bge-reranker-base, chunks: 220/40 words

| Mode | N | Recall@5 | Recall@10 | Mrr@10 | Ndcg@10 |
|---|---|---|---|---|---|
| bm25 | 117 | 0.742 | 0.843 | 0.615 | 0.665 |
| dense | 117 | 0.877 | 0.903 | 0.738 | 0.773 |
| hybrid | 117 | 0.893 | 0.936 | 0.738 | 0.783 |
| hybrid+rerank | 117 | 0.850 | 0.919 | 0.711 | 0.758 |
| hybrid+rerank+rrf | 117 | 0.910 | 0.936 | 0.741 | 0.787 |

## By question type

| Mode | Type | N | Recall@5 | Recall@10 | Mrr@10 | Ndcg@10 |
|---|---|---|---|---|---|---|
| bm25 | technique | 50 | 0.800 | 0.920 | 0.634 | 0.702 |
| bm25 | mitigation | 7 | 0.857 | 0.857 | 0.762 | 0.786 |
| bm25 | cve | 25 | 0.840 | 0.920 | 0.672 | 0.732 |
| bm25 | detection | 20 | 0.667 | 0.833 | 0.557 | 0.622 |
| bm25 | alert | 5 | 0.400 | 0.400 | 0.500 | 0.400 |
| bm25 | certfr | 5 | 0.900 | 1.000 | 0.900 | 0.890 |
| bm25 | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| dense | technique | 50 | 0.940 | 0.960 | 0.772 | 0.819 |
| dense | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| dense | cve | 25 | 0.840 | 0.920 | 0.677 | 0.735 |
| dense | detection | 20 | 0.933 | 0.933 | 0.754 | 0.789 |
| dense | alert | 5 | 0.800 | 0.800 | 0.850 | 0.731 |
| dense | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid | technique | 50 | 0.960 | 0.980 | 0.774 | 0.826 |
| hybrid | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| hybrid | cve | 25 | 0.920 | 0.960 | 0.740 | 0.793 |
| hybrid | detection | 20 | 0.900 | 1.000 | 0.711 | 0.784 |
| hybrid | alert | 5 | 0.700 | 0.900 | 0.672 | 0.653 |
| hybrid | certfr | 5 | 1.000 | 1.000 | 1.000 | 0.975 |
| hybrid | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid+rerank | technique | 50 | 0.900 | 0.960 | 0.724 | 0.782 |
| hybrid+rerank | mitigation | 7 | 1.000 | 1.000 | 0.786 | 0.842 |
| hybrid+rerank | cve | 25 | 0.840 | 0.960 | 0.747 | 0.796 |
| hybrid+rerank | detection | 20 | 0.950 | 1.000 | 0.738 | 0.800 |
| hybrid+rerank | alert | 5 | 0.500 | 0.700 | 0.622 | 0.567 |
| hybrid+rerank | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid+rerank | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid+rerank+rrf | technique | 50 | 0.960 | 0.980 | 0.771 | 0.824 |
| hybrid+rerank+rrf | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| hybrid+rerank+rrf | cve | 25 | 0.920 | 0.960 | 0.750 | 0.802 |
| hybrid+rerank+rrf | detection | 20 | 1.000 | 1.000 | 0.725 | 0.793 |
| hybrid+rerank+rrf | alert | 5 | 0.700 | 0.900 | 0.675 | 0.672 |
| hybrid+rerank+rrf | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid+rerank+rrf | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
