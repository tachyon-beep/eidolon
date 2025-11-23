"""
Test if merging tool results into one message works
"""
import asyncio
from openai import AsyncOpenAI
import os
import json

async def test_merged():
    """Test merging multiple tool results into one message"""
    print("\n🧪 Testing MERGED tool results...")

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY", "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")
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_modules",
                "description": "Get modules",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_architecture",
                "description": "Get architecture",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"}
                    }
                }
            }
        }
    ]

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Get modules and architecture for 'src'"}
    ]

    try:
        # First call
        print("📞 First call...")
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

        tool_calls = response1.choices[0].message.tool_calls
        if not tool_calls or len(tool_calls) < 2:
            print(f"❌ Expected 2 tool calls, got {len(tool_calls) if tool_calls else 0}")
            return False

        print(f"✅ Got {len(tool_calls)} tool calls")

        # Add assistant message
        messages.append({
            "role": "assistant",
            "content": "",
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

        # MERGE tool results into a SINGLE message with combined content
        combined_results = {
            tc.function.name: {"result": "success", "tool_call_id": tc.id}
            for tc in tool_calls
        }

        # Use first tool_call_id (or maybe we shouldn't specify id at all?)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_calls[0].id,  # Just use first one
            "content": json.dumps(combined_results)
        })

        print(f"📊 Message structure: {[m['role'] for m in messages]}")

        # Second call
        print("\n📞 Second call with MERGED results...")
        response2 = await client.chat.completions.create(
            model="anthropic/claude-sonnet-4.5",
            messages=messages,
            max_tokens=100,
            extra_headers={
                "HTTP-Referer": "https://github.com/studious-adventure",
                "X-Title": "Test"
            }
        )

        print(f"✅ Success!")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_merged())
    print(f"\n{'✅ PASS' if success else '❌ FAIL'}")
