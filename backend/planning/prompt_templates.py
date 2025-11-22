"""
Role-Based Prompt Templates for Different Agent Types

Different agents need different personas, instructions, and output formats:
- Diagnostic: Analysis, understanding, problem identification
- Design: Architecture, planning, decomposition
- Implementation: Code generation, following patterns
- Testing: Edge cases, validation, quality assurance
- Review: Code quality, security, best practices
"""

from typing import Dict, List, Any
from enum import Enum


class AgentRole(str, Enum):
    """Different agent roles with different responsibilities"""
    DIAGNOSTIC = "diagnostic"      # Analyze and understand
    DESIGN = "design"              # Plan and decompose
    IMPLEMENTATION = "implementation"  # Generate code
    TESTING = "testing"            # Create tests
    REVIEW = "review"              # Quality check
    REFACTOR = "refactor"          # Improve existing code


class PromptTemplateLibrary:
    """
    Library of prompt templates for different agent roles and task types
    """

    @staticmethod
    def get_system_decomposer_prompt(
        user_request: str,
        project_path: str,
        subsystems: List[str],
        role: AgentRole = AgentRole.DESIGN
    ) -> Dict[str, str]:
        """Get prompt for system-level decomposition based on role"""

        if role == AgentRole.DIAGNOSTIC:
            return {
                "system": """You are a senior software architect performing diagnostic analysis.
Your goal is to deeply understand the user's request, identify all affected subsystems,
and uncover potential challenges or dependencies that aren't immediately obvious.

Think critically about:
- What is the user trying to achieve (not just what they're asking for)?
- What existing systems will be affected?
- What hidden dependencies exist?
- What could go wrong?
- What alternative approaches exist?""",

                "user": f"""# Diagnostic Analysis Request

User Request: {user_request}

Project Context:
- Path: {project_path}
- Available Subsystems: {', '.join(subsystems)}

Please analyze this request and provide:

1. **True Intent**: What is the user really trying to achieve?
2. **Affected Subsystems**: Which subsystems will need changes and why?
3. **Dependencies**: What dependencies exist between subsystems?
4. **Risks**: What could go wrong? What edge cases should we consider?
5. **Alternatives**: Are there better approaches to achieve the same goal?

Respond in JSON format with your diagnostic analysis."""
            }

        elif role == AgentRole.DESIGN:
            return {
                "system": """You are a software architect designing a decomposition plan.
Your goal is to create a clear, actionable plan that breaks down the user's request
into subsystem-level tasks with proper dependencies and priorities.

Focus on:
- Creating specific, actionable instructions (not vague descriptions)
- Identifying ALL subsystems that need changes (be comprehensive)
- Setting realistic priorities and complexity estimates
- Defining clear dependencies to ensure correct execution order
- Providing enough detail for implementation agents to execute""",

                "user": f"""# Feature Decomposition Request

User Request: {user_request}

Project Context:
- Project path: {project_path}
- Available subsystems: {', '.join(subsystems)}

Create a decomposition plan with subsystem-level tasks.

**Important Guidelines:**
- Be specific in instructions (explain exactly what to do, don't just echo the request)
- Identify ALL subsystems that need changes
- Set dependencies correctly (e.g., models before services, utils before everything)
- Use appropriate task types: create_new vs modify_existing vs refactor
- Provide enough technical detail for implementation

**Example (JWT Authentication):**
```json
{{
  "understanding": "Add JWT authentication with token generation, user password hashing, authentication service, and API endpoints",
  "subsystem_tasks": [
    {{
      "subsystem": "models",
      "instruction": "Update User model: add password_hash field (string), hash_password(password) method using bcrypt with salt, verify_password(password) method returning bool. Use bcrypt library for security.",
      "type": "modify_existing",
      "priority": "critical",
      "dependencies": [],
      "complexity": "medium"
    }},
    {{
      "subsystem": "utils",
      "instruction": "Create jwt.py module with generate_token(user_id, expiry) returning JWT string using PyJWT HS256 algorithm, and decode_token(token) returning user_id or None on failure. Handle expiry and signature validation.",
      "type": "create_new",
      "priority": "critical",
      "dependencies": [],
      "complexity": "low"
    }},
    {{
      "subsystem": "services",
      "instruction": "Create AuthService class with login(username, password) that verifies credentials using User.verify_password(), generates JWT via utils.generate_token(). Add verify_token(token) using utils.decode_token(). Add logout(token) with in-memory blacklist set.",
      "type": "create_new",
      "priority": "high",
      "dependencies": ["models", "utils"],
      "complexity": "medium"
    }},
    {{
      "subsystem": "api",
      "instruction": "Add auth routes: POST /auth/login (accepts {{username, password}}, returns {{token, user}}), POST /auth/logout (accepts token in header, returns {{message}}), GET /auth/verify (validates token, returns {{valid, user_id}}). Use AuthService for logic.",
      "type": "modify_existing",
      "priority": "high",
      "dependencies": ["services"],
      "complexity": "medium"
    }}
  ],
  "overall_complexity": "medium"
}}
```

Provide ONLY valid JSON matching this format."""
            }

        else:  # Fallback to design role
            return PromptTemplateLibrary.get_system_decomposer_prompt(
                user_request, project_path, subsystems, AgentRole.DESIGN
            )

    @staticmethod
    def get_function_generator_prompt(
        function_name: str,
        instruction: str,
        module_context: str,
        role: AgentRole = AgentRole.IMPLEMENTATION
    ) -> Dict[str, str]:
        """Get prompt for function-level code generation based on role"""

        if role == AgentRole.IMPLEMENTATION:
            return {
                "system": """You are an expert Python developer writing production-quality code.

Your code must:
- Follow Python best practices and PEP 8 style
- Include comprehensive docstrings (Google style with Args, Returns, Raises, Examples)
- Use type hints for all parameters and return values
- Handle errors appropriately (validate inputs, raise informative exceptions)
- Be secure (prevent injection, validate all user input)
- Be efficient (avoid unnecessary complexity, use appropriate data structures)
- Include inline comments only where logic isn't self-evident

Write clean, readable, maintainable code that other developers will understand.""",

                "user": f"""# Code Generation Request

Function: {function_name}
Instruction: {instruction}

Module Context:
{module_context}

Generate a complete, production-ready implementation of this function.

**Requirements:**
1. Type hints on all parameters and return value
2. Comprehensive Google-style docstring with:
   - Brief description
   - Args section with types and descriptions
   - Returns section with type and description
   - Raises section listing exceptions
   - Example usage
3. Input validation (check types, ranges, None values)
4. Proper error handling with informative messages
5. Security considerations (prevent injection, validate user input)
6. Efficient implementation (appropriate algorithms and data structures)

**Output Format:**
Provide ONLY the Python function code. No markdown formatting, no explanations outside the code."""
            }

        elif role == AgentRole.TESTING:
            return {
                "system": """You are a testing specialist writing comprehensive test cases.

Your tests must:
- Cover happy path, edge cases, and error conditions
- Use pytest with clear, descriptive test names
- Include docstrings explaining what each test validates
- Test boundary conditions (empty, None, min, max)
- Verify error handling (assert raises with correct messages)
- Be independent (no test depends on another)
- Be deterministic (same input always produces same output)""",

                "user": f"""# Test Generation Request

Function to test: {function_name}
Function behavior: {instruction}

Module Context:
{module_context}

Generate comprehensive pytest test cases for this function.

**Test Coverage Required:**
1. Happy path (normal, valid inputs)
2. Edge cases (empty, None, boundary values)
3. Error cases (invalid types, invalid values, constraint violations)
4. Security cases (injection attempts, malicious input)
5. Performance cases (large inputs, if relevant)

**Output Format:**
Provide ONLY the Python test code (pytest functions). No markdown, no explanations outside code."""
            }

        elif role == AgentRole.REVIEW:
            return {
                "system": """You are a senior code reviewer evaluating code quality, security, and best practices.

Review for:
- Correctness: Does it implement the specification correctly?
- Security: Are there vulnerabilities (injection, overflow, etc.)?
- Performance: Are there inefficiencies or scaling issues?
- Maintainability: Is it readable and well-documented?
- Best Practices: Does it follow language conventions?
- Edge Cases: Are all scenarios handled?""",

                "user": f"""# Code Review Request

Function: {function_name}
Expected behavior: {instruction}

Code to review:
{module_context}

Provide a thorough code review covering:
1. Correctness issues
2. Security vulnerabilities
3. Performance problems
4. Maintainability concerns
5. Missing edge case handling
6. Suggested improvements

Respond in JSON format with structured feedback."""
            }

        else:
            # Fallback to implementation
            return PromptTemplateLibrary.get_function_generator_prompt(
                function_name, instruction, module_context, AgentRole.IMPLEMENTATION
            )

    @staticmethod
    def get_refactoring_prompt(
        code_to_refactor: str,
        reason: str,
        role: AgentRole = AgentRole.REFACTOR
    ) -> Dict[str, str]:
        """Get prompt for code refactoring"""

        return {
            "system": """You are an expert in code refactoring and design patterns.

When refactoring, you:
- Preserve existing behavior (tests must still pass)
- Improve code structure and readability
- Eliminate code smells (duplication, long functions, god classes)
- Apply design patterns where appropriate
- Maintain or improve performance
- Keep or enhance documentation""",

            "user": f"""# Refactoring Request

Reason for refactoring: {reason}

Current code:
```python
{code_to_refactor}
```

Refactor this code to address the stated issues while:
1. Preserving all existing behavior
2. Improving code quality
3. Enhancing readability and maintainability
4. Applying best practices and patterns

Provide the refactored code with comments explaining key changes."""
        }


# Example usage:
"""
# For diagnostic analysis
prompts = PromptTemplateLibrary.get_system_decomposer_prompt(
    user_request="Add user authentication",
    project_path="/app",
    subsystems=["models", "api", "services"],
    role=AgentRole.DIAGNOSTIC
)

# For design/decomposition
prompts = PromptTemplateLibrary.get_system_decomposer_prompt(
    user_request="Add user authentication",
    project_path="/app",
    subsystems=["models", "api", "services"],
    role=AgentRole.DESIGN
)

# For implementation
prompts = PromptTemplateLibrary.get_function_generator_prompt(
    function_name="hash_password",
    instruction="Hash password using bcrypt with salt",
    module_context="...",
    role=AgentRole.IMPLEMENTATION
)

# For testing
prompts = PromptTemplateLibrary.get_function_generator_prompt(
    function_name="hash_password",
    instruction="Hash password using bcrypt with salt",
    module_context="...",
    role=AgentRole.TESTING
)
"""
