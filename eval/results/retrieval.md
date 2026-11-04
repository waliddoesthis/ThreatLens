n = 117 questions, vector store: qdrant, embeddings: BAAI/bge-small-en-v1.5, reranker: BAAI/bge-reranker-base, chunks: 220/40 words

| Mode | N | Recall@5 | Recall@10 | Mrr@10 | Ndcg@10 |
|---|---|---|---|---|---|
| bm25 | 117 | 0.754 | 0.843 | 0.598 | 0.652 |
| dense | 117 | 0.869 | 0.912 | 0.742 | 0.779 |
| hybrid | 117 | 0.868 | 0.936 | 0.740 | 0.785 |
| hybrid+rerank | 117 | 0.842 | 0.902 | 0.700 | 0.746 |
| hybrid+rerank+rrf | 117 | 0.893 | 0.927 | 0.759 | 0.799 |

## By question type

| Mode | Type | N | Recall@5 | Recall@10 | Mrr@10 | Ndcg@10 |
|---|---|---|---|---|---|---|
| bm25 | technique | 50 | 0.820 | 0.920 | 0.591 | 0.670 |
| bm25 | mitigation | 7 | 0.857 | 0.857 | 0.786 | 0.804 |
| bm25 | cve | 25 | 0.840 | 0.920 | 0.672 | 0.732 |
| bm25 | detection | 20 | 0.683 | 0.833 | 0.556 | 0.622 |
| bm25 | alert | 5 | 0.400 | 0.400 | 0.500 | 0.384 |
| bm25 | certfr | 5 | 0.900 | 1.000 | 0.900 | 0.892 |
| bm25 | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| dense | technique | 50 | 0.920 | 0.980 | 0.790 | 0.836 |
| dense | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| dense | cve | 25 | 0.840 | 0.920 | 0.677 | 0.735 |
| dense | detection | 20 | 0.933 | 0.933 | 0.758 | 0.793 |
| dense | alert | 5 | 0.800 | 0.800 | 0.750 | 0.686 |
| dense | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid | technique | 50 | 0.940 | 0.980 | 0.782 | 0.831 |
| hybrid | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| hybrid | cve | 25 | 0.920 | 0.960 | 0.740 | 0.793 |
| hybrid | detection | 20 | 0.850 | 1.000 | 0.710 | 0.782 |
| hybrid | alert | 5 | 0.500 | 0.900 | 0.656 | 0.638 |
| hybrid | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid+rerank | technique | 50 | 0.880 | 0.940 | 0.711 | 0.768 |
| hybrid+rerank | mitigation | 7 | 1.000 | 1.000 | 0.714 | 0.789 |
| hybrid+rerank | cve | 25 | 0.840 | 0.920 | 0.743 | 0.785 |
| hybrid+rerank | detection | 20 | 0.950 | 1.000 | 0.729 | 0.794 |
| hybrid+rerank | alert | 5 | 0.500 | 0.700 | 0.625 | 0.570 |
| hybrid+rerank | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid+rerank | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid+rerank+rrf | technique | 50 | 0.920 | 0.960 | 0.814 | 0.850 |
| hybrid+rerank+rrf | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| hybrid+rerank+rrf | cve | 25 | 0.920 | 0.960 | 0.750 | 0.802 |
| hybrid+rerank+rrf | detection | 20 | 1.000 | 1.000 | 0.725 | 0.793 |
| hybrid+rerank+rrf | alert | 5 | 0.700 | 0.900 | 0.679 | 0.675 |
| hybrid+rerank+rrf | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid+rerank+rrf | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
