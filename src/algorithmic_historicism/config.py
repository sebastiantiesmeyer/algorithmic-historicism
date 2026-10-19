from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class LLMSettings(BaseModel):
    provider: str = "openai"
    agent_model: str
    consolidator_model: str
    api_key: str
    base_url: str | None = None
    max_output_tokens: int = Field(default=12_000, ge=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)

    @classmethod
    def from_env(
        cls, env_file: Path = Path(".env"), *, model_overrides: dict[str, object] | None = None
    ) -> "LLMSettings":
        load_dotenv(dotenv_path=env_file, override=False)
        overrides = model_overrides or {}
        provider = os.getenv("AH_LLM_PROVIDER", "openai").strip().lower()
        if provider != "openai":
            raise ValueError(f"Unsupported AH_LLM_PROVIDER: {provider}")
        agent_model = str(overrides.get("agent_model", os.getenv("AH_AGENT_MODEL", ""))).strip()
        if not agent_model:
            raise ValueError("AH_AGENT_MODEL is required; set it in .env or the environment")
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required; set it in .env or the environment")
        consolidator_model = (
            str(overrides.get("consolidator_model") or agent_model)
            if "agent_model" in overrides
            else os.getenv("AH_CONSOLIDATOR_MODEL", "").strip() or agent_model
        )
        max_output_tokens = overrides.get("max_output_tokens")
        if "max_output_tokens" not in overrides:
            max_output_tokens = int(os.getenv("AH_LLM_MAX_OUTPUT_TOKENS", "12000"))
        temperature = overrides.get("temperature")
        if "temperature" not in overrides:
            temperature_text = os.getenv("AH_LLM_TEMPERATURE", "").strip()
            temperature = float(temperature_text) if temperature_text else None
        return cls(
            provider=provider,
            agent_model=agent_model,
            consolidator_model=consolidator_model,
            api_key=api_key,
            base_url=os.getenv("AH_LLM_BASE_URL", "").strip() or None,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

    def metadata(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "agent_model": self.agent_model,
            "consolidator_model": self.consolidator_model,
            "max_output_tokens": self.max_output_tokens,
            "temperature": self.temperature,
        }
