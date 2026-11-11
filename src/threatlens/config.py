"""Central settings, loaded from environment / .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Models
    # ollama_chat/ (not ollama/): LiteLLM's ollama/ route flattens the messages into one prompt
    # ("### System: ..."), so the system prompt is not a real system turn and tools do not work
    small_model: str = "ollama_chat/llama3.1:8b"
    large_model: str = "anthropic/claude-sonnet-4-5"
    judge_model: str = ""  # LLM-as-judge for the answer eval; empty = large_model

    # Retrieval
    vector_store: str = "qdrant"  # qdrant | chroma
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    # instruction prefixes for embedding queries/passages; "auto" picks them from the model name
    query_prefix: str = "auto"
    passage_prefix: str = "auto"
    reranker_model: str = "BAAI/bge-reranker-base"
    use_reranker: bool = True
    rerank_fusion: bool = True  # RRF(hybrid order, cross-encoder order)
    top_k_retrieve: int = 30
    top_k_final: int = 6
    graph_expansion: bool = True  # link expansion (Sigma -> technique) + exact id lookup
    graph_top_n: int = 3  # techniques added from the Sigma rules' tags
    translate_queries: bool = True  # search French questions in English too (one small-LLM call)
    chunk_size_words: int = 220
    chunk_overlap_words: int = 40

    # Data
    data_dir: Path = Path("data")
    index_path: Path | None = None  # default data/index; the M2 ablations build one per config
    nvd_api_key: str = ""
    data_pin: str = "pinned"  # pinned (versions in ingest/pins.py) | latest (track upstream)

    # Agent
    answer_mode: str = "pipeline"  # pipeline (fixed chain) | agent (model chooses tools)
    agent_max_steps: int = 4  # tool-calling turns before the answer is written
    agent_max_sources: int = 8  # documents the answer is written from (seeded ones first)

    # Public demo (0 = no cap): questions per UTC day for everybody, and per browser session
    demo_daily_limit: int = 0
    demo_session_limit: int = 0

    # Router
    router_mode: str = "rules"  # rules | always_small | always_large
    # best cross-encoder score (0-1) below which the small model is not trusted with the answer
    router_min_confidence: float = 0.3

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def index_dir(self) -> Path:
        return self.index_path or self.data_dir / "index"


settings = Settings()
