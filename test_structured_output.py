"""
Test structured JSON outputs from GPT-5.1

This verifies that the LLM can return valid JSON in the expected format
"""
import asyncio
import json
import os
from openai import AsyncOpenAI

async def test_basic_json_output():
    """Test 1: Basic JSON output without tools"""
    print("\n" + "="*80)
    print("TEST 1: Basic JSON Output (No Tools)")
    print("="*80)

    api_key = os.getenv("OPENROUTER_API_KEY")
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    prompt = """Please respond with ONLY a valid JSON object in this exact format:
{
  "task_name": "descriptive name",
  "complexity": "low|medium|high",
  "steps": ["step 1", "step 2", "step 3"]
}

Task: Create a simple Python script that prints "Hello World"
"""

    response = await client.chat.completions.create(
        model="openai/gpt-5.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    content = response.choices[0].message.content
    print(f"\n📤 Raw Response:\n{content}\n")

    try:
        parsed = json.loads(content)
        print(f"✅ Valid JSON!")
        print(f"📋 Parsed:\n{json.dumps(parsed, indent=2)}\n")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}\n")
        return False


async def test_json_with_reasoning():
    """Test 2: JSON output with reasoning enabled"""
    print("\n" + "="*80)
    print("TEST 2: JSON Output WITH Reasoning")
    print("="*80)

    api_key = os.getenv("OPENROUTER_API_KEY")
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    prompt = """Please respond with ONLY a valid JSON object in this exact format:
{
  "subsystem_tasks": [
    {
      "name": "backend",
      "description": "FastAPI backend server"
    },
    {
      "name": "frontend",
      "description": "HTML/JS frontend"
    }
  ]
}

Task: Decompose an e-commerce shopfront into subsystems
"""

    response = await client.chat.completions.create(
        model="openai/gpt-5.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        extra_body={"reasoning": {"enabled": True}}
    )

    content = response.choices[0].message.content
    print(f"\n📤 Raw Response:\n{content}\n")

    # Check if there's reasoning output
    if hasattr(response.choices[0].message, 'reasoning'):
        print(f"🧠 Reasoning Output:\n{response.choices[0].message.reasoning}\n")

    try:
        parsed = json.loads(content)
        print(f"✅ Valid JSON!")
        print(f"📋 Parsed:\n{json.dumps(parsed, indent=2)}\n")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ JSON Parse Error: {e}")
        print("Trying to extract JSON from markdown code blocks...\n")

        # Try to extract from code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                print(f"✅ Extracted JSON from code block!")
                print(f"📋 Parsed:\n{json.dumps(parsed, indent=2)}\n")
                return True
            except:
                pass

        # Try to find any JSON object
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                print(f"✅ Extracted JSON from text!")
                print(f"📋 Parsed:\n{json.dumps(parsed, indent=2)}\n")
                return True
            except:
                pass

        print(f"❌ Could not extract valid JSON\n")
        return False


async def test_json_with_tools():
    """Test 3: JSON output in tool-calling context"""
    print("\n" + "="*80)
    print("TEST 3: JSON Output in Tool-Calling Context")
    print("="*80)

    api_key = os.getenv("OPENROUTER_API_KEY")
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_module_info",
                "description": "Get information about existing modules",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"}
                    }
                }
            }
        }
    ]

    messages = [
        {
            "role": "user",
            "content": "List the modules in the backend subsystem, then provide a plan as JSON"
        }
    ]

    # Turn 1: LLM calls tool
    response1 = await client.chat.completions.create(
        model="openai/gpt-5.1",
        messages=messages,
        tools=tools,
        temperature=0.0
    )

    print(f"\n📤 Turn 1 Response:")
    if response1.choices[0].message.tool_calls:
        print(f"🔧 Tool calls: {len(response1.choices[0].message.tool_calls)}")
        for tc in response1.choices[0].message.tool_calls:
            print(f"   - {tc.function.name}({tc.function.arguments})")

        # Add tool result
        messages.append(response1.choices[0].message)
        messages.append({
            "role": "tool",
            "tool_call_id": response1.choices[0].message.tool_calls[0].id,
            "content": json.dumps({"modules": ["main.py", "models.py"]})
        })

        # Turn 2: LLM provides final JSON
        response2 = await client.chat.completions.create(
            model="openai/gpt-5.1",
            messages=messages,
            temperature=0.0,
            extra_body={"reasoning": {"enabled": True}}
        )

        content = response2.choices[0].message.content
        print(f"\n📤 Turn 2 Response:\n{content}\n")

        try:
            parsed = json.loads(content)
            print(f"✅ Valid JSON after tool call!")
            print(f"📋 Parsed:\n{json.dumps(parsed, indent=2)}\n")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}\n")
            return False
    else:
        print(f"No tool calls made\n")
        return False


async def main():
    print("\n🧪 STRUCTURED OUTPUT TESTS FOR GPT-5.1")
    print("=" * 80)

    results = {}

    # Test 1: Basic JSON
    results["basic"] = await test_basic_json_output()

    # Test 2: JSON with reasoning
    results["reasoning"] = await test_json_with_reasoning()

    # Test 3: JSON in tool context
    results["tools"] = await test_json_with_tools()

    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(results.values())
    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n✅ All structured output tests PASSED!")
    else:
        print("\n⚠️ Some tests FAILED - structured outputs need fixing")


if __name__ == "__main__":
    asyncio.run(main())
