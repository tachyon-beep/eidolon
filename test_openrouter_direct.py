"""
Direct test of OpenRouter API to verify it's working
"""
import asyncio
from openai import AsyncOpenAI

async def test_basic_call():
    """Test basic OpenRouter call"""
    print("\n🧪 Testing basic OpenRouter call...")

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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"
    )

    try:
        response = await client.chat.completions.create(
            model="anthropic/claude-sonnet-4.5",
            messages=[
                {"role": "user", "content": "Say hello"}
            ],
            max_tokens=50,
            extra_headers={
                "HTTP-Referer": "https://github.com/studious-adventure",
                "X-Title": "Test"
            }
        )
        print(f"✅ Success: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_with_tools():
    """Test OpenRouter with tools"""
    print("\n🧪 Testing OpenRouter call with tools...")

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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"
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    }
                }
            }
        }
    ]

    try:
        response = await client.chat.completions.create(
            model="anthropic/claude-sonnet-4.5",
            messages=[
                {"role": "user", "content": "What's the weather in SF?"}
            ],
            tools=tools,
            max_tokens=100,
            extra_headers={
                "HTTP-Referer": "https://github.com/studious-adventure",
                "X-Title": "Test"
            }
        )
        print(f"✅ Success with tools!")
        if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
            print(f"   Tool called: {response.choices[0].message.tool_calls[0].function.name}")
        else:
            print(f"   Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def main():
    print("="*80)
    print("🔍 OPENROUTER API DIAGNOSTIC TEST")
    print("="*80)

    test1 = await test_basic_call()
    test2 = await test_with_tools()

    print("\n" + "="*80)
    if test1 and test2:
        print("✅ OpenRouter API is working correctly!")
    else:
        print("❌ OpenRouter API has issues")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
