from __future__ import annotations

from openai import OpenAI

from ..base import LLMProvider


class OpenAILLMProvider(LLMProvider):
    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        base_url: str | None = None,
        max_output_tokens: int = 12_000,
        temperature: float | None = None,
    ):
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.temperature = temperature
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(self, prompt: str) -> str:
        request: dict[str, object] = {
            "model": self.model,
            "input": prompt,
            "max_output_tokens": self.max_output_tokens,
            "store": False,
        }
        if self.temperature is not None:
            request["temperature"] = self.temperature
        response = self.client.responses.create(**request)
        output = response.output_text
        if not output:
            raise RuntimeError(f"Model {self.model} returned no text output")
        return output


def openai_provider(
    *,
    model: str,
    api_key: str,
    base_url: str | None,
    max_output_tokens: int,
    temperature: float | None,
) -> OpenAILLMProvider:
    return OpenAILLMProvider(
        model=model,
        api_key=api_key,
        base_url=base_url,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )
