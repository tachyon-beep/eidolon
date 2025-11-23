"""
Business Analyst with GPT-5.1 Reasoning - Shopfront Demo

Tests the BA using GPT-5.1's reasoning capabilities for better
tool calling and delegation decisions.
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from openai import AsyncOpenAI
from business_analyst import BusinessAnalyst
from design_context_tools import DesignContextToolHandler
from code_graph import CodeGraphAnalyzer
from specialist_agents import create_default_registry
from logging_config import get_logger

logger = get_logger(__name__)


class GPT5Provider:
    """GPT-5.1 Provider with reasoning support"""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = "openai/gpt-5.1"

    async def create_completion(
        self,
        messages: list,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        tools=None,
        **kwargs
    ):
        """Create completion with reasoning enabled"""

        # Build request params
        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools

        # Enable reasoning
        params["extra_body"] = {"reasoning": {"enabled": True}}

        # Make API call
        response = await self.client.chat.completions.create(**params)

        choice = response.choices[0]

        # Extract tool calls if present
        tool_calls = None
        if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
            tool_calls = choice.message.tool_calls

        # Extract reasoning if present
        reasoning_content = None
        if hasattr(choice.message, 'reasoning_details'):
            reasoning_content = choice.message.reasoning_details

        # Return response object with tool_calls attribute
        class Response:
            def __init__(self, content, tool_calls, reasoning):
                self.content = content
                self.tool_calls = tool_calls
                self.reasoning_details = reasoning
                self.input_tokens = response.usage.prompt_tokens if response.usage else 0
                self.output_tokens = response.usage.completion_tokens if response.usage else 0
                self.model = response.model
                self.finish_reason = choice.finish_reason or "stop"

        return Response(choice.message.content or "", tool_calls, reasoning_content)

    def get_model_name(self):
        return self.model

    def get_provider_name(self):
        return "openai-gpt5"


async def test_ba_with_gpt5():
    """Test BA with GPT-5.1 reasoning"""

    print("="*80)
    print("🧠 BUSINESS ANALYST WITH GPT-5.1 REASONING - SHOPFRONT DEMO")
    print("="*80)

    # Check for API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set")
        return False

    print("\n✅ API key found - initializing GPT-5.1 with reasoning...\n")

    # Create GPT-5.1 provider
    print("🧠 Initializing GPT-5.1 provider with reasoning enabled...")
    llm_provider = GPT5Provider(api_key=api_key)

    # Create project path
    project_path = str(Path(__file__).parent)

    # Build code graph (lightweight - no AI descriptions)
    print("\n📊 Building code graph...")
    code_graph_analyzer = CodeGraphAnalyzer()
    code_graph = await code_graph_analyzer.analyze_project(
        project_path=Path(project_path),
        exclude_patterns=["test_*", "*_test.py"]
    )
    print(f"   ✅ {code_graph.total_modules} modules, {code_graph.total_functions} functions")

    # Create design tool handler
    design_tool_handler = DesignContextToolHandler(
        code_graph=code_graph,
        project_context={"project_path": project_path, "project_type": "e-commerce"}
    )

    # Create specialist registry
    print("\n🔧 Creating specialist registry...")
    specialist_registry = create_default_registry(llm_provider)
    print("   ✅ 12 specialists registered")

    # Create Business Analyst
    print("\n🎓 Creating Business Analyst with all tools...")
    ba = BusinessAnalyst(
        llm_provider=llm_provider,
        code_graph=code_graph,
        design_tool_handler=design_tool_handler,
        specialist_registry=specialist_registry
    )

    # Shopfront request
    shopfront_request = """
I want to build a simple e-commerce shopfront with the following features:

1. **Product Catalog**
   - Display products with name, description, price, stock, image
   - Search products by name
   - Filter by price range

2. **Shopping Cart**
   - Add/remove products
   - Update quantities
   - View cart total

3. **User Authentication**
   - Register with email/password
   - Login/logout
   - JWT tokens

4. **Checkout**
   - Review order
   - Enter shipping address
   - PayPal payment integration (stub for now)
   - Create order

5. **Order History**
   - View past orders
   - Order status tracking

Technical requirements:
- Python 3.12+ with FastAPI
- SQLite database
- RESTful API
- Clean, type-safe code

Build this as a complete backend API.
"""

    print("\n📝 User Request:")
    print(shopfront_request)

    print("\n" + "="*80)
    print("🚀 STARTING BA SESSION WITH GPT-5.1 REASONING")
    print("="*80)
    print("\nGPT-5.1 will reason through:")
    print("  • What tools to use")
    print("  • Which specialists to consult")
    print("  • What questions to ask")
    print("  • When to confirm and fire")
    print("\n" + "="*80)

    # User callback
    async def user_callback(question: str, context: str, options: list = None):
        print(f"\n{'='*80}")
        print("🤖 BA QUESTION")
        print(f"{'='*80}")
        print(f"\n📋 Context: {context}")
        print(f"\n❓ Question:\n{question}")

        if options:
            print(f"\n💡 Options:")
            for i, opt in enumerate(options, 1):
                print(f"   {i}. {opt}")

        # Simulate user response
        if "confirm" in question.lower():
            response = "yes, looks good, proceed"
        elif "paypal" in question.lower():
            response = "stub it for now, we'll integrate later"
        elif "database" in question.lower():
            response = "SQLite is fine for MVP"
        elif "authentication" in question.lower():
            response = "JWT with bcrypt for passwords"
        else:
            response = "yes, that's correct"

        print(f"\n👤 USER RESPONSE:\n{response}")
        print(f"{'='*80}\n")

        return response

    try:
        # Run interactive analysis
        requirements = await ba.interactive_analyze(
            initial_request=shopfront_request,
            project_path=project_path,
            user_callback=user_callback,
            context={"project_type": "e-commerce"}
        )

        print("\n" + "="*80)
        print("✅ BA SESSION COMPLETE!")
        print("="*80)

        print(f"\n📋 Final Analysis:")
        print(f"   Change Type: {requirements.change_type}")
        print(f"   Complexity: {requirements.complexity_estimate}")
        print(f"   Analysis Turns: {requirements.analysis_turns}")
        print(f"   Tools Used: {len(requirements.tools_used)}")

        if requirements.tools_used:
            print(f"\n🔧 Tools Called:")
            for tool in requirements.tools_used:
                print(f"   - {tool}")

        print(f"\n🎯 Clear Objectives ({len(requirements.clear_objectives)}):")
        for obj in requirements.clear_objectives[:5]:
            print(f"   • {obj}")

        print(f"\n✅ Success Criteria ({len(requirements.success_criteria)}):")
        for criterion in requirements.success_criteria[:5]:
            print(f"   • {criterion}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🎬 BUSINESS ANALYST + GPT-5.1 REASONING DEMO")
    print("="*80)
    print("\nThis demo uses GPT-5.1's reasoning capabilities to:")
    print("  • Make smarter tool calling decisions")
    print("  • Intelligently delegate to specialists")
    print("  • Ask better clarifying questions")
    print("  • Reason through requirements systematically")
    print("\n" + "="*80)

    success = asyncio.run(test_ba_with_gpt5())

    if success:
        print("\n🎉 DEMO COMPLETE!")
    else:
        print("\n❌ Demo encountered errors")

    sys.exit(0 if success else 1)
