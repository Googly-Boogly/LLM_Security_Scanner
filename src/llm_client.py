"""Explicit-config LLM client that does not rely on the global Settings singleton."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ProviderType = Literal["anthropic", "openai", "google"]


@dataclass
class LLMConfig:
    provider: ProviderType
    model: str
    api_key: str


class LLMClient:
    """
    Thin async wrapper around three LLM provider SDKs.
    Takes an explicit LLMConfig rather than reading from global settings,
    allowing the scanner to use separate configs for target and judge LLMs.
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    async def call(self, system_prompt: str, user_prompt: str) -> str:
        provider = self._config.provider
        if provider == "anthropic":
            return await self._call_anthropic(system_prompt, user_prompt)
        elif provider == "openai":
            return await self._call_openai(system_prompt, user_prompt)
        elif provider == "google":
            return await self._call_google(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unsupported provider: {provider!r}")

    async def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self._config.api_key)
        message = await client.messages.create(
            model=self._config.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text

    async def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._config.api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = await client.chat.completions.create(
            model=self._config.model,
            messages=messages,
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""

    async def _call_google(self, system_prompt: str, user_prompt: str) -> str:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._config.api_key)
        response = await client.aio.models.generate_content(
            model=self._config.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                max_output_tokens=1024,
            ),
        )
        return response.text
