from __future__ import annotations

from ..base import LLMProvider, VLMProvider


class MockLLMProvider(LLMProvider):
    def complete(self, prompt: str) -> str:
        return f"MOCK_COMPLETION: {prompt[:80]}"


class MockVLMProvider(VLMProvider):
    def critique(self, prompt: str) -> str:
        return f"MOCK_CRITIQUE: {prompt[:80]}"
