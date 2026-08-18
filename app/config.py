from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "genai-agents"
    environment: Literal["dev", "staging", "prod"] = "dev"

    llm_provider: Literal["openai", "bedrock"] = "openai"
    llm_model: str = "gpt-4o-mini"

    openai_api_key: str = ""
    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1"

    embedding_model: str = "text-embedding-3-small"
    embedding_provider: Literal["openai", "bedrock"] = "openai"

    enable_guardrails: bool = True
    max_context_tokens: int = 4000

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
