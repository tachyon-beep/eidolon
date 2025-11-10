"""Unified LLM client for multiple providers."""

import hashlib
import json
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

from .cache import Cache

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Unified interface for LLM providers."""

    def __init__(
        self,
        provider: str = "anthropic",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        cache_enabled: bool = True,
    ):
        """Initialize LLM client.

        Args:
            provider: "anthropic", "openai", or "openai-compatible"
            model: Model name (uses default if not specified)
            api_key: API key (uses env var if not specified)
            base_url: Base URL for API (for openai-compatible providers like OpenRouter)
            cache_enabled: Whether to cache responses
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.base_url = base_url
        self.cache = Cache() if cache_enabled else None

        # Set default models
        if model:
            self.model = model
        elif self.provider == "anthropic":
            self.model = "claude-3-5-sonnet-20241022"
        elif self.provider == "openai":
            self.model = "gpt-4-turbo-preview"
        elif self.provider == "openai-compatible":
            # For OpenRouter, use a good default
            self.model = model or "anthropic/claude-3.5-sonnet"
        else:
            raise ValueError(f"Unknown provider: {provider}")

        # Initialize provider client
        self._client = None

    async def complete(
        self,
        prompt: str,
        json_mode: bool = False,
        cache_key: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> str | dict:
        """Call LLM with caching and retries.

        Args:
            prompt: Prompt to send
            json_mode: Whether to parse JSON response
            cache_key: Optional cache key
            max_tokens: Maximum response tokens

        Returns:
            Response text or parsed JSON
        """
        # Check cache
        if cache_key and self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached

        # Call provider
        if self.provider == "anthropic":
            response = await self._anthropic_call(prompt, json_mode, max_tokens)
        elif self.provider in ["openai", "openai-compatible"]:
            response = await self._openai_call(prompt, json_mode, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Store in cache
        if cache_key and self.cache:
            await self.cache.set(cache_key, response)

        return response

    async def complete_structured(
        self,
        prompt: str,
        response_model: Type[T],
        cache_key: Optional[str] = None,
        max_tokens: int = 4096,
    ) -> T:
        """Call LLM with structured output (Pydantic model).

        Args:
            prompt: Prompt to send
            response_model: Pydantic model class for structured response
            cache_key: Optional cache key
            max_tokens: Maximum response tokens

        Returns:
            Instance of response_model

        Note:
            - For OpenAI/OpenAI-compatible: Uses structured outputs API
            - For Anthropic: Falls back to JSON mode + manual parsing
        """
        # Check cache
        if cache_key and self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return response_model.model_validate(cached)

        # Call provider with structured output
        if self.provider == "openai":
            # Official OpenAI supports structured outputs API
            result = await self._openai_structured_call(prompt, response_model, max_tokens)
        elif self.provider in ["openai-compatible", "anthropic"]:
            # OpenRouter and Anthropic don't support structured outputs yet, fallback to JSON mode
            # Add schema to prompt
            schema = response_model.model_json_schema()
            enhanced_prompt = f"{prompt}\n\nRespond with JSON matching this schema:\n{json.dumps(schema, indent=2)}"

            json_response = await self._openai_call(enhanced_prompt, json_mode=True, max_tokens=max_tokens) if self.provider == "openai-compatible" else await self._anthropic_call(enhanced_prompt, json_mode=True, max_tokens=max_tokens)
            result = response_model.model_validate(json_response)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

        # Store in cache
        if cache_key and self.cache:
            await self.cache.set(cache_key, result.model_dump())

        return result

    async def _openai_structured_call(
        self, prompt: str, response_model: Type[T], max_tokens: int
    ) -> T:
        """Call OpenAI with structured output."""
        import openai

        if not self._client:
            if self.base_url:
                self._client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            else:
                self._client = openai.AsyncOpenAI(api_key=self.api_key)

        # Use beta API for structured outputs
        response = await self._client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format=response_model,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.parsed

    async def _anthropic_call(
        self, prompt: str, json_mode: bool, max_tokens: int
    ) -> str | dict:
        """Call Anthropic API."""
        import anthropic

        if not self._client:
            self._client = anthropic.AsyncAnthropic(api_key=self.api_key)

        message = await self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        content = message.content[0].text

        if json_mode:
            return self._extract_json(content)

        return content

    async def _openai_call(
        self, prompt: str, json_mode: bool, max_tokens: int
    ) -> str | dict:
        """Call OpenAI or OpenAI-compatible API."""
        import openai

        if not self._client:
            # For OpenAI-compatible providers (like OpenRouter)
            if self.base_url:
                self._client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            else:
                self._client = openai.AsyncOpenAI(api_key=self.api_key)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }

        # Only use response_format for official OpenAI (not all compatible APIs support it)
        if json_mode and self.provider == "openai":
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content

        if json_mode:
            return self._extract_json(content)

        return content

    def _extract_json(self, content: str) -> dict:
        """Extract JSON from markdown or raw text."""
        # Try to extract from markdown code block
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}\n\nContent:\n{content}")

    def make_cache_key(self, *parts: str) -> str:
        """Generate cache key from parts.

        Args:
            *parts: Parts to hash

        Returns:
            Cache key (hash of parts)
        """
        content = "|".join(parts)
        return hashlib.sha256(content.encode()).hexdigest()
