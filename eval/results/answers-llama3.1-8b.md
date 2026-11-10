Generator: `ollama_chat/llama3.1:8b` (pipeline) · judge: `ollama_chat/qwen2.5:7b` · reranker: BAAI/bge-reranker-base · top 6 chunks · 7121 s total

| Scope | n | faithfulness | relevancy | citation_validity | gold_cited | statement_coverage | unsupported_ids | latency_ms | judge_failures |
|---|---|---|---|---|---|---|---|---|---|
| **all** | 117 | 0.885 | 4.638 | 0.980 | 0.779 | 0.419 | 0.282 | 40733.547 | 1 |
| alert | 5 | 0.697 | 4.000 | 1.000 | 0.500 | 0.275 | 0.000 | 41213.000 | 1 |
| certfr | 5 | 0.850 | 4.800 | 0.750 | 0.400 | 0.256 | 1.800 | 40427.800 | 0 |
| cve | 25 | 0.854 | 4.240 | 0.990 | 0.875 | 0.515 | 0.880 | 36590.600 | 0 |
| detection | 20 | 0.882 | 4.550 | 1.000 | 0.400 | 0.137 | 0.000 | 41740.300 | 0 |
| french | 5 | 0.950 | 4.800 | 1.000 | 0.600 | 0.251 | 0.000 | 47831.400 | 0 |
| mitigation | 7 | 0.838 | 4.714 | 1.000 | 0.857 | 0.429 | 0.286 | 38900.571 | 0 |
| technique | 50 | 0.920 | 4.880 | 0.986 | 0.958 | 0.531 | 0.000 | 41931.780 | 0 |
