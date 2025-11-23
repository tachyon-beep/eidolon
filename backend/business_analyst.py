"""
Business Analyst Layer - Phase 5

Sits ABOVE/ADJACENT to SystemDecomposer as a requirements analysis layer.

Responsibilities:
1. Analyze raw user requests for clarity and completeness
2. Examine existing codebase to understand impact
3. Identify affected subsystems and components
4. Create structured requirements / change plan
5. Clarify ambiguous requirements
6. Pass refined requirements to SystemDecomposer

This provides an additional layer of indirection for requirements gathering,
similar to how DesignContextTools enable design exploration.

Flow:
  User Request (raw)
    ↓
  Business Analyst (Phase 5)
    - Analyzes request
    - Examines codebase
    - Creates change plan
    ↓
  SystemDecomposer (Tier 1)
    - Uses refined requirements
    - Decomposes to subsystems
    ↓
  ... rest of pipeline
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json

from llm_providers import LLMProvider
from code_graph import CodeGraph
from design_context_tools import DesignContextToolHandler, DESIGN_CONTEXT_TOOLS
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RequirementsAnalysis:
    """Result of business analyst requirements analysis"""

    # Original request
    raw_request: str

    # Refined requirements
    refined_requirements: str
    clear_objectives: List[str]
    success_criteria: List[str]

    # Impact analysis
    affected_subsystems: List[str]
    affected_modules: List[str]
    change_type: str  # "new_feature", "enhancement", "bug_fix", "refactor"
    complexity_estimate: str  # "low", "medium", "high", "very_high"

    # Clarifications
    assumptions: List[str]
    open_questions: List[str]
    risks: List[str]

    # Change plan
    proposed_changes: List[Dict[str, Any]]

    # Metadata
    analysis_turns: int = 0
    tools_used: List[str] = field(default_factory=list)


class BusinessAnalyst:
    """
    Phase 5: Business Analyst Layer

    Analyzes user requests and creates structured requirements/change plans
    BEFORE passing to SystemDecomposer.

    This is the first step in the pipeline, adding requirements refinement.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        code_graph: Optional[CodeGraph] = None,
        design_tool_handler: Optional[DesignContextToolHandler] = None
    ):
        """
        Initialize Business Analyst

        Args:
            llm_provider: LLM provider for analysis
            code_graph: Code graph for understanding existing codebase
            design_tool_handler: Design tools for exploring architecture
        """
        self.llm_provider = llm_provider
        self.code_graph = code_graph
        self.design_tool_handler = design_tool_handler

    async def analyze_request(
        self,
        user_request: str,
        project_path: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RequirementsAnalysis:
        """
        Analyze user request and create structured requirements

        Args:
            user_request: Raw user request
            project_path: Path to project
            context: Additional context

        Returns:
            RequirementsAnalysis with refined requirements and change plan
        """
        context = context or {}

        logger.info("business_analysis_starting", request=user_request[:100])

        # Build system prompt for business analyst role
        system_prompt = """You are a Business Analyst for software development.

Your role is to:
1. Analyze user requests for clarity and completeness
2. Examine the existing codebase to understand impact
3. Identify affected subsystems and components
4. Create a structured requirements document / change plan
5. Clarify ambiguous requirements
6. Identify risks and assumptions

You have access to design exploration tools to understand the codebase.

Your output should be a structured JSON with:
- refined_requirements: Clear, detailed requirements
- clear_objectives: List of specific objectives
- success_criteria: How to know when this is done
- affected_subsystems: Which subsystems will be impacted
- affected_modules: Which modules will be impacted
- change_type: "new_feature", "enhancement", "bug_fix", or "refactor"
- complexity_estimate: "low", "medium", "high", or "very_high"
- assumptions: List of assumptions you're making
- open_questions: Questions that need clarification
- risks: Potential risks or concerns
- proposed_changes: List of proposed changes to make

Explore the codebase using available tools before finalizing your analysis."""

        # Build user prompt
        user_prompt = f"""Analyze the following user request and create a structured requirements document / change plan:

**User Request:**
{user_request}

**Project Path:**
{project_path}

Please:
1. Understand what the user is asking for
2. Explore the existing codebase to understand impact
3. Identify affected components
4. Create a clear, structured change plan
5. Clarify any ambiguities
6. Identify risks and assumptions

Use the available tools to explore the codebase before finalizing your analysis."""

        # Add tool guidance if available
        if self.design_tool_handler:
            user_prompt += f"\n\n**Tools Available:**\n"
            user_prompt += f"- get_existing_modules: See what exists\n"
            user_prompt += f"- get_subsystem_architecture: Understand structure\n"
            user_prompt += f"- search_similar_modules: Find related code\n"
            user_prompt += f"- request_requirement_clarification: Ask questions\n"

        # Multi-turn analysis conversation
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        max_turns = 8  # More turns for thorough requirements analysis
        turn = 0
        analysis_result = None
        tools_used = []

        # Check if design tools are available
        use_tools = self.design_tool_handler is not None

        while turn < max_turns:
            turn += 1

            try:
                call_params = {
                    "messages": messages,
                    "max_tokens": 3072,
                    "temperature": 0.0
                }

                if use_tools:
                    call_params["tools"] = DESIGN_CONTEXT_TOOLS
                    call_params["tool_choice"] = "auto"
                else:
                    call_params["response_format"] = {"type": "json_object"}

                response = await self.llm_provider.create_completion(**call_params)

            except (TypeError, Exception) as e:
                logger.warning(f"Advanced features not supported: {e}, using regular mode")
                response = await self.llm_provider.create_completion(
                    messages=messages,
                    max_tokens=3072,
                    temperature=0.0
                )

            # Check if LLM made tool calls
            tool_calls = getattr(response, 'tool_calls', None)

            if tool_calls and use_tools:
                logger.info(
                    "ba_tool_calls_requested",
                    request=user_request[:50],
                    count=len(tool_calls),
                    turn=turn
                )

                messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": tool_calls
                })

                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    tools_used.append(tool_name)

                    logger.info(
                        "ba_executing_tool_call",
                        tool=tool_name,
                        args=tool_args
                    )

                    tool_result = self.design_tool_handler.handle_tool_call(
                        tool_name=tool_name,
                        arguments=tool_args
                    )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })

                continue

            # No tool calls - process as final analysis
            from utils.json_utils import extract_json_from_response
            analysis_result = extract_json_from_response(response.content)

            if analysis_result and "refined_requirements" in analysis_result:
                break
            elif response.content and not tool_calls:
                logger.warning(f"No valid analysis on turn {turn}, continuing...")
                continue
            else:
                logger.warning(f"Empty response on turn {turn}, continuing...")
                continue

        # Build RequirementsAnalysis from result
        if not analysis_result:
            logger.warning("Business analysis failed, using fallback")
            analysis_result = {
                "refined_requirements": user_request,
                "clear_objectives": ["Implement user request"],
                "success_criteria": ["Request is implemented"],
                "affected_subsystems": [],
                "affected_modules": [],
                "change_type": "enhancement",
                "complexity_estimate": "medium",
                "assumptions": ["No assumptions"],
                "open_questions": [],
                "risks": [],
                "proposed_changes": []
            }

        requirements = RequirementsAnalysis(
            raw_request=user_request,
            refined_requirements=analysis_result.get("refined_requirements", user_request),
            clear_objectives=analysis_result.get("clear_objectives", []),
            success_criteria=analysis_result.get("success_criteria", []),
            affected_subsystems=analysis_result.get("affected_subsystems", []),
            affected_modules=analysis_result.get("affected_modules", []),
            change_type=analysis_result.get("change_type", "enhancement"),
            complexity_estimate=analysis_result.get("complexity_estimate", "medium"),
            assumptions=analysis_result.get("assumptions", []),
            open_questions=analysis_result.get("open_questions", []),
            risks=analysis_result.get("risks", []),
            proposed_changes=analysis_result.get("proposed_changes", []),
            analysis_turns=turn,
            tools_used=tools_used
        )

        logger.info(
            "business_analysis_complete",
            request=user_request[:50],
            change_type=requirements.change_type,
            complexity=requirements.complexity_estimate,
            affected_subsystems=len(requirements.affected_subsystems),
            turns=turn,
            tools_used=len(set(tools_used))
        )

        return requirements
