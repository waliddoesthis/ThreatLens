Generator: `ollama_chat/llama3.1:8b` (agent) · judge: `ollama_chat/qwen2.5:7b` · reranker: BAAI/bge-reranker-base · top 6 chunks · 8130 s total

| Scope | n | faithfulness | relevancy | citation_validity | gold_cited | statement_coverage | unsupported_ids | latency_ms | judge_failures |
|---|---|---|---|---|---|---|---|---|---|
| **all** | 117 | 0.879 | 4.434 | 0.944 | 0.239 | 0.094 | 0.068 | 47325.761 | 14 |
| alert | 5 | 0.783 | 4.200 | – | 0.000 | 0.000 | 0.000 | 46051.000 | 0 |
| certfr | 5 | 0.933 | 4.600 | 0.500 | 0.200 | 0.106 | 0.800 | 47051.200 | 0 |
| cve | 25 | 0.788 | 3.958 | 0.933 | 0.333 | 0.113 | 0.160 | 46918.320 | 0 |
| detection | 20 | 0.874 | 4.533 | 1.000 | 0.200 | 0.154 | 0.000 | 49608.250 | 4 |
| french | 5 | 0.708 | 4.200 | – | 0.000 | 0.000 | 0.000 | 56311.800 | 0 |
| mitigation | 7 | 0.933 | 4.667 | – | 0.000 | 0.000 | 0.000 | 46407.571 | 1 |
| technique | 50 | 0.955 | 4.692 | 0.982 | 0.292 | 0.091 | 0.000 | 46001.360 | 9 |
