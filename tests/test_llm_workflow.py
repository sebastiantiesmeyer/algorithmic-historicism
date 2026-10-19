from pathlib import Path

import pytest

from algorithmic_historicism.config import LLMSettings


def test_llm_settings_loads_dotenv_and_redacts_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    for name in (
        "OPENAI_API_KEY",
        "AH_LLM_PROVIDER",
        "AH_AGENT_MODEL",
        "AH_CONSOLIDATOR_MODEL",
        "AH_LLM_BASE_URL",
        "AH_LLM_MAX_OUTPUT_TOKENS",
        "AH_LLM_TEMPERATURE",
    ):
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=test-secret\n"
        "AH_LLM_PROVIDER=openai\n"
        "AH_AGENT_MODEL=agent-model\n"
        "AH_CONSOLIDATOR_MODEL=memory-model\n"
        "AH_LLM_MAX_OUTPUT_TOKENS=4096\n",
        encoding="utf-8",
    )

    settings = LLMSettings.from_env(env_file)

    assert settings.agent_model == "agent-model"
    assert settings.consolidator_model == "memory-model"
    assert settings.max_output_tokens == 4096
    assert "api_key" not in settings.metadata()
    assert "test-secret" not in str(settings.metadata())


def test_llm_settings_requires_model_and_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AH_AGENT_MODEL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("AH_LLM_PROVIDER=openai\n", encoding="utf-8")

    with pytest.raises(ValueError, match="AH_AGENT_MODEL"):
        LLMSettings.from_env(env_file)


