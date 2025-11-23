#!/usr/bin/env python3
"""
Test script for 5-tier hierarchical agent system

Runs MONAD analysis on a sample project using mock LLM provider
to demonstrate the 5-tier hierarchy without making real API calls.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from agents.orchestrator import AgentOrchestrator
from storage import Database
from llm_providers import create_provider


async def print_hierarchy(orchestrator, agent_id, indent=0):
    """Recursively print agent hierarchy"""
    agent = await orchestrator.db.get_agent(agent_id)
    if not agent:
        return

    # Format agent info
    prefix = "  " * indent
    scope_emoji = {
        "System": "🌐",
        "Subsystem": "📁",
        "Module": "📄",
        "Class": "🏛️",
        "Function": "⚙️"
    }

    emoji = scope_emoji.get(agent.scope, "❓")
    target = agent.target.replace("/tmp/sample_project", ".")
    if "::" in target:
        # Extract just the class/function name
        parts = target.split("::")
        target = f"{Path(parts[0]).name}::{parts[1]}"

    print(f"{prefix}{emoji} {agent.scope}: {target}")
    print(f"{prefix}   Status: {agent.status} | Findings: {len(agent.findings)} | Cards: {len(agent.cards_created)}")

    # Print some findings
    if agent.findings:
        for finding in agent.findings[:2]:  # Show first 2 findings
            print(f"{prefix}   - {finding[:80]}...")

    # Recurse to children
    for child_id in agent.children_ids:
        await print_hierarchy(orchestrator, child_id, indent + 1)


async def main():
    """Main test function"""
    print("=" * 80)
    print("MONAD 5-Tier Hierarchical Agent System - Test Run")
    print("=" * 80)
    print()

    # Initialize components
    print("📦 Initializing components...")
    db = Database(":memory:")  # Use in-memory database
    await db.connect()

    # Create mock LLM provider
    print("🤖 Creating mock LLM provider...")
    mock_provider = create_provider("mock", model="mock-gpt-4")
    print(f"   Provider: {mock_provider.get_provider_name()}")
    print(f"   Model: {mock_provider.get_model_name()}")
    print()

    # Create orchestrator
    print("🎭 Creating orchestrator...")
    orchestrator = AgentOrchestrator(
        db=db,
        llm_provider=mock_provider,
        max_concurrent_modules=3,
        max_concurrent_functions=5,
        enable_cache=False  # Disable cache for demo
    )
    await orchestrator.initialize()
    print()

    # Run analysis on sample project
    sample_project_path = "/tmp/sample_project"
    print(f"🔍 Analyzing sample project: {sample_project_path}")
    print()

    try:
        system_agent = await orchestrator.analyze_codebase(sample_project_path)

        print("\n" + "=" * 80)
        print("✅ Analysis Complete!")
        print("=" * 80)
        print()

        # Print progress summary
        progress = orchestrator.get_progress()
        print("📊 Analysis Summary:")
        print(f"   Subsystems: {progress['completed_subsystems']}/{progress['total_subsystems']}")
        print(f"   Modules: {progress['completed_modules']}/{progress['total_modules']}")
        print(f"   Classes: {progress['completed_classes']}/{progress['total_classes']}")
        print(f"   Functions: {progress['completed_functions']}/{progress['total_functions']}")
        print(f"   Cache Hits: {progress['cache_hits']}")
        print(f"   Cache Misses: {progress['cache_misses']}")
        print(f"   Errors: {len(progress['errors'])}")
        print()

        # Print full hierarchy
        print("=" * 80)
        print("🌳 Complete Agent Hierarchy:")
        print("=" * 80)
        print()
        await print_hierarchy(orchestrator, system_agent.id)
        print()

        # Count cards created
        all_cards = []
        agents_to_check = [system_agent.id]
        checked = set()

        while agents_to_check:
            agent_id = agents_to_check.pop(0)
            if agent_id in checked:
                continue
            checked.add(agent_id)

            agent = await db.get_agent(agent_id)
            if agent:
                all_cards.extend(agent.cards_created)
                agents_to_check.extend(agent.children_ids)

        print("=" * 80)
        print(f"💳 Cards Created: {len(all_cards)}")
        print("=" * 80)

        # Show sample cards
        if all_cards:
            print("\nSample Cards:")
            for card_id in all_cards[:5]:  # Show first 5 cards
                card = await db.get_card(card_id)
                if card:
                    print(f"\n  📋 {card.type}: {card.title}")
                    print(f"     Status: {card.status} | Priority: {card.priority}")
                    print(f"     Owner: {card.owner_agent}")
                    # Print first 150 chars of summary
                    summary_preview = card.summary[:150].replace("\n", " ")
                    print(f"     Summary: {summary_preview}...")

        print("\n" + "=" * 80)
        print("🎉 Test Complete!")
        print("=" * 80)

        # Print mock provider stats
        print(f"\n📈 Mock LLM Stats:")
        print(f"   Total API calls: {mock_provider.call_count}")
        print(f"   Cost: $0.00 (mock)")

    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
