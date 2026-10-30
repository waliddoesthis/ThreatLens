"""Central settings, loaded from environment / .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Models
    small_model: str = "ollama/llama3.1:8b"
    large_model: str = "anthropic/claude-sonnet-4-5"

    # Retrieval
    vector_store: str = "qdrant"  # qdrant | chroma
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "BAAI/bge-reranker-base"
    use_reranker: bool = True
    rerank_fusion: bool = True  # RRF(hybrid order, cross-encoder order)
    top_k_retrieve: int = 30
    top_k_final: int = 6
    chunk_size_words: int = 220
    chunk_overlap_words: int = 40

    # Data
    data_dir: Path = Path("data")
    nvd_api_key: str = ""

    # Router
    router_mode: str = "rules"  # rules | always_small | always_large

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"


settings = Settings()
