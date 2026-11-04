n = 117 questions, vector store: qdrant, reranker: BAAI/bge-reranker-base

## Chunk ablation

| config | chunks | mode | n | recall@5 | recall@10 | mrr@10 | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bge-small-en-v1.5_120w | 7293 | dense | 117 | 0.869 | 0.915 | 0.693 | 0.742 |
| bge-small-en-v1.5_120w | 7293 | hybrid | 117 | 0.897 | 0.949 | 0.717 | 0.772 |
| bge-small-en-v1.5_120w | 7293 | hybrid+rerank+rrf | 117 | 0.897 | 0.940 | 0.760 | 0.803 |
| bge-small-en-v1.5_220w | 6100 | dense | 117 | 0.877 | 0.903 | 0.738 | 0.773 |
| bge-small-en-v1.5_220w | 6100 | hybrid | 117 | 0.893 | 0.936 | 0.738 | 0.783 |
| bge-small-en-v1.5_220w | 6100 | hybrid+rerank+rrf | 117 | 0.910 | 0.936 | 0.741 | 0.787 |
| bge-small-en-v1.5_400w | 5803 | dense | 117 | 0.877 | 0.903 | 0.751 | 0.783 |
| bge-small-en-v1.5_400w | 5803 | hybrid | 117 | 0.868 | 0.936 | 0.740 | 0.785 |
| bge-small-en-v1.5_400w | 5803 | hybrid+rerank+rrf | 117 | 0.910 | 0.936 | 0.755 | 0.797 |

## Embedding ablation

| config | chunks | mode | n | recall@5 | recall@10 | mrr@10 | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bge-small-en-v1.5_220w | 6100 | dense | 117 | 0.877 | 0.903 | 0.738 | 0.773 |
| bge-small-en-v1.5_220w | 6100 | hybrid | 117 | 0.893 | 0.936 | 0.738 | 0.783 |
| bge-small-en-v1.5_220w | 6100 | hybrid+rerank+rrf | 117 | 0.910 | 0.936 | 0.741 | 0.787 |
| bge-base-en-v1.5_220w | 6100 | dense | 117 | 0.877 | 0.929 | 0.703 | 0.753 |
| bge-base-en-v1.5_220w | 6100 | hybrid | 117 | 0.882 | 0.950 | 0.719 | 0.773 |
| bge-base-en-v1.5_220w | 6100 | hybrid+rerank+rrf | 117 | 0.925 | 0.944 | 0.758 | 0.802 |
| multilingual-e5-small_220w | 6100 | dense | 117 | 0.822 | 0.873 | 0.660 | 0.705 |
| multilingual-e5-small_220w | 6100 | hybrid | 117 | 0.863 | 0.932 | 0.729 | 0.772 |
| multilingual-e5-small_220w | 6100 | hybrid+rerank+rrf | 117 | 0.906 | 0.936 | 0.761 | 0.799 |
