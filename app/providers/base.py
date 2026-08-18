from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMResponse:
    text: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    model: str = ""
    raw: dict = field(default_factory=dict)


class LLMProviderError(Exception):
    pass


class LLMProvider(ABC):
    """Strategy for talking to a hosted LLM (OpenAI, Bedrock, ...)."""

    name: str = "base"

    @abstractmethod
    async def generate(self, system: str, user: str, **kwargs) -> LLMResponse:
        """Generate a completion from a system prompt and a user prompt."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vectors."""
