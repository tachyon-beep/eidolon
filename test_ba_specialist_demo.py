"""
Business Analyst + Specialist Demo - Focused on Delegation

This demo shows the BA consulting specialists for domain-specific advice.
Uses a simpler request to avoid context size issues.
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from llm_providers import OpenAICompatibleProvider
from business_analyst import BusinessAnalyst
from specialist_agents import create_default_registry
from logging_config import get_logger

logger = get_logger(__name__)


async def test_ba_specialist_delegation():
    """Test BA delegating to specialists"""

    print("="*80)
    print("🎯 BUSINESS ANALYST + SPECIALIST DELEGATION DEMO")
    print("="*80)

    # Check for API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set")
        return False

    print("\n✅ API key found - starting specialist delegation demo!\n")

    # Create LLM provider
    print("🤖 Initializing LLM provider...")
    llm_provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.5")
    )

    # Create specialist registry
    print("\n🔧 Creating specialist registry with 12 domain experts...")
    specialist_registry = create_default_registry(llm_provider)
    print("   ✅ All specialists registered\n")

    # Create BA with specialists but NO design tools (to force specialist usage)
    print("🎓 Creating Business Analyst with specialist delegation...")
    ba = BusinessAnalyst(
        llm_provider=llm_provider,
        code_graph=None,  # No code graph
        design_tool_handler=None,  # No design tools - forces specialist usage
        specialist_registry=specialist_registry
    )

    # Request that requires specialist consultation
    security_request = """
I need to implement JWT authentication for a FastAPI application.

Requirements:
- Secure token generation and validation
- Password hashing with best practices
- Protection against common auth vulnerabilities

Please advise on security best practices and implementation approach.
"""

    print("\n📝 User Request:")
    print(security_request)

    print("\n" + "="*80)
    print("🚀 STARTING BA SESSION - WATCH FOR SPECIALIST CONSULTATIONS")
    print("="*80)

    # User callback for questions
    async def simple_user_callback(question: str, context: str, options: list = None):
        print(f"\n🤖 BA ASKS: {question}")

        # Auto-respond with confirmation
        if "confirm" in question.lower():
            response = "yes, proceed"
        else:
            response = "Use bcrypt for password hashing, industry standard approach"

        print(f"👤 USER: {response}\n")
        return response

    try:
        # Run interactive analysis
        requirements = await ba.interactive_analyze(
            initial_request=security_request,
            project_path=str(Path(__file__).parent),
            user_callback=simple_user_callback,
            context={"project_type": "security"}
        )

        print("\n" + "="*80)
        print("✅ BA SESSION COMPLETE!")
        print("="*80)

        print(f"\n📋 Final Analysis:")
        print(f"   Change Type: {requirements.change_type}")
        print(f"   Complexity: {requirements.complexity_estimate}")
        print(f"   Tools Used: {len(requirements.tools_used)}")
        print(f"   Objectives: {len(requirements.clear_objectives)}")

        if requirements.tools_used:
            print(f"\n🔧 Tools Called:")
            for tool in requirements.tools_used:
                print(f"   - {tool}")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🎬 BUSINESS ANALYST SPECIALIST DELEGATION DEMO")
    print("="*80)
    print("\nThis demo shows the BA consulting domain specialists.\n")
    print("Expected behavior:")
    print("  1. BA receives security-focused request")
    print("  2. BA consults Security Engineer specialist")
    print("  3. Specialist provides security recommendations")
    print("  4. BA incorporates advice and confirms with user")
    print("  5. BA calls initiate_build when ready")
    print("\n" + "="*80)

    success = asyncio.run(test_ba_specialist_delegation())

    if success:
        print("\n🎉 DEMO COMPLETE - Specialist delegation working!")
    else:
        print("\n❌ Demo encountered errors")

    sys.exit(0 if success else 1)
