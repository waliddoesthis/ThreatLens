Generator: `ollama/llama3.1:8b` · judge: `ollama/qwen2.5:7b` · reranker: BAAI/bge-reranker-base · top 6 chunks · 7029 s total

| Scope | n | faithfulness | relevancy | citation_validity | gold_cited | statement_coverage | unsupported_ids | latency_ms | judge_failures |
|---|---|---|---|---|---|---|---|---|---|
| **all** | 112 | 0.875 | 4.609 | 0.974 | 0.765 | 0.444 | 0.143 | 41051.929 | 2 |
| alert | 5 | 0.739 | 4.400 | 1.000 | 0.750 | 0.258 | 0.200 | 41320.200 | 0 |
| cve | 25 | 0.842 | 4.320 | 0.899 | 0.783 | 0.521 | 0.600 | 37840.240 | 0 |
| detection | 20 | 0.837 | 4.579 | 1.000 | 0.400 | 0.130 | 0.000 | 43769.650 | 1 |
| french | 5 | 0.467 | 2.800 | 1.000 | – | 0.140 | 0.000 | 41637.200 | 0 |
| mitigation | 7 | 0.964 | 4.857 | 1.000 | 0.571 | 0.148 | 0.000 | 42869.857 | 0 |
| technique | 50 | 0.950 | 4.939 | 1.000 | 0.938 | 0.621 | 0.000 | 41230.820 | 1 |
