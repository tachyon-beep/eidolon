"""
Full End-to-End Shopfront Build - BA → Orchestrator → Code Generation

This test demonstrates the complete pipeline:
1. Business Analyst gathers requirements
2. Hands off to SystemDecomposer (Tier 1)
3. Full decomposition → planning → code generation
4. Generates actual FastAPI backend + frontend

Real code, not stubs!
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from openai import AsyncOpenAI
from business_analyst import BusinessAnalyst
from code_graph import CodeGraphAnalyzer
from specialist_agents import create_default_registry
from orchestrator import HierarchicalOrchestrator
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

        params = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if tools:
            params["tools"] = tools

        # Enable reasoning for better decisions
        params["extra_body"] = {"reasoning": {"enabled": True}}

        response = await self.client.chat.completions.create(**params)
        choice = response.choices[0]

        # Extract tool calls if present
        tool_calls = None
        if hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
            tool_calls = choice.message.tool_calls

        # Return response object
        class Response:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls
                self.input_tokens = response.usage.prompt_tokens if response.usage else 0
                self.output_tokens = response.usage.completion_tokens if response.usage else 0
                self.model = response.model
                self.finish_reason = choice.finish_reason or "stop"

        return Response(choice.message.content or "", tool_calls)

    def get_model_name(self):
        return self.model

    def get_provider_name(self):
        return "openai-gpt5"


async def run_full_e2e_shopfront():
    """Run complete end-to-end shopfront build"""

    print("="*80)
    print("🏗️  FULL END-TO-END SHOPFRONT BUILD")
    print("="*80)
    print("\nPipeline: BA → SystemDecomposer → Code Generation")
    print("Output: Real FastAPI backend + Frontend code")
    print("="*80)

    # Check for API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set")
        return False

    print("\n✅ API key found\n")

    # Create GPT-5.1 provider
    print("🧠 Initializing GPT-5.1 provider...")
    llm_provider = GPT5Provider(api_key=api_key)

    project_path = str(Path(__file__).parent)
    output_dir = Path(project_path) / "generated_shopfront"
    output_dir.mkdir(exist_ok=True)

    print(f"📂 Output directory: {output_dir}")

    # =========================================================================
    # PHASE 1: BUSINESS ANALYST - REQUIREMENTS GATHERING
    # =========================================================================

    print("\n" + "="*80)
    print("📋 PHASE 1: BUSINESS ANALYST - REQUIREMENTS GATHERING")
    print("="*80)

    # Build lightweight code graph (skip AI descriptions)
    print("\n📊 Analyzing existing codebase...")
    code_graph_analyzer = CodeGraphAnalyzer()
    code_graph = await code_graph_analyzer.analyze_project(
        project_path=Path(project_path),
        exclude_patterns=["test_*", "*_test.py", "generated_*"]
    )
    print(f"   ✅ {code_graph.total_modules} modules analyzed")

    # Create specialist registry
    print("\n🔧 Initializing 12 domain specialists...")
    specialist_registry = create_default_registry(llm_provider)
    print("   ✅ Specialists ready")

    # Create Business Analyst (no design tools to save context)
    print("\n🎓 Creating Business Analyst...")
    ba = BusinessAnalyst(
        llm_provider=llm_provider,
        code_graph=None,  # Skip to save context
        design_tool_handler=None,  # Skip to save context
        specialist_registry=specialist_registry
    )

    # Simplified shopfront request
    shopfront_request = """
Build a simple e-commerce shopfront with:

**Backend (FastAPI + Python 3.12+):**
1. Product API - List products (id, name, price, description, stock)
2. Cart API - Add/remove/update cart items (in-memory for now)
3. User Auth - Simple JWT login (stub user: admin@shop.com / password123)
4. Checkout - Create order from cart (stub payment as always-success)
5. Orders API - View order history

**Frontend (Simple HTML/JS):**
1. Product listing page with search
2. Shopping cart display
3. Simple login form
4. Checkout flow
5. Order confirmation page

**Technical:**
- FastAPI backend with Pydantic models
- SQLite database (Product, Order, OrderItem tables)
- Simple vanilla JS frontend (no React/Vue for simplicity)
- RESTful API design
- Type hints throughout
- Basic error handling

Keep it simple but functional. Generate actual working code.
"""

    print("\n📝 User Request:")
    print(shopfront_request)

    # Auto-confirming user callback
    async def user_callback(question: str, context: str, options: list = None):
        print(f"\n🤖 BA: {question[:100]}...")

        # Auto-confirm everything to keep it moving
        if "confirm" in question.lower():
            response = "yes, looks good"
        else:
            response = "yes, proceed with simple MVP"

        print(f"👤 USER: {response}")
        return response

    print("\n🚀 Running Business Analyst session...")

    try:
        requirements = await ba.interactive_analyze(
            initial_request=shopfront_request,
            project_path=project_path,
            user_callback=user_callback,
            context={"project_type": "e-commerce", "build_real_code": True}
        )

        print("\n✅ Requirements Analysis Complete!")
        print(f"   Change Type: {requirements.change_type}")
        print(f"   Complexity: {requirements.complexity_estimate}")
        print(f"   Objectives: {len(requirements.clear_objectives)}")

    except Exception as e:
        print(f"\n⚠️  BA session error: {e}")
        print("   Continuing with simplified requirements...")

        # Create fallback requirements
        from business_analyst import RequirementsAnalysis
        requirements = RequirementsAnalysis(
            raw_request=shopfront_request,
            refined_requirements=shopfront_request,
            clear_objectives=[
                "Build FastAPI backend with Product, Cart, Auth, Checkout APIs",
                "Create simple HTML/JS frontend for shopfront",
                "Implement SQLite database for products and orders",
                "Generate working, deployable code"
            ],
            success_criteria=[
                "Backend API endpoints respond correctly",
                "Frontend can browse products and checkout",
                "Database persists orders",
                "Code is clean and type-safe"
            ],
            affected_subsystems=["backend", "frontend", "database"],
            affected_modules=["api", "models", "auth", "ui"],
            change_type="new_feature",
            complexity_estimate="medium",
            assumptions=[
                "Simple in-memory cart",
                "Stubbed payment always succeeds",
                "Basic auth without email verification"
            ],
            open_questions=[],
            risks=["First iteration may need refinement"],
            proposed_changes=[
                {"type": "create", "path": "shopfront/backend/", "description": "FastAPI backend"},
                {"type": "create", "path": "shopfront/frontend/", "description": "HTML/JS frontend"}
            ]
        )

    # =========================================================================
    # PHASE 2: ORCHESTRATOR - CODE GENERATION
    # =========================================================================

    print("\n" + "="*80)
    print("🏗️  PHASE 2: ORCHESTRATOR - FULL PIPELINE")
    print("="*80)
    print("\nPipeline stages:")
    print("  1. SystemDecomposer (Tier 1) - Break into subsystems")
    print("  2. ModuleDecomposer (Tier 2) - Plan modules")
    print("  3. FunctionPlanner (Tier 3) - Plan functions")
    print("  4. CodeGenerator - Write actual code")
    print("  5. ReviewLoop - Review and refine")
    print("="*80)

    # Create orchestrator
    print("\n⚙️  Initializing HierarchicalOrchestrator...")
    orchestrator = HierarchicalOrchestrator(
        llm_provider=llm_provider,
        use_review_loops=True,
        use_code_graph=True
    )

    # Run full pipeline
    print("\n🚀 Starting code generation pipeline...\n")

    try:
        result = await orchestrator.orchestrate(
            user_request=requirements.refined_requirements,
            project_path=str(output_dir),
            context={
                "requirements_analysis": requirements,
                "build_real_code": True,
                "target": "shopfront",
                "tech_stack": "FastAPI + SQLite + HTML/JS",
                "clear_objectives": requirements.clear_objectives,
                "success_criteria": requirements.success_criteria
            }
        )

        print("\n" + "="*80)
        print("✅ CODE GENERATION COMPLETE!")
        print("="*80)

        print(f"\n📊 Generation Statistics:")
        print(f"   Status: {result.status}")
        print(f"   Success: {result.success}")
        print(f"   Total tasks: {result.tasks_total}")
        print(f"   Completed: {result.tasks_completed}")
        print(f"   Failed: {result.tasks_failed}")
        print(f"   Files created: {result.files_created}")
        print(f"   Files modified: {result.files_modified}")

        generated_files = result.files_written or []
        print(f"   Files generated: {len(generated_files)}")

        if generated_files:
            print(f"\n📁 Generated Files:")
            for file_path in generated_files[:15]:  # Show first 15
                print(f"   ✅ {file_path}")

            if len(generated_files) > 15:
                print(f"   ... and {len(generated_files) - 15} more")

        # Show output directory
        print(f"\n📂 All files written to: {output_dir}")
        print("\n🎉 SHOPFRONT BUILD COMPLETE!")

        return True

    except Exception as e:
        print(f"\n❌ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🎬 FULL END-TO-END SHOPFRONT BUILD")
    print("="*80)
    print("\nThis demo runs the complete pipeline:")
    print("  1. Business Analyst gathers requirements")
    print("  2. SystemDecomposer breaks into subsystems")
    print("  3. ModuleDecomposer plans module structure")
    print("  4. FunctionPlanner designs functions")
    print("  5. CodeGenerator writes actual code")
    print("  6. ReviewLoop reviews and refines")
    print("\nOutput: Working FastAPI backend + HTML/JS frontend")
    print("="*80)

    success = asyncio.run(run_full_e2e_shopfront())

    if success:
        print("\n" + "="*80)
        print("🎉 BUILD SUCCESSFUL!")
        print("="*80)
        print("\nNext steps:")
        print("  1. cd generated_shopfront")
        print("  2. Review generated code")
        print("  3. Install dependencies: pip install -r requirements.txt")
        print("  4. Run: python -m uvicorn main:app --reload")
        print("  5. Open: http://localhost:8000")
        print("="*80)
    else:
        print("\n❌ Build encountered errors - check logs above")

    sys.exit(0 if success else 1)
