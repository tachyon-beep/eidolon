"""
Gemini Pro: Proactive Enhancement Suggestions for MONAD

Let Gemini analyze the MONAD codebase and suggest strategic improvements,
optimizations, and new features that would make the system better.
"""
import asyncio
import sys
import os
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables.")
    pass

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from llm_providers import create_provider


async def get_gemini_enhancements():
    """
    Ask Gemini to analyze MONAD and suggest proactive enhancements
    """
    print("\n" + "=" * 80)
    print("GEMINI PRO: Proactive Enhancement Suggestions for MONAD")
    print("=" * 80)
    print("\nAsking Gemini to analyze the codebase and suggest improvements...\n")

    # Create Gemini Pro provider
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in .env file")

    gemini_provider = create_provider(
        "openai",
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.getenv("OPENROUTER_MODEL", "google/gemini-pro-1.5-preview")
    )

    print(f"🤖 LLM Provider: {gemini_provider.get_provider_name()}")
    print(f"📦 Model: {gemini_provider.get_model_name()}")
    print()

    # Scan MONAD codebase
    project_path = Path(__file__).parent
    backend_path = project_path / "backend"

    # Collect codebase structure
    subsystems = {}
    total_files = 0
    total_lines = 0

    for py_file in backend_path.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            rel_path = py_file.relative_to(backend_path)
            subsystem = rel_path.parts[0] if len(rel_path.parts) > 1 else "root"

            if subsystem not in subsystems:
                subsystems[subsystem] = {"files": [], "lines": 0}

            try:
                content = py_file.read_text()
                lines = len(content.split('\n'))
                subsystems[subsystem]["files"].append(str(rel_path))
                subsystems[subsystem]["lines"] += lines
                total_files += 1
                total_lines += lines
            except:
                pass

    print(f"📊 Codebase Analysis:")
    print(f"   Total Python files: {total_files}")
    print(f"   Total lines of code: {total_lines:,}")
    print(f"   Subsystems: {len(subsystems)}")
    print()

    # Read key architecture files for context
    key_files_content = {}
    key_files = [
        "models/task.py",
        "planning/decomposition.py",
        "agents/implementation_orchestrator.py",
        "llm_providers/base.py"
    ]

    for key_file in key_files:
        file_path = backend_path / key_file
        if file_path.exists():
            try:
                content = file_path.read_text()
                # Limit to first 100 lines for context
                lines = content.split('\n')[:100]
                key_files_content[key_file] = '\n'.join(lines)
            except:
                pass

    # Prepare comprehensive prompt for Gemini
    prompt = f"""You are an expert software architect analyzing the MONAD system - a hierarchical AI agent system for code generation and modification.

## Current MONAD Architecture

### Overview
MONAD is a 5-tier hierarchical agent system that decomposes user feature requests into executable tasks:
- SYSTEM tier: Overall feature orchestration
- SUBSYSTEM tier: Package/directory level changes
- MODULE tier: File-level modifications
- CLASS tier: Class definitions
- FUNCTION tier: Individual functions/methods

### Codebase Structure
Total Files: {total_files}
Total Lines: {total_lines:,}

Subsystems ({len(subsystems)}):
{chr(10).join(f"  • {name}: {info['lines']:,} lines in {len(info['files'])} files" for name, info in sorted(subsystems.items()))}

### Key Components

1. **Task Decomposition** (planning/)
   - SystemDecomposer: Breaks user requests into subsystem tasks
   - SubsystemDecomposer: Creates module-level tasks
   - ModuleDecomposer: Creates class/function tasks
   - Uses LLM to intelligently decompose each tier

2. **Implementation** (agents/)
   - ImplementationOrchestrator: Coordinates entire implementation
   - Executes tasks bottom-up after top-down decomposition
   - Handles dependencies, rollback, testing

3. **LLM Integration** (llm_providers/)
   - Multi-provider support (Anthropic, OpenAI, OpenRouter, Mock)
   - Pluggable architecture for different LLMs

4. **Storage** (storage/)
   - SQLite-based task tracking
   - Audit trail of all operations

5. **File Operations** (agents/code_writer.py)
   - Atomic writes with backups
   - Rollback capability
   - Session-based backup management

### Current Capabilities
✅ Top-down task decomposition
✅ Bottom-up execution with dependencies
✅ Multi-LLM provider support
✅ Automatic rollback on failure
✅ File backup and audit trail
✅ Type hints and Pydantic models
✅ Structured logging

### Known Limitations
- No agent-to-agent negotiation (Phase 3 planned)
- Limited error recovery (basic retry needed)
- No test execution (enable_testing=False currently)
- No code quality analysis
- No user approval workflows
- No metrics/observability
- No rate limiting
- No caching of LLM responses

## Your Task

As an expert architect, analyze this system and provide **proactive enhancement suggestions** in the following categories:

### 1. Architecture Improvements
Suggest architectural changes that would make the system:
- More robust and reliable
- More scalable and performant
- Easier to maintain and extend
- Better separated concerns

### 2. Missing Features
Identify high-value features that are missing:
- What would make this system more useful?
- What do production systems need that this lacks?
- What would improve the developer experience?

### 3. Code Quality & Best Practices
Suggest improvements to:
- Code organization
- Error handling patterns
- Testing strategy
- Documentation
- Type safety

### 4. Performance Optimizations
Identify opportunities to:
- Reduce LLM API calls
- Speed up task execution
- Cache intermediate results
- Parallelize better

### 5. User Experience
How to make the system:
- Easier to use
- More transparent (show progress)
- Better error messages
- More configurable

### 6. Security & Safety
What security/safety features are needed:
- Code injection prevention
- Resource limits
- Sandboxing
- Audit logging improvements

### 7. Integration & Ecosystem
How to better integrate with:
- Version control (git)
- CI/CD pipelines
- IDEs
- Testing frameworks
- Code quality tools

## Response Format

Please provide your analysis in this structure:

```json
{{
  "top_priorities": [
    {{
      "title": "Clear, actionable title",
      "category": "Architecture|Feature|Performance|UX|Security|Integration",
      "priority": "critical|high|medium|low",
      "effort": "small|medium|large",
      "impact": "Brief description of business value",
      "rationale": "Why this matters for MONAD",
      "implementation_hint": "High-level approach to implement"
    }}
  ],
  "quick_wins": [
    {{
      "title": "Easy improvements with good ROI",
      "effort": "small",
      "implementation": "Specific steps to implement"
    }}
  ],
  "strategic_enhancements": [
    {{
      "title": "Major features for future phases",
      "phase": "Phase 3|Phase 4|Future",
      "dependencies": ["What needs to exist first"],
      "description": "Detailed explanation"
    }}
  ],
  "code_smells_found": [
    {{
      "location": "Subsystem or file",
      "issue": "What's problematic",
      "fix": "How to improve it"
    }}
  ]
}}
```

Be creative, strategic, and specific. Think like a principal engineer reviewing a production system.
"""

    print("🔄 Querying Gemini Pro for enhancement suggestions...")
    print("   (This may take 30-60 seconds for comprehensive analysis)\n")

    import time
    start_time = time.time()

    response = await gemini_provider.create_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
        temperature=0.7  # Higher temperature for creativity
    )

    elapsed_time = time.time() - start_time

    print(f"✅ Analysis complete in {elapsed_time:.1f}s")
    print("\n" + "=" * 80)
    print("GEMINI PRO ENHANCEMENT SUGGESTIONS")
    print("=" * 80)
    print()

    # Parse and display response
    import json
    try:
        # Try to extract JSON from response
        content = response.content
        if "```json" in content:
            json_start = content.index("```json") + 7
            json_end = content.index("```", json_start)
            json_str = content[json_start:json_end].strip()
            suggestions = json.loads(json_str)

            # Display top priorities
            if "top_priorities" in suggestions:
                print("🎯 TOP PRIORITY ENHANCEMENTS")
                print("=" * 80)
                for i, item in enumerate(suggestions["top_priorities"], 1):
                    print(f"\n{i}. {item.get('title', 'Untitled')}")
                    print(f"   Category: {item.get('category', 'N/A')}")
                    print(f"   Priority: {item.get('priority', 'N/A')} | Effort: {item.get('effort', 'N/A')}")
                    print(f"   Impact: {item.get('impact', 'N/A')}")
                    print(f"   Rationale: {item.get('rationale', 'N/A')}")
                    if 'implementation_hint' in item:
                        print(f"   How: {item['implementation_hint']}")

            # Display quick wins
            if "quick_wins" in suggestions:
                print("\n\n⚡ QUICK WINS (Easy improvements)")
                print("=" * 80)
                for i, item in enumerate(suggestions["quick_wins"], 1):
                    print(f"\n{i}. {item.get('title', 'Untitled')}")
                    print(f"   Effort: {item.get('effort', 'small')}")
                    print(f"   How: {item.get('implementation', 'N/A')}")

            # Display strategic enhancements
            if "strategic_enhancements" in suggestions:
                print("\n\n🚀 STRATEGIC ENHANCEMENTS (Future phases)")
                print("=" * 80)
                for i, item in enumerate(suggestions["strategic_enhancements"], 1):
                    print(f"\n{i}. {item.get('title', 'Untitled')} [{item.get('phase', 'Future')}]")
                    print(f"   {item.get('description', 'N/A')}")
                    if item.get('dependencies'):
                        print(f"   Depends on: {', '.join(item['dependencies'])}")

            # Display code smells
            if "code_smells_found" in suggestions:
                print("\n\n🔍 CODE SMELLS & IMPROVEMENTS")
                print("=" * 80)
                for i, item in enumerate(suggestions["code_smells_found"], 1):
                    print(f"\n{i}. {item.get('location', 'Unknown')}")
                    print(f"   Issue: {item.get('issue', 'N/A')}")
                    print(f"   Fix: {item.get('fix', 'N/A')}")

            # Save full response to file
            output_file = Path(__file__).parent / "GEMINI_ENHANCEMENT_SUGGESTIONS.md"
            with output_file.open('w') as f:
                f.write("# Gemini Pro: MONAD Enhancement Suggestions\n\n")
                f.write(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Model**: {gemini_provider.get_model_name()}\n")
                f.write(f"**Analysis Time**: {elapsed_time:.1f}s\n\n")
                f.write("---\n\n")
                f.write("## Full Response\n\n")
                f.write("```json\n")
                f.write(json.dumps(suggestions, indent=2))
                f.write("\n```\n\n")
                f.write("## Raw Response\n\n")
                f.write(content)

            print(f"\n\n📄 Full suggestions saved to: {output_file.name}")

        else:
            # No JSON, display raw response
            print(content)

            # Save raw response
            output_file = Path(__file__).parent / "GEMINI_ENHANCEMENT_SUGGESTIONS.md"
            with output_file.open('w') as f:
                f.write("# Gemini Pro: MONAD Enhancement Suggestions\n\n")
                f.write(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"**Model**: {gemini_provider.get_model_name()}\n\n")
                f.write("---\n\n")
                f.write(content)

            print(f"\n\n📄 Suggestions saved to: {output_file.name}")

    except json.JSONDecodeError:
        print("⚠️  Could not parse JSON response, displaying raw text:\n")
        print(response.content)
    except Exception as e:
        print(f"⚠️  Error processing response: {e}\n")
        print("Raw response:")
        print(response.content)

    print("\n" + "=" * 80)
    print("✅ Enhancement analysis complete!")
    print("=" * 80)

    return response


if __name__ == "__main__":
    asyncio.run(get_gemini_enhancements())
