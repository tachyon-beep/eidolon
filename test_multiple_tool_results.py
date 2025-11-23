"""
Test multiple tool results in sequence (like our decomposer does)
"""
import asyncio
from openai import AsyncOpenAI
import os

async def test_multiple_tools():
    """Test that multiple tool results work"""
    print("\n🧪 Testing multiple tool results...")

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY", "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")
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_existing_modules",
                "description": "Get existing modules",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_subsystem_architecture",
                "description": "Get subsystem architecture",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subsystem_name": {"type": "string"}
                    }
                }
            }
        }
    ]

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Get existing modules and the architecture for 'src' subsystem"}
    ]

    try:
        # First call - LLM should request both tools
        print("📞 First call - requesting tools...")
        response1 = await client.chat.completions.create(
            model="anthropic/claude-sonnet-4.5",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=100,
            extra_headers={
                "HTTP-Referer": "https://github.com/studious-adventure",
                "X-Title": "Test"
            }
        )

        tool_calls = response1.choices[0].message.tool_calls
        if not tool_calls:
            print("❌ No tool calls made")
            return False

        print(f"✅ {len(tool_calls)} tool(s) called")

        # Add assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": response1.choices[0].message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in tool_calls
            ]
        })

        # Add tool results
        for tc in tool_calls:
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": '{"result": "success"}'
            })

        print(f"📊 Message structure: {[m['role'] for m in messages]}")
        print(f"   Total messages: {len(messages)}")

        # Debug: print full messages
        import json
        print("\n📋 Full messages:")
        for i, msg in enumerate(messages):
            print(f"  {i+1}. {msg.get('role')}: {json.dumps(msg, indent=4, default=str)[:200]}")

        # Second call - LLM should use tool results
        # NOTE: Do NOT send tools parameter when tool results are in messages!
        print("\n📞 Second call - with tool results (NO tools param)...")
        response2 = await client.chat.completions.create(
            model="anthropic/claude-sonnet-4.5",
            messages=messages,
            # tools=tools,  # REMOVED - causes 500 error with tool results!
            # tool_choice="auto",  # REMOVED
            max_tokens=100,
            extra_headers={
                "HTTP-Referer": "https://github.com/studious-adventure",
                "X-Title": "Test"
            }
        )

        print(f"✅ Success: {response2.choices[0].message.content[:100] if response2.choices[0].message.content else 'No content'}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_multiple_tools())
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}")
