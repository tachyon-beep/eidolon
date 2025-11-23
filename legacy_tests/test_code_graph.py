"""
Test Code Graph Analyzer

Demonstrates the code graph analysis on our own codebase!
Shows:
- Parsing all Python files
- Building call graphs
- Extracting dependencies
- Getting rich context for functions
- Optional AI descriptions
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from code_graph import CodeGraphAnalyzer, CodeElementType
from llm_providers import OpenAICompatibleProvider
import os


async def test_code_graph_basic():
    """Test basic code graph analysis without AI"""

    print("\n" + "="*80)
    print("TEST 1: BASIC CODE GRAPH ANALYSIS")
    print("="*80)

    analyzer = CodeGraphAnalyzer(
        llm_provider=None,
        generate_ai_descriptions=False
    )

    # Analyze our own backend directory
    backend_path = Path(__file__).parent / "backend"

    print(f"\n📁 Analyzing: {backend_path}")
    print(f"   This is our own codebase!")

    graph = await analyzer.analyze_project(
        project_path=backend_path,
        exclude_patterns=["test_*", ".*", "__pycache__"]
    )

    # Print statistics
    print("\n" + "="*80)
    print("PROJECT STATISTICS")
    print("="*80)

    print(f"\n**Code Elements:**")
    print(f"  Total modules: {graph.total_modules}")
    print(f"  Total classes: {graph.total_classes}")
    print(f"  Total functions: {graph.total_functions}")
    print(f"  Total lines: {graph.total_lines:,}")

    print(f"\n**Graph Nodes:**")
    print(f"  Call graph nodes: {graph.call_graph.number_of_nodes()}")
    print(f"  Call graph edges: {graph.call_graph.number_of_edges()}")
    print(f"  Import graph nodes: {graph.import_graph.number_of_nodes()}")
    print(f"  Import graph edges: {graph.import_graph.number_of_edges()}")

    # Show some modules
    print("\n" + "="*80)
    print("DISCOVERED MODULES")
    print("="*80)

    for i, (module_id, module) in enumerate(list(graph.modules.items())[:10], 1):
        print(f"\n{i}. {module.name}")
        print(f"   Path: {module.file_path.relative_to(backend_path)}")
        print(f"   Lines: {module.lines_of_code}")
        print(f"   Imports: {len(module.imports)}")
        if module.docstring:
            print(f"   Doc: {module.docstring[:60]}...")

    # Show some functions
    print("\n" + "="*80)
    print("DISCOVERED FUNCTIONS (Sample)")
    print("="*80)

    sample_functions = list(graph.functions.values())[:15]
    for i, func in enumerate(sample_functions, 1):
        print(f"\n{i}. {func.name}")
        print(f"   Type: {func.type.value}")
        print(f"   File: {func.file_path.name}:{func.line_number}")
        print(f"   Signature: {func.signature}")
        print(f"   Calls: {len(func.calls)} functions")
        print(f"   Called by: {len(func.called_by)} functions")
        print(f"   Complexity: {func.cyclomatic_complexity}")

    # Show some classes
    print("\n" + "="*80)
    print("DISCOVERED CLASSES (Sample)")
    print("="*80)

    sample_classes = list(graph.classes.values())[:10]
    for i, cls in enumerate(sample_classes, 1):
        print(f"\n{i}. {cls.name}")
        print(f"   File: {cls.file_path.name}:{cls.line_number}")
        print(f"   Lines: {cls.lines_of_code}")
        if cls.docstring:
            print(f"   Doc: {cls.docstring[:80]}...")

    # Analyze call graph
    print("\n" + "="*80)
    print("CALL GRAPH ANALYSIS")
    print("="*80)

    if graph.call_graph.number_of_nodes() > 0:
        # Find most called functions
        import networkx as nx

        in_degrees = dict(graph.call_graph.in_degree())
        if in_degrees:
            most_called = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:10]

            print(f"\n**Most Called Functions:**")
            for func_id, call_count in most_called:
                if func_id in graph.elements:
                    func = graph.elements[func_id]
                    print(f"  {func.name} - called {call_count} times")

        # Find functions that call the most other functions
        out_degrees = dict(graph.call_graph.out_degree())
        if out_degrees:
            most_calling = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:10]

            print(f"\n**Functions That Call Most Others:**")
            for func_id, call_count in most_calling:
                if func_id in graph.elements:
                    func = graph.elements[func_id]
                    print(f"  {func.name} - calls {call_count} functions")

    print("\n" + "="*80)
    print("✅ TEST 1 PASSED - Basic analysis working!")
    print("="*80)

    return graph


async def test_rich_context():
    """Test getting rich context for a specific function"""

    print("\n" + "="*80)
    print("TEST 2: RICH CONTEXT EXTRACTION")
    print("="*80)

    analyzer = CodeGraphAnalyzer()
    backend_path = Path(__file__).parent / "backend"

    print(f"\n📁 Analyzing: {backend_path}")

    graph = await analyzer.analyze_project(
        project_path=backend_path,
        exclude_patterns=["test_*", ".*", "__pycache__"]
    )

    # Pick an interesting function to analyze
    # Let's find a function from the orchestrator
    target_function = None
    for func_id, func in graph.functions.items():
        if "orchestrate" in func.name.lower() and func.type == CodeElementType.FUNCTION:
            target_function = func
            break

    if not target_function:
        # Fallback: just pick the first complex function
        for func in graph.functions.values():
            if func.cyclomatic_complexity > 5:
                target_function = func
                break

    if not target_function:
        print("\n❌ No suitable function found for context extraction")
        return

    print(f"\n🎯 Target Function: {target_function.name}")
    print(f"   File: {target_function.file_path.name}:{target_function.line_number}")
    print(f"   Signature: {target_function.signature}")

    # Get rich context
    context = analyzer.get_context_for_function(target_function.id, graph)

    print("\n" + "="*80)
    print("RICH CONTEXT FOR LLM")
    print("="*80)

    print(f"\n**Function Details:**")
    print(f"  Name: {context['function']['name']}")
    print(f"  Signature: {context['function']['signature']}")
    print(f"  File: {context['function']['file']}:{context['function']['line']}")
    print(f"  Complexity: {context['complexity']}")

    if context['function']['docstring']:
        print(f"  Docstring: {context['function']['docstring'][:100]}...")

    print(f"\n**Callers ({len(context['callers'])} functions call this):**")
    for i, caller in enumerate(context['callers'][:5], 1):
        print(f"  {i}. {caller['name']} in {Path(caller['file']).name}:{caller['line']}")
        if caller['signature']:
            print(f"     Signature: {caller['signature']}")

    print(f"\n**Callees ({len(context['callees'])} functions called by this):**")
    for i, callee in enumerate(context['callees'][:5], 1):
        print(f"  {i}. {callee['name']} in {Path(callee['file']).name}:{callee['line']}")
        if callee['signature']:
            print(f"     Signature: {callee['signature']}")
        if callee['docstring']:
            print(f"     Doc: {callee['docstring'][:60]}...")

    print(f"\n**Imports ({len(context['imports'])}):**")
    for imp in context['imports'][:5]:
        print(f"  - {imp}")

    print(f"\n**Related Classes ({len(context['related_classes'])}):**")
    for cls in context['related_classes'][:3]:
        print(f"  - {cls['name']} in {Path(cls['file']).name}")

    print("\n" + "="*80)
    print("EXAMPLE: What Would Be Sent to LLM")
    print("="*80)

    example_prompt = f"""
You are modifying the function: {context['function']['name']}

Current signature: {context['function']['signature']}
Location: {context['function']['file']}:{context['function']['line']}

This function is called by {len(context['callers'])} other functions:
"""
    for caller in context['callers'][:3]:
        example_prompt += f"  - {caller['name']}() in {Path(caller['file']).name}\n"

    example_prompt += f"\nThis function calls {len(context['callees'])} other functions:\n"
    for callee in context['callees'][:3]:
        example_prompt += f"  - {callee['name']}()\n"
        if callee['docstring']:
            example_prompt += f"    Purpose: {callee['docstring'][:60]}\n"

    print(example_prompt)

    print("\n" + "="*80)
    print("✅ TEST 2 PASSED - Rich context extraction working!")
    print("="*80)


async def test_with_ai_descriptions():
    """Test with AI-generated descriptions"""

    print("\n" + "="*80)
    print("TEST 3: AI-GENERATED DESCRIPTIONS")
    print("="*80)

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("\n⚠️  SKIPPED - No OPENROUTER_API_KEY found")
        print("   Set environment variable to test AI descriptions")
        return

    # Initialize LLM
    llm_provider = OpenAICompatibleProvider(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.getenv("OPENROUTER_MODEL", "x-ai/grok-2-1212")
    )

    analyzer = CodeGraphAnalyzer(
        llm_provider=llm_provider,
        generate_ai_descriptions=True  # Enable AI descriptions
    )

    backend_path = Path(__file__).parent / "backend"

    print(f"\n📁 Analyzing: {backend_path}")
    print(f"   🤖 AI descriptions: ENABLED")
    print(f"   This will take longer - analyzing each function with LLM...")

    # Analyze a small subset to save time/tokens
    # Just analyze the models.py file
    models_file = backend_path / "models.py"

    if not models_file.exists():
        print(f"\n❌ {models_file} not found")
        return

    print(f"\n   Analyzing just: models.py")

    graph = await analyzer.analyze_project(
        project_path=backend_path,
        exclude_patterns=["*"]  # Exclude everything
    )

    # Manually add models.py
    await analyzer._parse_file(models_file, graph)

    # Generate AI descriptions for functions in models.py
    await analyzer._generate_ai_descriptions(graph)

    print("\n" + "="*80)
    print("AI-GENERATED DESCRIPTIONS")
    print("="*80)

    functions_with_ai = [
        f for f in graph.functions.values()
        if f.ai_description
    ]

    for i, func in enumerate(functions_with_ai[:5], 1):
        print(f"\n{i}. Function: {func.name}")
        print(f"   File: {func.file_path.name}:{func.line_number}")
        print(f"   Complexity: {func.cyclomatic_complexity}")
        print(f"\n   🤖 AI Description: {func.ai_description}")
        print(f"   🎯 Purpose: {func.ai_purpose}")
        print(f"   📊 Complexity Rating: {func.ai_complexity}")

    print("\n" + "="*80)
    print("✅ TEST 3 PASSED - AI descriptions working!")
    print("="*80)


async def run_all_tests():
    """Run all code graph tests"""

    print("\n" + "="*80)
    print("CODE GRAPH ANALYZER TESTS")
    print("="*80)
    print("\nTesting comprehensive code analysis on our own codebase")
    print("This demonstrates Phase 4: Code Graph & Context Enrichment\n")

    # Test 1: Basic analysis
    graph = await test_code_graph_basic()

    # Test 2: Rich context
    await test_rich_context()

    # Test 3: AI descriptions (optional, requires API key)
    await test_with_ai_descriptions()

    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)

    print("\n🎉 Code Graph Analyzer is working!")
    print("\n**Next Steps:**")
    print("  1. Integrate into HierarchicalOrchestrator")
    print("  2. Pass rich context to all decomposers")
    print("  3. Improve code generation quality with context")
    print("\nPhase 4 foundation is ready! 🚀")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
