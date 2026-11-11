n = 117 questions, vector store: qdrant, embeddings: BAAI/bge-small-en-v1.5, reranker: BAAI/bge-reranker-base, chunks: 220/40 words

Corpus: attack ATT&CK-v20.1 (750 docs); kev 2db0708eb3cd (1773 docs); sigma r2026-07-01 (3142 docs); certfr rss + 6 pinned advisories + local archive (46 docs)

| Mode | N | Recall@5 | Recall@10 | Mrr@10 | Ndcg@10 |
|---|---|---|---|---|---|
| bm25 | 117 | 0.746 | 0.849 | 0.618 | 0.670 |
| dense | 117 | 0.875 | 0.900 | 0.734 | 0.768 |
| hybrid | 117 | 0.887 | 0.930 | 0.729 | 0.774 |
| hybrid+rerank | 117 | 0.845 | 0.913 | 0.711 | 0.754 |
| hybrid+rerank+rrf | 117 | 0.905 | 0.930 | 0.741 | 0.783 |
| graph | 117 | 0.900 | 0.934 | 0.723 | 0.772 |
| graph+translate | 117 | 0.943 | 0.977 | 0.739 | 0.794 |

## Uncertainty (2,000 bootstrap resamples of the questions)

| Mode | Recall@5 95% CI | MRR@10 95% CI | Δ Recall@5 vs hybrid (95% CI) |
|---|---|---|---|
| bm25 | 0.665–0.821 | 0.543–0.690 | -0.141 (-0.218 to -0.073) |
| dense | 0.813–0.929 | 0.665–0.798 | -0.013 (-0.051 to +0.026) |
| hybrid | 0.825–0.943 | 0.664–0.792 | – |
| hybrid+rerank | 0.778–0.906 | 0.645–0.781 | -0.043 (-0.103 to +0.009) |
| hybrid+rerank+rrf | 0.848–0.956 | 0.678–0.805 | +0.017 (-0.017 to +0.051) |
| graph | 0.843–0.952 | 0.660–0.788 | +0.013 (-0.017 to +0.047) |
| graph+translate | 0.900–0.983 | 0.683–0.799 | +0.056 (+0.013 to +0.107) |

## By question type

| Mode | Type | N | Recall@5 | Recall@10 | Mrr@10 | Ndcg@10 |
|---|---|---|---|---|---|---|
| bm25 | technique | 50 | 0.800 | 0.940 | 0.636 | 0.708 |
| bm25 | mitigation | 7 | 0.857 | 0.857 | 0.762 | 0.786 |
| bm25 | cve | 25 | 0.840 | 0.920 | 0.685 | 0.742 |
| bm25 | detection | 20 | 0.667 | 0.817 | 0.561 | 0.615 |
| bm25 | alert | 5 | 0.400 | 0.400 | 0.467 | 0.384 |
| bm25 | certfr | 5 | 1.000 | 1.000 | 0.900 | 0.926 |
| bm25 | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| dense | technique | 50 | 0.940 | 0.960 | 0.762 | 0.812 |
| dense | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| dense | cve | 25 | 0.840 | 0.920 | 0.677 | 0.735 |
| dense | detection | 20 | 0.917 | 0.917 | 0.754 | 0.778 |
| dense | alert | 5 | 0.800 | 0.800 | 0.850 | 0.731 |
| dense | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| dense | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid | technique | 50 | 0.960 | 0.980 | 0.766 | 0.820 |
| hybrid | mitigation | 7 | 1.000 | 1.000 | 0.833 | 0.876 |
| hybrid | cve | 25 | 0.920 | 0.960 | 0.740 | 0.793 |
| hybrid | detection | 20 | 0.867 | 0.967 | 0.711 | 0.765 |
| hybrid | alert | 5 | 0.700 | 0.900 | 0.672 | 0.653 |
| hybrid | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid+rerank | technique | 50 | 0.900 | 0.960 | 0.734 | 0.789 |
| hybrid+rerank | mitigation | 7 | 1.000 | 1.000 | 0.786 | 0.842 |
| hybrid+rerank | cve | 25 | 0.840 | 0.960 | 0.747 | 0.796 |
| hybrid+rerank | detection | 20 | 0.917 | 0.967 | 0.713 | 0.757 |
| hybrid+rerank | alert | 5 | 0.500 | 0.700 | 0.622 | 0.567 |
| hybrid+rerank | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid+rerank | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid+rerank+rrf | technique | 50 | 0.960 | 0.980 | 0.771 | 0.824 |
| hybrid+rerank+rrf | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| hybrid+rerank+rrf | cve | 25 | 0.920 | 0.960 | 0.750 | 0.802 |
| hybrid+rerank+rrf | detection | 20 | 0.967 | 0.967 | 0.725 | 0.769 |
| hybrid+rerank+rrf | alert | 5 | 0.700 | 0.900 | 0.675 | 0.672 |
| hybrid+rerank+rrf | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| hybrid+rerank+rrf | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| graph | technique | 50 | 0.960 | 0.980 | 0.732 | 0.794 |
| graph | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| graph | cve | 25 | 0.920 | 0.960 | 0.750 | 0.802 |
| graph | detection | 20 | 0.917 | 0.967 | 0.717 | 0.762 |
| graph | alert | 5 | 0.800 | 1.000 | 0.692 | 0.731 |
| graph | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| graph | french | 5 | 0.000 | 0.000 | 0.000 | 0.000 |
| graph+translate | technique | 50 | 0.960 | 0.980 | 0.732 | 0.794 |
| graph+translate | mitigation | 7 | 1.000 | 1.000 | 0.929 | 0.947 |
| graph+translate | cve | 25 | 0.920 | 0.960 | 0.750 | 0.802 |
| graph+translate | detection | 20 | 0.917 | 0.967 | 0.717 | 0.762 |
| graph+translate | alert | 5 | 0.800 | 1.000 | 0.692 | 0.731 |
| graph+translate | certfr | 5 | 1.000 | 1.000 | 1.000 | 1.000 |
| graph+translate | french | 5 | 1.000 | 1.000 | 0.373 | 0.530 |
