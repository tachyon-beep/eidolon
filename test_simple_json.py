"""
Simple test to verify JSON extraction from LLM responses
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import asyncio
from llm_providers import create_provider
from utils.json_utils import extract_json_from_response

async def test_json_extraction():
    """Test that we can extract JSON from various response formats"""

    print("\n" + "="*80)
    print("TEST: JSON Extraction from Various Formats")
    print("="*80 + "\n")

    # Test cases
    test_cases = [
        {
            "name": "Pure JSON",
            "input": '{"subsystem_tasks": ["backend", "frontend"]}',
            "expected": True
        },
        {
            "name": "JSON in markdown code block",
            "input": '''Here's the plan:
```json
{
  "subsystem_tasks": ["backend", "frontend"]
}
```
That's my analysis.''',
            "expected": True
        },
        {
            "name": "JSON without code fence",
            "input": '''Based on the requirements:

{
  "subsystem_tasks": ["backend", "frontend"]
}

This decomposition makes sense.''',
            "expected": True
        },
        {
            "name": "No JSON",
            "input": "This is just text without any JSON",
            "expected": False
        },
        {
            "name": "Reasoning + JSON (GPT-5.1 style)",
            "input": '''<reasoning>
Let me think about this... The system needs backend and frontend components.
</reasoning>

```json
{
  "subsystem_tasks": ["backend", "frontend"]
}
```''',
            "expected": True
        }
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        print(f"📝 Test: {test['name']}")
        print(f"Input: {test['input'][:80]}...")

        result = extract_json_from_response(test['input'])
        success = (result is not None) == test['expected']

        if success:
            print(f"✅ PASS")
            if result:
                print(f"   Extracted: {result}")
            passed += 1
        else:
            print(f"❌ FAIL - Expected {test['expected']}, got {result}")
            failed += 1
        print()

    print("="*80)
    print(f"Results: {passed}/{len(test_cases)} passed")
    print("="*80 + "\n")

    return passed == len(test_cases)


async def test_llm_json_output():
    """Test actual LLM JSON output"""

    print("\n" + "="*80)
    print("TEST: Actual LLM JSON Output")
    print("="*80 + "\n")

    try:
        # Create OpenAI provider (via OpenRouter)
        import os
        provider = create_provider(
            provider_type="openai",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL"),
            model=os.getenv("OPENROUTER_MODEL", "openai/gpt-5.1")
        )

        prompt = """Please respond with ONLY valid JSON in this format:
{
  "subsystem_tasks": [
    {
      "name": "backend",
      "description": "FastAPI backend server"
    }
  ]
}

Task: Decompose a simple web app into subsystems."""

        print("📤 Sending request to LLM...")
        response = await provider.create_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )

        print(f"\n📥 Raw Response (first 500 chars):\n{response.content[:500]}\n")

        # Try to extract JSON
        extracted = extract_json_from_response(response.content)

        if extracted and "subsystem_tasks" in extracted:
            print(f"✅ Successfully extracted JSON with 'subsystem_tasks' key!")
            print(f"📋 Extracted: {extracted}\n")
            return True
        else:
            print(f"❌ Failed to extract valid JSON with expected structure")
            print(f"   Extracted: {extracted}\n")
            return False

    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


async def main():
    print("\n🧪 JSON EXTRACTION & STRUCTURED OUTPUT TESTS")
    print("="*80 + "\n")

    # Test 1: JSON extraction logic
    test1_pass = await test_json_extraction()

    # Test 2: Actual LLM output
    test2_pass = await test_llm_json_output()

    print("\n" + "="*80)
    print("📊 FINAL SUMMARY")
    print("="*80)
    print(f"JSON Extraction Logic: {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Actual LLM JSON Output: {'✅ PASS' if test2_pass else '❌ FAIL'}")

    if test1_pass and test2_pass:
        print("\n✅ All tests PASSED - Structured outputs are working!")
        return 0
    else:
        print("\n⚠️ Some tests FAILED - Structured outputs need investigation")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
