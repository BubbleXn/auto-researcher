"""Unit tests for OpenAILLMClient configuration."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.clients.llm import OpenAILLMClient


@pytest.mark.asyncio
async def test_openai_client_uses_timeout_and_retries():
    with patch("app.agent.clients.llm.AsyncOpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client

        OpenAILLMClient(api_key="test-key", base_url="http://localhost", max_retries=5, timeout=42.0)

        mock_openai_cls.assert_called_once_with(
            api_key="test-key",
            base_url="http://localhost",
            timeout=42.0,
            max_retries=5,
        )


@pytest.mark.asyncio
async def test_generate_returns_content():
    with patch("app.agent.clients.llm.AsyncOpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content="hello"))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai_cls.return_value = mock_client

        client = OpenAILLMClient(api_key="test-key")
        result = await client.generate([{"role": "user", "content": "hi"}])

        assert result == "hello"
        mock_client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_structured_parses_json():
    with patch("app.agent.clients.llm.AsyncOpenAI") as mock_openai_cls:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock(message=MagicMock(content='{"answer": 42}'))]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_openai_cls.return_value = mock_client

        client = OpenAILLMClient(api_key="test-key")
        result = await client.generate_structured(
            [{"role": "user", "content": "hi"}],
            schema={"type": "object"},
        )

        assert result == {"answer": 42}
