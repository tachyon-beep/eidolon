#!/usr/bin/env python3
"""Demo of Agent SDK orchestration with full observability.

This demonstrates spawning multiple Claude Code agents and mediating
their communication for parallel analysis and refactoring.
"""

import asyncio
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from src.eidolon_mvp.orchestrator import AgentConfig, AgentOrchestrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Example complex function to refactor
COMPLEX_FUNCTION = """
def process_order(order_data):
    \"\"\"Process customer order - has high complexity.\"\"\"
    # Validation
    if not order_data:
        raise ValueError("No order data")

    if "customer_id" not in order_data:
        raise ValueError("Missing customer")

    if "items" not in order_data or not order_data["items"]:
        raise ValueError("No items")

    # Calculate totals
    subtotal = 0
    for item in order_data["items"]:
        if "price" not in item or "quantity" not in item:
            raise ValueError("Invalid item")

        price = item["price"]
        quantity = item["quantity"]

        if price < 0 or quantity <= 0:
            raise ValueError("Invalid price/quantity")

        subtotal += price * quantity

    # Apply discount
    discount = 0
    if "discount_code" in order_data:
        code = order_data["discount_code"]
        if code == "SAVE10":
            discount = subtotal * 0.1
        elif code == "SAVE20":
            discount = subtotal * 0.2
        elif code == "SAVE30":
            discount = subtotal * 0.3

    total = subtotal - discount

    # Calculate tax
    tax_rate = 0.08
    if "state" in order_data:
        state = order_data["state"]
        if state == "CA":
            tax_rate = 0.0875
        elif state == "NY":
            tax_rate = 0.08875
        elif state == "TX":
            tax_rate = 0.0625

    tax = total * tax_rate
    final_total = total + tax

    # Process payment
    if "payment_method" not in order_data:
        raise ValueError("No payment method")

    payment = order_data["payment_method"]
    if payment not in ["credit_card", "paypal", "apple_pay"]:
        raise ValueError("Invalid payment method")

    # Create order record
    order = {
        "customer_id": order_data["customer_id"],
        "items": order_data["items"],
        "subtotal": subtotal,
        "discount": discount,
        "tax": tax,
        "total": final_total,
        "payment_method": payment,
        "status": "pending"
    }

    return order
"""


async def demo_parallel_analysis():
    """Demo: Analyze multiple functions in parallel."""
    print("\n" + "=" * 70)
    print("DEMO 1: Parallel Function Analysis")
    print("=" * 70)

    # Create temporary workspace
    with TemporaryDirectory(prefix="eidolon-") as tmpdir:
        workspace = Path(tmpdir)
        logger.info(f"Workspace: {workspace}")

        # Initialize orchestrator
        orchestrator = AgentOrchestrator(base_workspace=workspace)

        # Functions to analyze
        functions = [
            ("process_order", COMPLEX_FUNCTION),
            ("calculate_total", "def calculate_total(items): return sum(i['price'] * i['qty'] for i in items)"),
            ("validate_email", "def validate_email(email): return '@' in email and '.' in email"),
        ]

        # Analyze in parallel with multiple agents
        print(f"\n🚀 Spawning {len(functions)} analyzer agents...")
        results = await orchestrator.analyze_function_parallel(functions)

        print("\n" + "=" * 70)
        print("ANALYSIS RESULTS")
        print("=" * 70)

        for (name, _), result in zip(functions, results):
            if isinstance(result, Exception):
                print(f"\n❌ {name}: Error - {result}")
            else:
                print(f"\n✓ {name}:")
                print(f"  {result[:200]}...")

        # Export conversation for inspection
        log_file = workspace / "conversation.json"
        orchestrator.export_conversation(log_file)
        print(f"\n📝 Full conversation saved to: {log_file}")

        # Cleanup
        await orchestrator.cleanup()


async def demo_refactoring_with_verification():
    """Demo: Refactor with actual test execution."""
    print("\n" + "=" * 70)
    print("DEMO 2: Refactoring with Test-Based Verification")
    print("=" * 70)

    with TemporaryDirectory(prefix="eidolon-") as tmpdir:
        workspace = Path(tmpdir)
        logger.info(f"Workspace: {workspace}")

        # Initialize orchestrator
        orchestrator = AgentOrchestrator(base_workspace=workspace)

        # Refactor complex function
        print("\n🔧 Refactoring process_order function...")
        result = await orchestrator.refactor_with_verification(
            function_name="process_order",
            function_code=COMPLEX_FUNCTION,
            complexity=20,
        )

        print("\n" + "=" * 70)
        print("REFACTORING RESULTS")
        print("=" * 70)

        print(f"\nFunction: {result['function_name']}")
        print(f"Original Complexity: {result['original_complexity']}")
        print(f"Agent: {result['agent_id']}")
        print(f"Workspace: {result['workspace']}")
        print(f"\nRefactored Code Preview:")
        print(f"{result['refactored_code'][:500]}...")

        # Show workspace contents
        workspace_path = Path(result['workspace'])
        if workspace_path.exists():
            print(f"\n📁 Workspace Contents:")
            for file in workspace_path.rglob("*"):
                if file.is_file():
                    print(f"  - {file.relative_to(workspace_path)}")

        # Export conversation
        log_file = workspace / "refactoring_conversation.json"
        orchestrator.export_conversation(log_file)
        print(f"\n📝 Full conversation saved to: {log_file}")

        # Cleanup
        await orchestrator.cleanup()


async def demo_observability():
    """Demo: Full observability of agent communication."""
    print("\n" + "=" * 70)
    print("DEMO 3: Observability - Agent Communication Log")
    print("=" * 70)

    with TemporaryDirectory(prefix="eidolon-") as tmpdir:
        workspace = Path(tmpdir)

        orchestrator = AgentOrchestrator(base_workspace=workspace)

        # Spawn two agents and have them communicate
        analyzer_config = AgentConfig(
            role="analyzer",
            system_prompt="You analyze code complexity.",
            workspace=workspace / "analyzer",
        )
        analyzer_id = await orchestrator.spawn_agent(analyzer_config)

        reviewer_config = AgentConfig(
            role="reviewer",
            system_prompt="You review code quality.",
            workspace=workspace / "reviewer",
        )
        reviewer_id = await orchestrator.spawn_agent(reviewer_config)

        # Orchestrator mediates communication
        analysis = await orchestrator.send_message(
            from_agent="orchestrator",
            to_agent=analyzer_id,
            message=f"Analyze: {COMPLEX_FUNCTION[:200]}...",
        )

        review = await orchestrator.send_message(
            from_agent="orchestrator",
            to_agent=reviewer_id,
            message=f"Review this analysis: {analysis[:200]}...",
        )

        # Show message log
        print("\n" + "=" * 70)
        print("MESSAGE LOG (Full Observability)")
        print("=" * 70)

        for i, msg in enumerate(orchestrator.message_log, 1):
            print(f"\n[{i}] {msg.from_agent} → {msg.to_agent}")
            print(f"    Time: {msg.timestamp.isoformat()}")
            print(f"    Content: {msg.content[:100]}...")

        print(f"\n📊 Statistics:")
        print(f"  Total messages: {len(orchestrator.message_log)}")
        print(f"  Agents spawned: {len(orchestrator.agents)}")
        print(f"  Agent IDs: {list(orchestrator.agents.keys())}")

        await orchestrator.cleanup()


async def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("EIDOLON AGENT SDK DEMO")
    print("=" * 70)
    print("\nDemonstrating:")
    print("1. Parallel analysis with multiple agents")
    print("2. Refactoring with test-based verification")
    print("3. Full observability of agent communication")

    try:
        # Demo 1: Parallel analysis
        await demo_parallel_analysis()

        # Demo 2: Refactoring with verification
        await demo_refactoring_with_verification()

        # Demo 3: Observability
        await demo_observability()

        print("\n" + "=" * 70)
        print("✅ ALL DEMOS COMPLETED")
        print("=" * 70)
        print("\nKey Benefits Demonstrated:")
        print("  ✓ Parallel agent spawning and execution")
        print("  ✓ Full observability of agent-to-agent communication")
        print("  ✓ Mediated message passing through orchestrator")
        print("  ✓ Isolated workspaces for each agent")
        print("  ✓ Conversation logging and export")
        print("  ✓ Test-based verification (not just LLM judgment)")

    except ImportError as e:
        print("\n❌ Error: Claude Agent SDK not installed")
        print("\nInstall with:")
        print("  pip install claude-agent-sdk")
        print("\nOr using uv:")
        print("  uv add claude-agent-sdk")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Demo failed")
        return 1

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
