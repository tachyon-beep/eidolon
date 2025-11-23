"""
Intelligent Agent Selection System

The orchestrator needs to decide:
1. What TYPE of agent to use (diagnostic, design, implementation, testing, review, refactor)
2. What TIER to operate at (system, subsystem, module, class, function)

This requires meta-reasoning about the user's request.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import re

from eidolon.planning.prompt_templates import AgentRole
from eidolon.llm_providers import LLMProvider
from eidolon.logging_config import get_logger

logger = get_logger(__name__)


class AgentTier(str, Enum):
    """Hierarchical tiers where agents operate"""
    SYSTEM = "system"          # System-wide orchestration
    SUBSYSTEM = "subsystem"    # Package/directory level
    MODULE = "module"          # File level
    CLASS = "class"            # Class definition level
    FUNCTION = "function"      # Function/method level


class AgentCapability:
    """Describes what an agent can do"""
    def __init__(
        self,
        role: AgentRole,
        tier: AgentTier,
        strengths: List[str],
        keywords: List[str]
    ):
        self.role = role
        self.tier = tier
        self.strengths = strengths
        self.keywords = keywords


class IntelligentAgentSelector:
    """
    Analyzes user requests and intelligently selects the appropriate agent type and tier

    Uses both heuristics and LLM-powered reasoning to make decisions.
    """

    # Agent capability catalog
    AGENT_CATALOG = [
        # DIAGNOSTIC agents - analyze and understand
        AgentCapability(
            role=AgentRole.DIAGNOSTIC,
            tier=AgentTier.SYSTEM,
            strengths=[
                "Analyze system-wide issues",
                "Identify root causes of problems",
                "Detect architecture smells",
                "Find performance bottlenecks"
            ],
            keywords=[
                "why", "analyze", "investigate", "debug", "diagnose",
                "find bug", "slow", "not working", "broken", "issue",
                "problem", "error", "fail"
            ]
        ),

        # DESIGN agents - plan and decompose
        AgentCapability(
            role=AgentRole.DESIGN,
            tier=AgentTier.SYSTEM,
            strengths=[
                "Decompose features into subsystem tasks",
                "Identify affected components",
                "Define dependencies",
                "Create implementation plans"
            ],
            keywords=[
                "add", "create", "implement", "build", "design",
                "feature", "new", "architecture", "plan", "how to"
            ]
        ),

        # IMPLEMENTATION agents - write code
        AgentCapability(
            role=AgentRole.IMPLEMENTATION,
            tier=AgentTier.FUNCTION,
            strengths=[
                "Write production-quality code",
                "Follow best practices",
                "Handle edge cases",
                "Generate comprehensive docs"
            ],
            keywords=[
                "write", "code", "function", "method", "implement",
                "generate", "create function"
            ]
        ),

        # TESTING agents - create tests
        AgentCapability(
            role=AgentRole.TESTING,
            tier=AgentTier.MODULE,
            strengths=[
                "Generate comprehensive test suites",
                "Cover edge cases",
                "Test error handling",
                "Validate security"
            ],
            keywords=[
                "test", "pytest", "unittest", "coverage", "validate",
                "verify", "check"
            ]
        ),

        # REVIEW agents - quality check
        AgentCapability(
            role=AgentRole.REVIEW,
            tier=AgentTier.MODULE,
            strengths=[
                "Evaluate code quality",
                "Check security vulnerabilities",
                "Verify best practices",
                "Suggest improvements"
            ],
            keywords=[
                "review", "check quality", "security audit", "code smell",
                "improve", "best practice", "vulnerable"
            ]
        ),

        # REFACTOR agents - improve existing code
        AgentCapability(
            role=AgentRole.REFACTOR,
            tier=AgentTier.CLASS,
            strengths=[
                "Improve code structure",
                "Eliminate duplication",
                "Apply design patterns",
                "Enhance maintainability"
            ],
            keywords=[
                "refactor", "cleanup", "simplify", "reorganize",
                "improve", "optimize", "clean up"
            ]
        ),
    ]

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider

    def select_agent_heuristic(self, user_request: str) -> Dict[str, Any]:
        """
        Use heuristics to select agent type and tier

        Fast but less accurate than LLM-powered selection
        """
        request_lower = user_request.lower()

        # Score each agent capability
        scores = []
        for capability in self.AGENT_CATALOG:
            score = 0
            for keyword in capability.keywords:
                if keyword in request_lower:
                    score += 1

            scores.append((capability, score))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        # Get best match
        if scores and scores[0][1] > 0:
            best_capability = scores[0][0]
            confidence = scores[0][1] / len(best_capability.keywords)

            return {
                "role": best_capability.role,
                "tier": best_capability.tier,
                "confidence": confidence,
                "method": "heuristic",
                "reasoning": f"Matched {scores[0][1]} keywords: {best_capability.keywords[:3]}"
            }

        # Default: design agent at system tier
        return {
            "role": AgentRole.DESIGN,
            "tier": AgentTier.SYSTEM,
            "confidence": 0.5,
            "method": "default",
            "reasoning": "No strong signals, defaulting to design/system"
        }

    async def select_agent_llm(self, user_request: str, project_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Use LLM reasoning to select the best agent type and tier

        More accurate but slower than heuristics
        """
        if not self.llm_provider:
            logger.warning("No LLM provider, falling back to heuristics")
            return self.select_agent_heuristic(user_request)

        project_context = project_context or {}

        # Build agent selection prompt
        prompt = f"""You are an expert software engineering coordinator analyzing a user request to determine what type of work is needed.

# User Request
{user_request}

# Project Context
- Subsystems: {project_context.get('subsystems', [])}
- Existing modules: {len(project_context.get('modules', []))} files

# Available Agent Types

1. **DIAGNOSTIC** - Analyze and understand
   - Use when: User wants to understand issues, find bugs, analyze problems
   - Examples: "Why is this slow?", "Debug authentication", "Find memory leak"
   - Tier: Usually SYSTEM or SUBSYSTEM level

2. **DESIGN** - Plan and decompose
   - Use when: User wants to add features, plan architecture
   - Examples: "Add user authentication", "Implement search", "Create API"
   - Tier: SYSTEM level (decomposes to lower tiers)

3. **IMPLEMENTATION** - Write code
   - Use when: Specific, concrete code needs to be written
   - Examples: "Write hash_password function", "Implement JWT encoding"
   - Tier: FUNCTION or CLASS level

4. **TESTING** - Create tests
   - Use when: Test coverage needed
   - Examples: "Write tests for auth", "Add edge case tests"
   - Tier: MODULE or CLASS level

5. **REVIEW** - Quality check
   - Use when: Code needs evaluation
   - Examples: "Review this code", "Check security", "Audit auth system"
   - Tier: MODULE or SYSTEM level

6. **REFACTOR** - Improve existing code
   - Use when: Code needs improvement without behavior change
   - Examples: "Simplify this function", "Remove duplication"
   - Tier: CLASS or MODULE level

# Your Task
Analyze the user's request and determine:
1. What type of work is needed (which agent role)?
2. What scope/tier should it operate at?
3. Why did you choose this?

Respond in JSON:
```json
{{
  "role": "DIAGNOSTIC|DESIGN|IMPLEMENTATION|TESTING|REVIEW|REFACTOR",
  "tier": "SYSTEM|SUBSYSTEM|MODULE|CLASS|FUNCTION",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why you chose this role and tier"
}}
```

Provide ONLY valid JSON."""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing software engineering tasks. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=512,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            # Extract JSON
            from eidolon.planning.improved_decomposition import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result and "role" in result and "tier" in result:
                return {
                    "role": AgentRole(result["role"].lower()),
                    "tier": AgentTier(result["tier"].lower()),
                    "confidence": result.get("confidence", 0.8),
                    "method": "llm",
                    "reasoning": result.get("reasoning", "LLM analysis")
                }

        except Exception as e:
            logger.warning(f"LLM agent selection failed: {e}, using heuristic")

        # Fallback to heuristics
        return self.select_agent_heuristic(user_request)

    async def select_agent(
        self,
        user_request: str,
        project_context: Dict[str, Any] = None,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """
        Main entry point for agent selection

        Args:
            user_request: User's request
            project_context: Information about the project
            use_llm: Whether to use LLM reasoning (slower but more accurate)

        Returns:
            Dictionary with selected agent role, tier, confidence, and reasoning
        """
        if use_llm and self.llm_provider:
            selection = await self.select_agent_llm(user_request, project_context)
        else:
            selection = self.select_agent_heuristic(user_request)

        logger.info(
            "agent_selected",
            role=selection["role"].value if isinstance(selection["role"], AgentRole) else selection["role"],
            tier=selection["tier"].value if isinstance(selection["tier"], AgentTier) else selection["tier"],
            confidence=selection["confidence"],
            method=selection["method"]
        )

        return selection


# Example usage:
"""
selector = IntelligentAgentSelector(llm_provider)

# Heuristic (fast)
result = selector.select_agent_heuristic("Add JWT authentication to API")
# → {role: DESIGN, tier: SYSTEM, confidence: 0.8}

# LLM-powered (accurate)
result = await selector.select_agent("Why is the login endpoint slow?")
# → {role: DIAGNOSTIC, tier: SYSTEM, confidence: 0.95, reasoning: "..."}

# Then use the selected role for prompting:
from eidolon.planning.prompt_templates import PromptTemplateLibrary

prompts = PromptTemplateLibrary.get_system_decomposer_prompt(
    user_request=request,
    project_path=path,
    subsystems=subs,
    role=result["role"]  # Use selected role!
)
"""
