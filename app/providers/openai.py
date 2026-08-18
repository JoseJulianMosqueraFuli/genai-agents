import openai

from app.config import get_settings
from app.logging_config import structured_log
from app.providers.base import LLMProvider, LLMProviderError, LLMResponse, LLMUsage


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise LLMProviderError("OPENAI_API_KEY is not set")
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.llm_model
        self.embedding_model = settings.embedding_model

    async def generate(self, system: str, user: str, **kwargs) -> LLMResponse:
        # `model` override lets the tiering router pick cheap vs strong per request.
        model = kwargs.get("model") or self.model
        try:
            resp = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", 1024),
            )
            usage = resp.usage
            usage_out = LLMUsage(
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
            )
            structured_log(
                "INFO",
                "openai.generate",
                model=model,
                input_tokens=usage_out.input_tokens,
                output_tokens=usage_out.output_tokens,
            )
            return LLMResponse(
                text=resp.choices[0].message.content or "",
                usage=usage_out,
                model=model,
            )
        except Exception as e:
            structured_log("ERROR", "openai.generate.error", error=str(e))
            raise LLMProviderError(str(e)) from e

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            resp = await self.client.embeddings.create(model=self.embedding_model, input=texts)
            return [d.embedding for d in resp.data]
        except Exception as e:
            structured_log("ERROR", "openai.embed.error", error=str(e))
            raise LLMProviderError(str(e)) from e
