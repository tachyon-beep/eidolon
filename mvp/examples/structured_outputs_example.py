#!/usr/bin/env python3
"""Example of using structured outputs with Pydantic models.

This demonstrates how to get type-safe, validated responses from LLMs
using the structured outputs API.
"""

import asyncio

from pydantic import BaseModel, Field

from eidolon_mvp.llm.config import create_llm_from_env


# Define your response schema with Pydantic
class CodeAnalysis(BaseModel):
    """Analysis of a code snippet."""

    complexity: int = Field(description="Cyclomatic complexity (1-10)")
    maintainability: int = Field(description="Maintainability score (1-10)")
    issues: list[str] = Field(description="List of identified issues")
    suggestions: list[str] = Field(description="Improvement suggestions")


async def main():
    """Demonstrate structured outputs."""
    # Setup LLM
    llm = create_llm_from_env()
    if not llm:
        print("❌ No LLM configured. Set environment variables:")
        print("  export LLM_PROVIDER=openai-compatible")
        print("  export OPENAI_API_KEY=your-key")
        print("  export OPENAI_BASE_URL=https://openrouter.ai/api/v1")
        print("  export LLM_MODEL=anthropic/claude-3.5-sonnet")
        return 1

    # Example code to analyze
    code = """
def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]["price"] * items[i]["qty"]
    return total
    """

    print("Code to analyze:")
    print(code)
    print()

    # Use structured outputs - response is guaranteed to match CodeAnalysis schema
    print("Analyzing with structured outputs...")
    analysis = await llm.complete_structured(
        prompt=f"Analyze this Python code and rate its complexity and maintainability:\n\n{code}",
        response_model=CodeAnalysis,
    )

    # Now we have a typed, validated Pydantic model!
    print(f"\n✓ Complexity: {analysis.complexity}/10")
    print(f"✓ Maintainability: {analysis.maintainability}/10")

    if analysis.issues:
        print("\nIssues:")
        for issue in analysis.issues:
            print(f"  • {issue}")

    if analysis.suggestions:
        print("\nSuggestions:")
        for suggestion in analysis.suggestions:
            print(f"  • {suggestion}")

    # Type checking works!
    # analysis.complexity is an int, not str or any
    assert isinstance(analysis.complexity, int)
    assert 1 <= analysis.complexity <= 10

    print("\n✓ Response validated against schema!")

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
