from app.config import get_settings
from app.providers.base import LLMProvider, LLMProviderError
from app.providers.bedrock import BedrockProvider
from app.providers.openai import OpenAIProvider


def get_provider(name: str | None = None) -> LLMProvider:
    settings = get_settings()
    provider_name = name or settings.llm_provider
    if provider_name == "openai":
        return OpenAIProvider()
    if provider_name == "bedrock":
        return BedrockProvider()
    raise LLMProviderError(f"Unknown LLM provider: {provider_name}")
