"""
Test tool results message format with OpenRouter
"""
import asyncio
from openai import AsyncOpenAI
import os

async def test_tool_results():
    """Test that tool results messages work correctly"""
    print("\n🧪 Testing tool results format...")

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY", "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")
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
                    },
                    "required": ["location"]
                }
            }
        }
    ]

    messages = [
        {"role": "user", "content": "What's the weather in SF?"}
    ]

    try:
        # First call - LLM should request tool
        print("📞 First call - requesting tool...")
        response1 = await client.chat.completions.create(
            model="anthropic/claude-sonnet-4.5",
            messages=messages,
            tools=tools,
            max_tokens=100,
            extra_headers={
                "HTTP-Referer": "https://github.com/studious-adventure",
                "X-Title": "Test"
            }
        )

        if not response1.choices[0].message.tool_calls:
            print("❌ No tool calls made")
            return False

        tool_call = response1.choices[0].message.tool_calls[0]
        print(f"✅ Tool called: {tool_call.function.name}")
        print(f"   Tool call ID: {tool_call.id}")

        # Add assistant message with tool calls
        messages.append(response1.choices[0].message)

        # Simulate tool execution and add result
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": '{"temperature": 72, "condition": "sunny"}'
        })

        # Second call - LLM should use tool result
        print("\n📞 Second call - with tool results...")
        response2 = await client.chat.completions.create(
            model="anthropic/claude-sonnet-4.5",
            messages=messages,
            max_tokens=100,
            extra_headers={
                "HTTP-Referer": "https://github.com/studious-adventure",
                "X-Title": "Test"
            }
        )

        print(f"✅ Success: {response2.choices[0].message.content}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_tool_results())
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}")
