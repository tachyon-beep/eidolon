"""
Improved Task Decomposition with Structured Outputs and Better Prompting

Enhancements:
1. JSON Schema for structured outputs
2. Improved prompts with examples
3. Better JSON extraction from responses
4. Support for response_format parameter
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
import json
import re

from models import Task, TaskType, TaskStatus, TaskPriority
from llm_providers import LLMProvider
from logging_config import get_logger

logger = get_logger(__name__)


def extract_json_from_response(content: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling markdown code blocks

    Tries multiple extraction strategies:
    1. Direct JSON parsing
    2. Extract from ```json code blocks
    3. Extract from ``` code blocks
    4. Find first {...} or [...] object
    """
    # Strategy 1: Try direct parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from ```json blocks
    json_block_match = re.search(r'```json\s*\n(.*?)\n```', content, re.DOTALL)
    if json_block_match:
        try:
            return json.loads(json_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 3: Extract from ``` blocks
    code_block_match = re.search(r'```\s*\n(.*?)\n```', content, re.DOTALL)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except json.JSONDecodeError:
            pass

    # Strategy 4: Find first {..} object
    brace_match = re.search(r'\{.*\}', content, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


class ImprovedSystemDecomposer:
    """
    Enhanced System Decomposer with structured outputs and better prompting
    """

    # JSON Schema for subsystem decomposition response
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "understanding": {
                "type": "string",
                "description": "Brief explanation of what the user wants to achieve"
            },
            "subsystem_tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subsystem": {
                            "type": "string",
                            "description": "Name of the subsystem to modify"
                        },
                        "instruction": {
                            "type": "string",
                            "description": "Detailed instruction for what needs to be done in this subsystem"
                        },
                        "type": {
                            "type": "string",
                            "enum": ["create_new", "modify_existing", "refactor", "delete", "fix", "test"],
                            "description": "Type of change needed"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["critical", "high", "medium", "low", "optional"],
                            "description": "Priority level"
                        },
                        "dependencies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of other subsystem names this depends on"
                        },
                        "complexity": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": "Estimated complexity"
                        }
                    },
                    "required": ["subsystem", "instruction", "type", "priority", "complexity"]
                }
            },
            "overall_complexity": {
                "type": "string",
                "enum": ["low", "medium", "high"]
            }
        },
        "required": ["understanding", "subsystem_tasks", "overall_complexity"]
    }

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def _build_improved_prompt(
        self,
        user_request: str,
        project_path: str,
        subsystems: List[str]
    ) -> str:
        """Build improved prompt with clear instructions and examples"""

        prompt = f"""You are a system architect analyzing a user's feature request and decomposing it into subsystem-level tasks.

# User Request
{user_request}

# Project Context
- Project path: {project_path}
- Available subsystems: {', '.join(subsystems)}

# Your Task
Analyze the request and create a decomposition plan that:
1. Identifies which subsystems need changes
2. Defines specific, actionable instructions for each subsystem
3. Determines task type, priority, and complexity
4. Identifies dependencies between subsystem tasks

# Important Guidelines
- Be specific in instructions (don't just echo the user request)
- Identify ALL subsystems that need changes (don't miss any)
- Set realistic priorities (critical=must have, high=important, medium=nice to have)
- Consider dependencies (e.g., models must exist before services can use them)
- Type should match the actual work: create_new vs modify_existing vs refactor

# Example Response Format
```json
{{
  "understanding": "Add JWT authentication system with token generation, user password hashing, authentication service, and API endpoints",
  "subsystem_tasks": [
    {{
      "subsystem": "models",
      "instruction": "Update User model to add password_hash field (string), hash_password(password) method using bcrypt, and verify_password(password) method that returns bool",
      "type": "modify_existing",
      "priority": "critical",
      "dependencies": [],
      "complexity": "medium"
    }},
    {{
      "subsystem": "utils",
      "instruction": "Create JWT utilities module with generate_token(user_id, expiry) that returns JWT string and decode_token(token) that returns user_id or None. Use PyJWT library with HS256 algorithm",
      "type": "create_new",
      "priority": "critical",
      "dependencies": [],
      "complexity": "low"
    }},
    {{
      "subsystem": "services",
      "instruction": "Create AuthService class with login(username, password) that returns JWT token using User model and JWT utils, verify_token(token) that returns user_id, and logout(token) that invalidates token via blacklist",
      "type": "create_new",
      "priority": "high",
      "dependencies": ["models", "utils"],
      "complexity": "medium"
    }},
    {{
      "subsystem": "api",
      "instruction": "Add authentication endpoints: POST /auth/login (accepts username/password, returns token), POST /auth/logout (invalidates token), GET /auth/verify (validates token, returns user info)",
      "type": "modify_existing",
      "priority": "high",
      "dependencies": ["services"],
      "complexity": "medium"
    }}
  ],
  "overall_complexity": "medium"
}}
```

# Your Response
Provide ONLY valid JSON matching the format above. No markdown formatting, no explanations outside the JSON.
"""
        return prompt

    async def decompose(
        self,
        user_request: str,
        project_path: str,
        subsystems: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose user request into subsystem tasks using structured outputs
        """
        context = context or {}

        # Build improved prompt
        prompt = self._build_improved_prompt(user_request, project_path, subsystems)

        # Call LLM with structured output request
        try:
            # Try to use JSON mode if supported (OpenAI, some providers)
            response = await self.llm_provider.create_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a software architect. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4096,
                temperature=0.0,
                response_format={"type": "json_object"}  # Structured output
            )
        except (TypeError, Exception) as e:
            # Fallback if response_format not supported
            logger.warning(f"Structured output not supported, using regular mode: {e}")
            response = await self.llm_provider.create_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a software architect. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=4096,
                temperature=0.0
            )

        # Extract JSON from response using improved extraction
        plan = extract_json_from_response(response.content)

        if not plan:
            logger.error("Failed to extract JSON from LLM response", response=response.content[:500])
            # Fallback: create minimal task structure
            plan = {
                "understanding": user_request,
                "subsystem_tasks": [
                    {
                        "subsystem": subsystems[0] if subsystems else "root",
                        "instruction": user_request,
                        "type": "modify_existing",
                        "priority": "high",
                        "dependencies": [],
                        "complexity": "medium"
                    }
                ],
                "overall_complexity": "medium"
            }

        # Validate response has required fields
        if "subsystem_tasks" not in plan:
            logger.warning("Response missing subsystem_tasks, using fallback")
            plan["subsystem_tasks"] = []

        # Create Task objects
        tasks = []
        for i, subtask_def in enumerate(plan.get("subsystem_tasks", [])):
            task = Task(
                id=f"T-SYS-{uuid.uuid4().hex[:8]}",
                parent_task_id=None,
                type=TaskType(subtask_def.get("type", "modify_existing")),
                scope="SUBSYSTEM",
                target=subtask_def.get("subsystem", "unknown"),
                instruction=subtask_def.get("instruction", ""),
                context={
                    "user_request": user_request,
                    "project_path": project_path,
                    **context
                },
                dependencies=[],
                priority=self._parse_priority(subtask_def.get("priority", "medium")),
                estimated_complexity=subtask_def.get("complexity", "medium")
            )
            tasks.append(task)

        # Resolve dependencies
        task_by_subsystem = {t.target: t for t in tasks}
        for i, subtask_def in enumerate(plan.get("subsystem_tasks", [])):
            for dep_name in subtask_def.get("dependencies", []):
                if dep_name in task_by_subsystem:
                    tasks[i].dependencies.append(task_by_subsystem[dep_name].id)

        logger.info(
            "system_decomposition_complete",
            tasks=len(tasks),
            understanding=plan.get("understanding", ""),
            structured_output_used=bool(plan and "subsystem_tasks" in plan)
        )

        return tasks

    def _parse_priority(self, priority_str: str) -> TaskPriority:
        """Parse priority string to enum"""
        mapping = {
            "critical": TaskPriority.CRITICAL,
            "high": TaskPriority.HIGH,
            "medium": TaskPriority.MEDIUM,
            "low": TaskPriority.LOW,
            "optional": TaskPriority.OPTIONAL
        }
        return mapping.get(priority_str.lower(), TaskPriority.MEDIUM)
