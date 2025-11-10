"""LLM configuration from environment."""

import os
from pathlib import Path
from typing import Optional

from .client import LLMClient

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Look for .env in the project root
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # dotenv not installed, environment variables must be set manually
    pass


def create_llm_from_env() -> Optional[LLMClient]:
    """Create LLM client from environment variables.

    Supports:
    - Anthropic (ANTHROPIC_API_KEY)
    - OpenAI (OPENAI_API_KEY with LLM_PROVIDER=openai)
    - OpenRouter (OPENAI_API_KEY + OPENAI_BASE_URL with LLM_PROVIDER=openai-compatible)

    Returns:
        LLMClient or None if no API key configured
    """
    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    # Get API key
    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        model = os.getenv("ANTHROPIC_MODEL")
        base_url = None
    else:
        # openai or openai-compatible
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")
        base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key:
        return None

    return LLMClient(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        cache_enabled=True,
    )
