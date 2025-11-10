#!/usr/bin/env python3
"""Demo of TDD-based refactoring using specialized prompts.

This shows how we use ONE agent type (FunctionAgent concept) with
different prompts for different tasks, rather than many agent classes.
"""

import asyncio
import os

from src.eidolon_mvp.agents.tasks import refactor_function_tdd
from src.eidolon_mvp.llm.config import create_llm_from_env


# Example complex function
COMPLEX_FUNCTION = '''def process_order(order_data):
    """Process customer order - has high complexity."""
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
'''


async def main():
    """Run refactoring demo."""
    print("=" * 70)
    print("TDD Refactoring Demo")
    print("=" * 70)
    print()
    print("This demonstrates using ONE agent type with SPECIALIZED PROMPTS")
    print("instead of creating many agent classes.")
    print()

    # Setup LLM
    llm = create_llm_from_env()
    if not llm:
        print("❌ No LLM configured")
        print()
        print("Set environment variables:")
        print("  export LLM_PROVIDER=openai-compatible")
        print("  export OPENAI_API_KEY=your-key")
        print("  export OPENAI_BASE_URL=https://openrouter.ai/api/v1")
        print("  export LLM_MODEL=anthropic/claude-3.5-sonnet")
        return 1

    print(f"✓ LLM configured: {llm.provider} / {llm.model}")
    print()

    print("Example function:")
    print("-" * 70)
    print(COMPLEX_FUNCTION[:500] + "...")
    print("-" * 70)
    print()

    # Run TDD refactoring
    result = await refactor_function_tdd(
        llm=llm,
        function_code=COMPLEX_FUNCTION,
        function_name="process_order",
        issue_description="High complexity (20+ decision points)",
    )

    if not result["success"]:
        print(f"\n❌ Refactoring failed: {result.get('error')}")
        return 1

    # Show results
    print()
    print("=" * 70)
    print("REFACTORING RESULTS")
    print("=" * 70)
    print()

    plan = result["plan"]

    print("Behavior Tests Generated:")
    print("-" * 70)
    for test in plan.behavior_tests:
        print(f"• {test.test_name}: {test.description}")
    print()

    print("Sub-functions Planned:")
    print("-" * 70)
    for sub_fn in plan.sub_functions:
        print(f"• {sub_fn.name}: {sub_fn.purpose}")
        print(f"  Signature: {sub_fn.signature}")
    print()

    print("Refactored Code:")
    print("-" * 70)
    print(result["refactored_code"][:1000])
    print("... (truncated)")
    print()

    review = result["review"]
    print("Review:")
    print("-" * 70)
    print(f"✓ Behavior preserved: {review.get('behavior_preserved', '?')}")
    print(f"✓ Complexity reduced: {review.get('complexity_reduced', '?')}")
    print(f"Status: {review.get('approval', '?')}")

    if review.get("suggestions"):
        print("\nSuggestions:")
        for suggestion in review["suggestions"]:
            print(f"  • {suggestion}")

    print()
    print("=" * 70)
    print("APPROACH")
    print("=" * 70)
    print()
    print("Instead of creating RefactoringAgent, TestGeneratorAgent, etc.,")
    print("we used FunctionAgent concept with specialized prompts:")
    print()
    print("1. PLAN_REFACTORING prompt → creates TDD plan")
    print("2. GENERATE_FUNCTION prompt → generates sub-functions")
    print("3. REVIEW_CODE prompt → verifies behavior preservation")
    print()
    print("This keeps the codebase simple while enabling complex workflows!")

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
