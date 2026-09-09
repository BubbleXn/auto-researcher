"""OpenAI-based LLM client implementation."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

_DEFAULT_TIMEOUT_SECONDS = 60.0
_DEFAULT_MAX_RETRIES = 3


class OpenAILLMClient:
    """Production LLM client using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int = _DEFAULT_MAX_RETRIES,
    ):
        self._client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url,
            timeout=timeout or _DEFAULT_TIMEOUT_SECONDS,
            max_retries=max_retries,
        )
        self._model = model or settings.openai_model

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = await self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        *,
        schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        response_text = await self.generate(
            messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        return json.loads(response_text)
