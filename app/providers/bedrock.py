import json

import boto3

from app.config import get_settings
from app.logging_config import structured_log
from app.providers.base import LLMProvider, LLMProviderError, LLMResponse, LLMUsage


class BedrockProvider(LLMProvider):
    """Amazon Bedrock provider.

    Generation uses the **Converse API**, which is model-agnostic — the same call
    works for Amazon Nova, Anthropic Claude, Meta Llama, etc. Embeddings use Amazon
    Titan Text Embeddings V2 (Nova has no embeddings model).
    """

    name = "bedrock"

    def __init__(self) -> None:
        settings = get_settings()
        self.session = boto3.Session(region_name=settings.bedrock_region)
        self.client = self.session.client("bedrock-runtime")
        self.model = settings.bedrock_model_id
        self.embedding_model = settings.bedrock_embedding_model
        self.embedding_dimension = settings.embedding_dimension

    async def generate(self, system: str, user: str, **kwargs) -> LLMResponse:
        # `model` override lets the tiering router pick cheap vs strong per request.
        model = kwargs.get("model") or self.model
        try:
            resp = self.client.converse(
                modelId=model,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user}]}],
                inferenceConfig={
                    "maxTokens": kwargs.get("max_tokens", 1024),
                    "temperature": kwargs.get("temperature", 0.2),
                },
            )
            content = resp["output"]["message"]["content"]
            text = content[0].get("text", "") if content else ""
            usage = resp.get("usage", {})
            usage_out = LLMUsage(
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
            )
            structured_log(
                "INFO",
                "bedrock.generate",
                model=model,
                input_tokens=usage_out.input_tokens,
                output_tokens=usage_out.output_tokens,
            )
            return LLMResponse(text=text, usage=usage_out, model=model, raw=resp)
        except Exception as e:
            structured_log("ERROR", "bedrock.generate.error", error=str(e))
            raise LLMProviderError(str(e)) from e

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Titan Text Embeddings V2 embeds one input per invocation.
        try:
            vectors: list[list[float]] = []
            for text in texts:
                body = json.dumps(
                    {
                        "inputText": text,
                        "dimensions": self.embedding_dimension,
                        "normalize": True,
                    }
                )
                resp = self.client.invoke_model(
                    modelId=self.embedding_model,
                    contentType="application/json",
                    accept="application/json",
                    body=body,
                )
                data = json.loads(resp["body"].read())
                vectors.append(data["embedding"])
            structured_log("INFO", "bedrock.embed", model=self.embedding_model, count=len(vectors))
            return vectors
        except Exception as e:
            structured_log("ERROR", "bedrock.embed.error", error=str(e))
            raise LLMProviderError(str(e)) from e
