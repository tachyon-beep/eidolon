"""RefactoringAgent that breaks down complex functions using TDD.

Workflow:
1. Extract function signature and behavior
2. Generate test cases that capture current behavior
3. Plan refactoring (identify sub-functions)
4. Generate new functions with tests
5. Verify behavior preservation
"""

import ast
import textwrap
from dataclasses import dataclass
from typing import Optional

from ..llm.client import LLMClient
from .base import Agent, Scope
from .models import Finding


@dataclass
class FunctionSignature:
    """Extracted function signature."""

    name: str
    args: list[str]
    return_type: Optional[str]
    docstring: Optional[str]


@dataclass
class BehaviorTest:
    """Test case that captures function behavior."""

    inputs: dict  # Argument name -> value
    expected_output: str  # What the function should return
    test_name: str
    description: str


@dataclass
class SubFunction:
    """A proposed sub-function from refactoring."""

    name: str
    purpose: str
    signature: str
    implementation: Optional[str] = None


@dataclass
class RefactoringPlan:
    """Complete refactoring plan."""

    original_function: str
    original_signature: FunctionSignature
    behavior_tests: list[BehaviorTest]
    sub_functions: list[SubFunction]
    main_function_logic: str
    reasoning: str


class RefactoringAgent(Agent):
    """Agent that refactors complex functions using TDD."""

    def __init__(
        self,
        function_name: str,
        source_code: str,
        file_path: str,
        issue: Finding,
        llm: LLMClient,
        memory_store: "MemoryStore",
    ):
        """Initialize refactoring agent.

        Args:
            function_name: Name of function to refactor
            source_code: Complete module source
            file_path: Path to file
            issue: The finding that triggered refactoring
            llm: LLM client for planning
            memory_store: Memory storage
        """
        super().__init__(
            agent_id=f"refactor:{file_path}:{function_name}",
            scope=Scope(type="function", id=function_name, path=file_path),
            memory_store=memory_store,
        )
        self.function_name = function_name
        self.source_code = source_code
        self.file_path = file_path
        self.issue = issue
        self.llm = llm

        # Extract the function
        self.function_node = self._extract_function()
        self.function_code = self._get_function_code()

    def _extract_function(self) -> Optional[ast.FunctionDef]:
        """Extract the function AST node."""
        try:
            tree = ast.parse(self.source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == self.function_name:
                    return node
        except SyntaxError:
            pass
        return None

    def _get_function_code(self) -> str:
        """Get the function's source code."""
        if self.function_node:
            return ast.unparse(self.function_node)
        return ""

    async def analyze(self) -> list[Finding]:
        """Create refactoring plan (not used in standard flow)."""
        return [self.issue]

    async def create_refactoring_plan(self) -> RefactoringPlan:
        """Create a complete refactoring plan with TDD.

        Returns:
            RefactoringPlan with tests and sub-functions
        """
        print(f"🔍 Analyzing function: {self.function_name}")
        print(f"   Issue: {self.issue.description}")
        print()

        # Step 1: Extract signature
        signature = self._extract_signature()
        print(f"✓ Extracted signature: {signature.name}({', '.join(signature.args)})")

        # Step 2: Generate behavior tests (capture current behavior)
        print("\n📝 Generating behavior tests to capture current behavior...")
        behavior_tests = await self._generate_behavior_tests(signature)
        print(f"✓ Generated {len(behavior_tests)} test cases")
        for test in behavior_tests:
            print(f"   • {test.test_name}: {test.description}")

        # Step 3: Plan refactoring (identify sub-functions)
        print("\n🎯 Planning refactoring...")
        sub_functions = await self._plan_sub_functions(signature)
        print(f"✓ Planned {len(sub_functions)} sub-functions:")
        for sub_fn in sub_functions:
            print(f"   • {sub_fn.name}: {sub_fn.purpose}")

        # Step 4: Generate main function logic
        print("\n🔧 Generating new main function logic...")
        main_logic = await self._generate_main_logic(signature, sub_functions)
        print("✓ Main function logic generated")

        return RefactoringPlan(
            original_function=self.function_code,
            original_signature=signature,
            behavior_tests=behavior_tests,
            sub_functions=sub_functions,
            main_function_logic=main_logic,
            reasoning=f"Refactoring to reduce complexity from {self.issue.description}",
        )

    def _extract_signature(self) -> FunctionSignature:
        """Extract function signature."""
        if not self.function_node:
            return FunctionSignature(self.function_name, [], None, None)

        args = [arg.arg for arg in self.function_node.args.args]

        # Get return type if annotated
        return_type = None
        if self.function_node.returns:
            return_type = ast.unparse(self.function_node.returns)

        # Get docstring
        docstring = ast.get_docstring(self.function_node)

        return FunctionSignature(
            name=self.function_name,
            args=args,
            return_type=return_type,
            docstring=docstring,
        )

    async def _generate_behavior_tests(
        self, signature: FunctionSignature
    ) -> list[BehaviorTest]:
        """Generate test cases that capture current behavior.

        This is TDD Step 1: Write tests that pass with current code.
        """
        prompt = f"""Generate test cases that capture the behavior of this function.

Function:
```python
{self.function_code}
```

For each test case, provide:
1. Input arguments (as dict)
2. Expected output
3. Test name
4. Brief description of what it tests

Focus on:
- Edge cases
- Normal cases
- Error cases

Return JSON array:
[
  {{
    "test_name": "test_normal_case",
    "description": "Tests typical input",
    "inputs": {{"arg1": "value1", "arg2": 123}},
    "expected_output": "expected result"
  }}
]

Generate 3-5 tests that cover key behavior.
"""

        try:
            response = await self.llm.complete(prompt, json_mode=True)

            tests = []
            if isinstance(response, list):
                for item in response:
                    tests.append(
                        BehaviorTest(
                            test_name=item.get("test_name", "test_case"),
                            description=item.get("description", ""),
                            inputs=item.get("inputs", {}),
                            expected_output=str(item.get("expected_output", "")),
                        )
                    )

            return tests
        except Exception as e:
            print(f"   Warning: Could not generate tests: {e}")
            return []

    async def _plan_sub_functions(
        self, signature: FunctionSignature
    ) -> list[SubFunction]:
        """Plan how to break function into smaller pieces.

        This is the refactoring planning step.
        """
        prompt = f"""Analyze this complex function and propose how to break it into smaller sub-functions.

Function:
```python
{self.function_code}
```

Issue: {self.issue.description}

Propose 2-4 sub-functions that:
1. Each have a single, clear purpose
2. Reduce the complexity of the main function
3. Are well-named and focused

For each sub-function provide:
- name: descriptive function name
- purpose: what it does
- signature: full function signature with types

Return JSON:
[
  {{
    "name": "validate_inputs",
    "purpose": "Validate and sanitize input arguments",
    "signature": "def validate_inputs(data: dict) -> dict:"
  }}
]
"""

        try:
            response = await self.llm.complete(prompt, json_mode=True)

            sub_fns = []
            if isinstance(response, list):
                for item in response:
                    sub_fns.append(
                        SubFunction(
                            name=item.get("name", "helper"),
                            purpose=item.get("purpose", ""),
                            signature=item.get("signature", "def helper():"),
                        )
                    )

            return sub_fns
        except Exception as e:
            print(f"   Warning: Could not plan sub-functions: {e}")
            return []

    async def _generate_main_logic(
        self, signature: FunctionSignature, sub_functions: list[SubFunction]
    ) -> str:
        """Generate new main function that calls sub-functions.

        This is TDD Step 2: Refactor while keeping tests passing.
        """
        prompt = f"""Given these sub-functions, generate the new main function logic.

Original function:
```python
{self.function_code}
```

Proposed sub-functions:
{self._format_sub_functions(sub_functions)}

Generate the new main function that:
1. Calls these sub-functions in the right order
2. Preserves the original behavior
3. Is simpler and easier to understand

Return just the function body (the logic inside the function).
"""

        try:
            response = await self.llm.complete(prompt, json_mode=False)
            return response.strip()
        except Exception as e:
            print(f"   Warning: Could not generate main logic: {e}")
            return "# Failed to generate logic"

    def _format_sub_functions(self, sub_functions: list[SubFunction]) -> str:
        """Format sub-functions for prompt."""
        lines = []
        for sf in sub_functions:
            lines.append(f"- {sf.name}: {sf.purpose}")
            lines.append(f"  Signature: {sf.signature}")
        return "\n".join(lines)

    async def generate_sub_function_code(self, sub_fn: SubFunction) -> str:
        """Generate implementation for a sub-function.

        This is TDD Step 3: Implement each sub-function.
        """
        prompt = f"""Implement this sub-function extracted from refactoring.

Sub-function to implement:
Name: {sub_fn.name}
Purpose: {sub_fn.purpose}
Signature: {sub_fn.signature}

Original complex function context:
```python
{self.function_code}
```

Generate the complete implementation including:
1. Function signature with type hints
2. Docstring
3. Implementation
4. Return statement

Return just the Python code.
"""

        try:
            response = await self.llm.complete(prompt, json_mode=False)
            # Extract code if in markdown
            if "```python" in response:
                response = response.split("```python")[1].split("```")[0].strip()
            return response
        except Exception as e:
            return f"# Failed to generate: {e}"

    def format_refactored_code(self, plan: RefactoringPlan) -> str:
        """Format the complete refactored code."""
        parts = []

        # Add sub-functions
        for sub_fn in plan.sub_functions:
            if sub_fn.implementation:
                parts.append(sub_fn.implementation)
                parts.append("")

        # Add main function
        sig = plan.original_signature
        args_str = ", ".join(sig.args)
        return_type = f" -> {sig.return_type}" if sig.return_type else ""

        main_fn = f"""def {sig.name}({args_str}){return_type}:
    \"\"\"{sig.docstring or 'Refactored function.'}\"\"\"
{textwrap.indent(plan.main_function_logic, '    ')}
"""
        parts.append(main_fn)

        return "\n".join(parts)
