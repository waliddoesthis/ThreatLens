n = 117 questions, vector store: qdrant, reranker: BAAI/bge-reranker-base

## Chunk ablation

| config | chunks | mode | n | recall@5 | recall@10 | mrr@10 | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bge-small-en-v1.5_120w | 7404 | dense | 117 | 0.877 | 0.915 | 0.697 | 0.746 |
| bge-small-en-v1.5_120w | 7404 | hybrid | 117 | 0.906 | 0.932 | 0.743 | 0.786 |
| bge-small-en-v1.5_120w | 7404 | hybrid+rerank+rrf | 117 | 0.885 | 0.940 | 0.771 | 0.810 |
| bge-small-en-v1.5_220w | 6153 | dense | 117 | 0.869 | 0.912 | 0.742 | 0.779 |
| bge-small-en-v1.5_220w | 6153 | hybrid | 117 | 0.868 | 0.936 | 0.740 | 0.785 |
| bge-small-en-v1.5_220w | 6153 | hybrid+rerank+rrf | 117 | 0.893 | 0.927 | 0.759 | 0.799 |
| bge-small-en-v1.5_400w | 5806 | dense | 117 | 0.869 | 0.903 | 0.740 | 0.775 |
| bge-small-en-v1.5_400w | 5806 | hybrid | 117 | 0.868 | 0.936 | 0.726 | 0.775 |
| bge-small-en-v1.5_400w | 5806 | hybrid+rerank+rrf | 117 | 0.893 | 0.927 | 0.756 | 0.796 |

## Embedding ablation

| config | chunks | mode | n | recall@5 | recall@10 | mrr@10 | ndcg@10 |
|---|---|---|---|---|---|---|---|
| bge-small-en-v1.5_220w | 6153 | dense | 117 | 0.869 | 0.912 | 0.742 | 0.779 |
| bge-small-en-v1.5_220w | 6153 | hybrid | 117 | 0.868 | 0.936 | 0.740 | 0.785 |
| bge-small-en-v1.5_220w | 6153 | hybrid+rerank+rrf | 117 | 0.893 | 0.927 | 0.759 | 0.799 |
| bge-base-en-v1.5_220w | 6153 | dense | 117 | 0.895 | 0.929 | 0.718 | 0.764 |
| bge-base-en-v1.5_220w | 6153 | hybrid | 117 | 0.865 | 0.950 | 0.731 | 0.781 |
| bge-base-en-v1.5_220w | 6153 | hybrid+rerank+rrf | 117 | 0.916 | 0.944 | 0.778 | 0.816 |
| multilingual-e5-small_220w | 6153 | dense | 117 | 0.805 | 0.873 | 0.680 | 0.720 |
| multilingual-e5-small_220w | 6153 | hybrid | 117 | 0.860 | 0.897 | 0.721 | 0.758 |
| multilingual-e5-small_220w | 6153 | hybrid+rerank+rrf | 117 | 0.880 | 0.915 | 0.759 | 0.791 |
