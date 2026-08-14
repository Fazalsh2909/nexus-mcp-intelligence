import pytest

from app.orchestration.llm import get_llm_provider


class TestGetLLMProvider:
    @pytest.mark.asyncio
    async def test_returns_real_provider_when_configured(self):
        provider = get_llm_provider()
        assert provider is not None
