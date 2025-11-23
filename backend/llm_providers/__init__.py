"""
LLM Provider Abstraction for MONAD

Supports multiple LLM providers with a unified interface:
- Anthropic (Claude)
- OpenAI (GPT-4, GPT-4 Turbo)
- OpenRouter (any model via OpenAI-compatible API)
- Together.ai, Groq, etc. (any OpenAI-compatible endpoint)
- Mock (for testing and demos - no API calls)

Configuration via environment variables:
- LLM_PROVIDER: "anthropic", "openai", or "mock" (default: "anthropic")
- ANTHROPIC_API_KEY: For Anthropic/Claude
- OPENAI_API_KEY: For OpenAI or compatible providers
- OPENAI_BASE_URL: For OpenRouter, Together.ai, etc. (optional)
- OPENAI_MODEL: Model to use with OpenAI-compatible providers
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import os

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class LLMResponse:
    """Unified response format across providers"""
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    finish_reason: str = "stop"
    tool_calls: Optional[List[Any]] = None  # Tool calls from LLM
    raw_response: Optional[Any] = None


@dataclass
class LLMMessage:
    """Unified message format"""
    role: str  # "user", "assistant", "system"
    content: str


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        """
        Create a chat completion

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse with unified format
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Get the model name being used"""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name (e.g., 'anthropic', 'openai')"""
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Anthropic provider

        Args:
            api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
            model: Model to use (default: claude-3-5-sonnet-20241022)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        self.client = AsyncAnthropic(api_key=self.api_key)

        logger.info(
            "anthropic_provider_initialized",
            model=self.model
        )

    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        """Create completion using Anthropic API"""
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            **kwargs
        )

        # Extract tool calls if present (Anthropic format)
        tool_calls = None
        # Note: Anthropic uses a different format for tool use
        # We would need to extract from response.content if tool_use blocks exist
        # For now, we'll rely on raw_response for Anthropic tool calls

        return LLMResponse(
            content=response.content[0].text if response.content and hasattr(response.content[0], 'text') else "",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            finish_reason=response.stop_reason or "stop",
            tool_calls=tool_calls,
            raw_response=response
        )

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return "anthropic"


class OpenAICompatibleProvider(LLMProvider):
    """
    OpenAI-compatible provider

    Works with:
    - OpenAI (api.openai.com)
    - OpenRouter (openrouter.ai)
    - Together.ai (api.together.xyz)
    - Groq (api.groq.com)
    - Any other OpenAI-compatible API
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize OpenAI-compatible provider

        Args:
            api_key: API key (falls back to OPENAI_API_KEY env var)
            base_url: API base URL (falls back to OPENAI_BASE_URL, or OpenAI default)
            model: Model to use (falls back to OPENAI_MODEL env var or gpt-4-turbo)

        Examples:
            # OpenAI
            provider = OpenAICompatibleProvider(
                api_key="sk-...",
                model="gpt-4-turbo"
            )

            # OpenRouter
            provider = OpenAICompatibleProvider(
                api_key="sk-or-...",
                base_url="https://openrouter.ai/api/v1",
                model="anthropic/claude-3.5-sonnet"
            )

            # Together.ai
            provider = OpenAICompatibleProvider(
                api_key="...",
                base_url="https://api.together.xyz/v1",
                model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
            )
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4-turbo")

        # Create client
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = AsyncOpenAI(**client_kwargs)

        # Determine provider from base URL
        if self.base_url:
            if "openrouter" in self.base_url:
                self.provider_name = "openrouter"
            elif "together" in self.base_url:
                self.provider_name = "together"
            elif "groq" in self.base_url:
                self.provider_name = "groq"
            else:
                self.provider_name = "openai-compatible"
        else:
            self.provider_name = "openai"

        logger.info(
            "openai_provider_initialized",
            provider=self.provider_name,
            model=self.model,
            base_url=self.base_url or "default (api.openai.com)"
        )

    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        """Create completion using OpenAI-compatible API"""

        # Add OpenRouter-specific headers if using OpenRouter
        if self.provider_name == "openrouter":
            if "extra_headers" not in kwargs:
                kwargs["extra_headers"] = {
                    "HTTP-Referer": "https://github.com/studious-adventure",
                    "X-Title": "Studious Adventure Code Generator"
                }

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )

        choice = response.choices[0]

        # Extract tool calls if present
        tool_calls = None
        if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
            tool_calls = choice.message.tool_calls

        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
            model=response.model,
            finish_reason=choice.finish_reason or "stop",
            tool_calls=tool_calls,
            raw_response=response
        )

    def get_model_name(self) -> str:
        return self.model

    def get_provider_name(self) -> str:
        return self.provider_name


def create_provider(
    provider_type: Optional[str] = None,
    **kwargs
) -> LLMProvider:
    """
    Factory function to create LLM provider

    Args:
        provider_type: "anthropic" or "openai" (default: from LLM_PROVIDER env var or "anthropic")
        **kwargs: Provider-specific arguments (api_key, model, base_url, etc.)

    Returns:
        LLMProvider instance

    Environment Variables:
        LLM_PROVIDER: Provider to use ("anthropic" or "openai")
        ANTHROPIC_API_KEY: For Anthropic
        ANTHROPIC_MODEL: Model name for Anthropic (default: claude-3-5-sonnet-20241022)
        OPENAI_API_KEY: For OpenAI and compatible providers
        OPENAI_BASE_URL: Custom API endpoint (for OpenRouter, Together.ai, etc.)
        OPENAI_MODEL: Model name for OpenAI-compatible (default: gpt-4-turbo)

    Examples:
        # Use environment variables (LLM_PROVIDER=anthropic)
        provider = create_provider()

        # Explicit Anthropic
        provider = create_provider("anthropic", api_key="sk-ant-...")

        # OpenAI
        provider = create_provider("openai", api_key="sk-...", model="gpt-4-turbo")

        # OpenRouter
        provider = create_provider(
            "openai",
            api_key="sk-or-...",
            base_url="https://openrouter.ai/api/v1",
            model="anthropic/claude-3.5-sonnet"
        )
    """
    provider_type = provider_type or os.environ.get("LLM_PROVIDER", "anthropic")
    provider_type = provider_type.lower()

    if provider_type == "anthropic":
        return AnthropicProvider(**kwargs)
    elif provider_type == "openai":
        return OpenAICompatibleProvider(**kwargs)
    elif provider_type == "mock":
        from llm_providers.mock_provider import MockLLMProvider
        return MockLLMProvider(**kwargs)
    else:
        raise ValueError(
            f"Unknown provider: {provider_type}. "
            f"Supported providers: 'anthropic', 'openai', 'mock'"
        )


# Convenience function for getting provider info
def get_provider_info() -> Dict[str, Any]:
    """
    Get information about configured provider

    Returns:
        Dict with provider configuration
    """
    provider_type = os.environ.get("LLM_PROVIDER", "anthropic")

    info = {
        "provider": provider_type,
        "configured": False
    }

    if provider_type == "anthropic":
        info["configured"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
        info["model"] = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    elif provider_type == "openai":
        info["configured"] = bool(os.environ.get("OPENAI_API_KEY"))
        info["model"] = os.environ.get("OPENAI_MODEL", "gpt-4-turbo")
        info["base_url"] = os.environ.get("OPENAI_BASE_URL", "default")

    return info
