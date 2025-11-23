"""
Mock LLM Provider for Testing

Generates realistic analysis responses without making actual API calls.
Useful for testing, demos, and development.
"""

from typing import List, Dict, Any
import random
from eidolon.llm_providers import LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """Mock LLM provider that generates synthetic analysis responses"""

    def __init__(self, model: str = "mock-gpt-4", **kwargs):
        self.model = model
        self.call_count = 0

    def get_provider_name(self) -> str:
        return "mock"

    def get_model_name(self) -> str:
        return self.model

    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        """Generate mock analysis response based on context"""
        self.call_count += 1

        # Extract context from messages
        user_message = messages[0]["content"] if messages else ""

        # Determine analysis type from context
        analysis_type = self._detect_analysis_type(user_message)

        # Generate appropriate response
        content = self._generate_analysis(analysis_type, user_message)

        # Simulate token usage
        input_tokens = len(user_message.split()) * 2  # Rough approximation
        output_tokens = len(content.split()) * 2

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            finish_reason="stop"
        )

    def _detect_analysis_type(self, context: str) -> str:
        """Detect what type of analysis is being requested"""
        if "analyzing a function" in context.lower():
            return "function"
        elif "analyzing a Python class" in context.lower():
            return "class"
        elif "analyzing a Python module" in context.lower():
            return "module"
        elif "analyzing a subsystem" in context.lower():
            return "subsystem"
        elif "system-level code review" in context.lower():
            return "system"
        else:
            return "generic"

    def _generate_analysis(self, analysis_type: str, context: str) -> str:
        """Generate realistic analysis based on type"""

        if analysis_type == "function":
            return self._generate_function_analysis(context)
        elif analysis_type == "class":
            return self._generate_class_analysis(context)
        elif analysis_type == "module":
            return self._generate_module_analysis(context)
        elif analysis_type == "subsystem":
            return self._generate_subsystem_analysis(context)
        elif analysis_type == "system":
            return self._generate_system_analysis(context)
        else:
            return self._generate_generic_analysis()

    def _generate_function_analysis(self, context: str) -> str:
        """Generate function-level analysis"""
        issues = [
            {
                "title": "Missing input validation",
                "problem": "Function does not validate input parameters, which could lead to unexpected behavior or errors.",
                "severity": "Medium",
                "fix": "def validated_function(param):\n    if param is None:\n        raise ValueError('param cannot be None')\n    # existing logic"
            },
            {
                "title": "Error handling improvement",
                "problem": "Function does not handle edge cases properly.",
                "severity": "Low",
                "fix": "try:\n    # existing logic\nexcept SpecificException as e:\n    logger.error(f'Error: {e}')\n    return default_value"
            },
            {
                "title": "Performance optimization opportunity",
                "problem": "Loop could be optimized using list comprehension or generator.",
                "severity": "Low",
                "fix": "result = [process(item) for item in items if condition(item)]"
            }
        ]

        # Randomly select 1-2 issues
        selected_issues = random.sample(issues, k=random.randint(1, 2))

        response = "## Issues Found\n\n"
        for i, issue in enumerate(selected_issues, 1):
            response += f"### Issue {i}: {issue['title']}\n"
            response += f"**Problem:** {issue['problem']}\n"
            response += f"**Severity:** {issue['severity']}\n\n"
            response += "**Fix:**\n```python\n"
            response += issue['fix']
            response += "\n```\n\n"

        return response

    def _generate_class_analysis(self, context: str) -> str:
        """Generate class-level analysis"""
        observations = [
            "- **Single Responsibility Principle**: Class appears to handle multiple concerns. Consider splitting into separate classes.",
            "- **Class Cohesion**: Methods are well-organized and work toward a single purpose.",
            "- **Open/Closed Principle**: Class uses composition well, making it extensible without modification.",
            "- **Dependency Inversion**: Class depends on concrete implementations rather than abstractions. Consider using dependency injection.",
            "- **Encapsulation**: Some internal state is exposed. Consider making attributes private and providing getters/setters.",
            "- **Design Pattern**: Appears to follow the Strategy pattern effectively.",
            "- **Class Size**: Class has grown large. Consider extracting some methods into helper classes.",
        ]

        # Randomly select 2-4 observations
        selected = random.sample(observations, k=random.randint(2, 4))

        response = "## Class-Level Assessment\n\n"
        response += "\n".join(selected)
        response += "\n\n**Overall**: Class demonstrates good organization but has opportunities for improvement in adherence to SOLID principles."

        return response

    def _generate_module_analysis(self, context: str) -> str:
        """Generate module-level analysis"""
        observations = [
            "- Module organization is clear with well-separated concerns",
            "- Consider extracting helper functions into a separate utilities module",
            "- Imports are well-organized but could benefit from absolute imports",
            "- Module has grown large; consider splitting into submodules",
            "- Good separation between public and private functions",
            "- Documentation could be improved with docstrings",
            "- Consider adding type hints for better code clarity",
        ]

        smells = [
            "- **Long Module**: Module exceeds 500 lines. Consider refactoring.",
            "- **Complex Logic**: Some functions have high cyclomatic complexity.",
            "- **Duplicate Code**: Similar patterns appear multiple times.",
        ]

        # Randomly select observations and smells
        selected_obs = random.sample(observations, k=random.randint(2, 3))
        selected_smells = random.sample(smells, k=random.randint(1, 2))

        response = "## Module-Level Assessment\n\n"
        response += "### Code Quality\n"
        response += "\n".join(selected_obs)
        response += "\n\n### Code Smells Detected\n"
        response += "\n".join(selected_smells)
        response += "\n\n**Recommendation**: Refactor module to improve maintainability and reduce complexity."

        return response

    def _generate_subsystem_analysis(self, context: str) -> str:
        """Generate subsystem-level analysis"""
        observations = [
            "- **Package Cohesion**: Modules are well-organized around a central theme",
            "- **API Boundaries**: Clear public API with good encapsulation of internals",
            "- **Inter-module Coupling**: Some modules are tightly coupled; consider using dependency injection",
            "- **Architectural Pattern**: Package follows a layered architecture effectively",
            "- **Dependency Flow**: Dependencies flow in one direction, maintaining good separation",
            "- **Cross-cutting Concerns**: Logging and error handling are consistent across modules",
            "- **Package Structure**: Directory organization reflects logical grouping",
        ]

        selected = random.sample(observations, k=random.randint(3, 5))

        response = "## Subsystem-Level Assessment\n\n"
        response += "\n".join(selected)
        response += "\n\n**Overall**: Subsystem demonstrates solid architectural principles with minor opportunities for decoupling."

        return response

    def _generate_system_analysis(self, context: str) -> str:
        """Generate system-level analysis"""
        response = """## System-Level Code Review

### Overall Architecture Quality
The codebase demonstrates a well-structured hierarchical architecture with clear separation of concerns. The use of subsystems effectively organizes related functionality.

### Critical Issues Requiring Immediate Attention
- **Security**: Input validation needs strengthening across API endpoints
- **Performance**: Some database queries could benefit from indexing and optimization
- **Error Handling**: Inconsistent error handling patterns across modules

### Strategic Refactoring Recommendations
- Extract common patterns into shared utilities to reduce code duplication
- Implement comprehensive logging strategy across all subsystems
- Consider introducing an event-driven architecture for better scalability
- Strengthen type safety with comprehensive type hints

### Code Health Score
**78/100** - Good foundation with room for improvement in consistency and testing coverage.

**Priority Actions**:
1. Address security vulnerabilities in input validation (P0)
2. Improve test coverage to >80% (P1)
3. Refactor large modules into smaller, focused units (P2)
4. Document public APIs comprehensively (P2)
"""
        return response

    def _generate_generic_analysis(self) -> str:
        """Generate generic analysis when type cannot be determined"""
        return """## Analysis

The code demonstrates good practices overall with opportunities for improvement:

- Code organization is clear and logical
- Consider adding more comprehensive error handling
- Documentation could be enhanced with examples
- Type hints would improve code clarity

**Overall Assessment**: Code is functional but could benefit from additional polish and defensive programming practices.
"""
