from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "genai-agents"
    environment: Literal["dev", "staging", "prod"] = "dev"

    # Single provider: Amazon Bedrock (Converse API for generation, Titan v2 for
    # embeddings). Kept as a field so the value surfaces in responses/health/logs.
    llm_provider: Literal["bedrock"] = "bedrock"
    bedrock_region: str = "us-east-1"
    # Generation: Amazon Nova. Bedrock usually requires the region-prefixed
    # inference profile id (e.g. "us.amazon.nova-pro-v1:0").
    bedrock_model_id: str = "us.amazon.nova-pro-v1:0"

    # Embeddings: Amazon Titan Text Embeddings V2 (Nova has no embeddings model).
    bedrock_embedding_model: str = "amazon.titan-embed-text-v2:0"
    embedding_dimension: int = 1024

    # Model tiering: cheap tier (Nova Micro) for short/factual queries, strong tier
    # (bedrock_model_id / Nova Pro) for reasoning.
    bedrock_cheap_model: str = "us.amazon.nova-micro-v1:0"

    enable_guardrails: bool = True
    max_context_tokens: int = 4000

    # RAG retrieval: "in_memory" (default) or "s3_vectors" (Amazon S3 Vectors).
    vector_backend: Literal["in_memory", "s3_vectors"] = "in_memory"
    s3_vectors_bucket: str = ""
    s3_vectors_index: str = ""
    retrieval_top_k: int = 4

    # Conversation memory: "in_memory" (default) or "agentcore" (Bedrock AgentCore Memory).
    memory_backend: Literal["in_memory", "agentcore"] = "in_memory"
    agentcore_memory_id: str = ""
    # Logical end-user id used to scope AgentCore Memory events.
    agentcore_actor_id: str = "user"
    # Max prior turns injected into the prompt for multi-turn coherence.
    memory_window: int = 6

    cost_per_1k_input_tokens: float = 0.00015
    cost_per_1k_output_tokens: float = 0.0006

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
