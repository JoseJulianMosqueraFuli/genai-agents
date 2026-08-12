import boto3
from typing import Dict, List

from app.config import get_settings
from app.logging_config import structured_log
from app.providers.base import LLMProvider, LLMResponse, LLMUsage, LLMProviderError


class BedrockProvider(LLMProvider):
    name = "bedrock"

    def __init__(self) -> None:
        settings = get_settings()
        self.session = boto3.Session(region_name=settings.bedrock_region)
        self.client = self.session.client("bedrock-runtime")
        self.model = settings.bedrock_model_id
        self.embedding_model = settings.embedding_model

    async def generate(self, system: str, user: str, **kwargs) -> LLMResponse:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": kwargs.get("max_tokens", 1024),
            "temperature": kwargs.get("temperature", 0.2),
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        try:
            resp = self.client.invoke_model(
                modelId=self.model, contentType="application/json", accept="*/*", body=body
            )
            import json

            data = json.loads(resp["body"].read())
            text = data.get("content", [{}])[0].get("text", "")
            usage = data.get("usage", {})
            usage_out = LLMUsage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
            )
            structured_log(
                "INFO",
                "bedrock.generate",
                model=self.model,
                input_tokens=usage_out.input_tokens,
                output_tokens=usage_out.output_tokens,
            )
            return LLMResponse(text=text, usage=usage_out, model=self.model, raw=data)
        except Exception as e:
            structured_log("ERROR", "bedrock.generate.error", error=str(e))
            raise LLMProviderError(str(e)) from e

    async def embed(self, texts: List[str]) -> List[List[float]]:
        raise LLMProviderError("Embeddings via Bedrock must use a deployed endpoint; configure OpenAI provider for embeddings")
