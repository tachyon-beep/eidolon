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

from eidolon.llm_providers import LLMProvider
from eidolon.code_graph import CodeGraph
from eidolon.design_context_tools import DesignContextToolHandler, DESIGN_CONTEXT_TOOLS
from eidolon.specialist_agents import SpecialistRegistry, SpecialistDomain
from eidolon.utils.json_utils import extract_json_from_response
from eidolon.logging_config import get_logger

logger = get_logger(__name__)


# User interaction tools for Business Analyst
USER_INTERACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ask_user_question",
            "description": "Ask the user a clarifying question about their requirements. Use this when requirements are ambiguous or you need more details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The clarifying question to ask the user"
                    },
                    "context": {
                        "type": "string",
                        "description": "Why you're asking this question (what you're trying to understand)"
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: Suggested answers/options for the user"
                    }
                },
                "required": ["question", "context"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_understanding",
            "description": "Confirm your understanding of the requirements with the user before proceeding. Present a summary and ask for confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Summary of your understanding of the requirements"
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key points to confirm with the user"
                    }
                },
                "required": ["summary", "key_points"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "initiate_build",
            "description": "FIRE! Start the build process. Only call this when you have complete, clear requirements and the user has confirmed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "requirements_complete": {
                        "type": "boolean",
                        "description": "Confirm that requirements are complete and clear"
                    },
                    "confidence_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Your confidence level in the requirements"
                    },
                    "ready_to_build": {
                        "type": "boolean",
                        "description": "Confirm you're ready to initiate the build"
                    }
                },
                "required": ["requirements_complete", "confidence_level", "ready_to_build"]
            }
        }
    }
]


# Specialist consultation tools for Business Analyst
# These allow the BA to delegate to domain-specific expert agents
SPECIALIST_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "consult_security_engineer",
            "description": "Consult the Security Engineer specialist for security analysis, vulnerability assessment, OWASP Top 10, authentication/authorization design, and security best practices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The security question or task to delegate to the security specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_test_engineer",
            "description": "Consult the Test Engineer specialist for testing strategy, test pyramid design, pytest generation, mocking, fixtures, and test coverage analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The testing question or task to delegate to the test specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_deployment_specialist",
            "description": "Consult the Deployment Specialist for Docker, Kubernetes, Terraform, CI/CD pipelines, cloud deployment, and infrastructure as code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The deployment question or task to delegate to the deployment specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_frontend_specialist",
            "description": "Consult the Frontend Specialist for React/Vue components, state management, hooks, responsive design, and frontend architecture.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The frontend question or task to delegate to the frontend specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_database_specialist",
            "description": "Consult the Database Specialist for schema design, query optimization, indexing strategies, migrations, ORMs, and database best practices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The database question or task to delegate to the database specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_api_specialist",
            "description": "Consult the API Specialist for RESTful/GraphQL API design, endpoint design, error handling (RFC 7807), versioning, and API best practices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The API design question or task to delegate to the API specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_data_specialist",
            "description": "Consult the Data Specialist for ETL pipelines, data processing, data validation, pandas/polars, and data engineering tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The data engineering question or task to delegate to the data specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_integration_specialist",
            "description": "Consult the Integration Specialist for third-party API integration, webhooks, OAuth, API clients, and integration patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The integration question or task to delegate to the integration specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_diagnostic_specialist",
            "description": "Consult the Diagnostic Specialist for debugging, profiling, tracing, error analysis, and troubleshooting production issues.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The debugging or diagnostic question to delegate to the diagnostic specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_performance_specialist",
            "description": "Consult the Performance Specialist for Big-O analysis, algorithmic optimization, caching strategies, and performance tuning.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The performance optimization question or task to delegate to the performance specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_pytorch_engineer",
            "description": "Consult the PyTorch Engineer specialist for ML model design, neural network architecture, training loops, and PyTorch best practices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The ML/PyTorch question or task to delegate to the PyTorch specialist"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consult_ux_specialist",
            "description": "Consult the UX Specialist for user experience design, WCAG accessibility, user flows, interaction patterns, and usability analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The UX design question or task to delegate to the UX specialist"
                    }
                },
                "required": ["query"]
            }
        }
    }
]


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
        design_tool_handler: Optional[DesignContextToolHandler] = None,
        specialist_registry: Optional[SpecialistRegistry] = None
    ):
        """
        Initialize Business Analyst

        Args:
            llm_provider: LLM provider for analysis
            code_graph: Code graph for understanding existing codebase
            design_tool_handler: Design tools for exploring architecture
            specialist_registry: Registry of specialist agents for delegation
        """
        self.llm_provider = llm_provider
        self.code_graph = code_graph
        self.design_tool_handler = design_tool_handler
        self.specialist_registry = specialist_registry

        # Map tool names to specialist domains
        self.specialist_tool_map = {
            "consult_security_engineer": SpecialistDomain.SECURITY,
            "consult_test_engineer": SpecialistDomain.TESTING,
            "consult_deployment_specialist": SpecialistDomain.DEPLOYMENT,
            "consult_frontend_specialist": SpecialistDomain.FRONTEND,
            "consult_database_specialist": SpecialistDomain.DATABASE,
            "consult_api_specialist": SpecialistDomain.API_DESIGN,
            "consult_data_specialist": SpecialistDomain.DATA_ENGINEERING,
            "consult_integration_specialist": SpecialistDomain.INTEGRATION,
            "consult_diagnostic_specialist": SpecialistDomain.DIAGNOSTICS,
            "consult_performance_specialist": SpecialistDomain.PERFORMANCE,
            "consult_pytorch_engineer": SpecialistDomain.MACHINE_LEARNING,
            "consult_ux_specialist": SpecialistDomain.UX_DESIGN
        }

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
                    "temperature": 0.0,
                    "response_format": {"type": "json_object"},
                }

                if use_tools:
                    call_params["tools"] = DESIGN_CONTEXT_TOOLS
                    call_params["tool_choice"] = "auto"
                # Note: Claude follows JSON prompts well without response_format

                response = await self.llm_provider.create_completion(**call_params)

            except (TypeError, Exception) as e:
                logger.warning(f"Advanced features not supported: {e}, using regular mode")
                response = await self.llm_provider.create_completion(
                    messages=messages,
                    max_tokens=3072,
                    temperature=0.0,
                    response_format={"type": "json_object"},
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

    async def interactive_analyze(
        self,
        initial_request: str,
        project_path: str,
        user_callback,
        context: Optional[Dict[str, Any]] = None
    ) -> RequirementsAnalysis:
        """
        Interactive requirements analysis with user conversation

        The Business Analyst asks clarifying questions until confident,
        then "fires" by calling initiate_build.

        Args:
            initial_request: Initial user request
            project_path: Path to project
            user_callback: Async function(question, options) -> user response
            context: Additional context

        Returns:
            RequirementsAnalysis when analyst is ready to build
        """
        context = context or {}

        logger.info("interactive_analysis_starting", request=initial_request[:100])

        # Enhanced system prompt for interactive mode
        system_prompt = """You are a Senior Business Analyst conducting requirements gathering for a software project.

Your mission is to fully understand the user's requirements through interactive conversation before initiating development.

WORKFLOW:
1. **Initial Analysis**
   - Analyze the user's request
   - Identify what's clear vs ambiguous
   - Explore existing codebase (use design tools)
   - Form initial understanding

2. **Clarification Phase** (use ask_user_question)
   - Ask clarifying questions about ambiguous aspects
   - Probe for edge cases and constraints
   - Understand user's goals and success criteria
   - Ask about non-functional requirements (performance, security, etc.)
   - Confirm technical approach preferences

3. **Confirmation Phase** (use confirm_understanding)
   - Present comprehensive summary of requirements
   - List key points and assumptions
   - Give user chance to correct or add details

4. **FIRE!** (use initiate_build)
   - Only when requirements are complete and clear
   - Only when user has confirmed understanding
   - Only when confidence_level is "high"
   - This starts the actual build process

QUESTION STRATEGIES:
✓ **Good Questions:**
  - "What should happen when...?" (edge cases)
  - "Should the system...?" (specific behavior)
  - "What are the performance requirements?" (non-functional)
  - "Who will use this feature?" (user personas)
  - "What does success look like?" (acceptance criteria)

✗ **Avoid:**
  - Yes/no questions without context
  - Too many questions at once (max 2-3)
  - Technical jargon without explaining
  - Questions answered by codebase exploration

CONFIDENCE LEVELS:
- **low**: Major ambiguities, many unknowns → Keep asking questions
- **medium**: Some clarity, minor gaps → Ask targeted questions
- **high**: Clear requirements, confirmed with user → Ready to initiate_build

TOOLS AVAILABLE:
1. Design context tools (explore codebase)
2. Specialist consultation tools (delegate to domain experts)
3. ask_user_question (clarifying questions)
4. confirm_understanding (summarize and confirm)
5. initiate_build (FIRE! Start the build)

DELEGATION STRATEGY:
- Use specialist tools to delegate complex domain-specific questions
- Security concerns → consult_security_engineer
- Testing strategy → consult_test_engineer
- Database design → consult_database_specialist
- API design → consult_api_specialist
- etc.

CRITICAL: Only call initiate_build when:
- Requirements are complete and clear
- User has confirmed your understanding
- You have high confidence
- All major questions answered"""

        # Build user prompt
        user_prompt = f"""The user wants to build something. Here's their initial request:

**User Request:**
{initial_request}

**Project Path:**
{project_path}

Your task:
1. Analyze this request
2. Explore the codebase to understand impact
3. Ask clarifying questions to fill gaps
4. Confirm your understanding with the user
5. When confident and user confirms, call initiate_build to start development

Start by analyzing the request and either:
- Using design tools to explore the codebase
- Asking clarifying questions if requirements are unclear

Be thorough but efficient. Ask good questions."""

        # Add tool definitions
        all_tools = list(USER_INTERACTION_TOOLS)
        if self.design_tool_handler:
            all_tools.extend(DESIGN_CONTEXT_TOOLS)
        if self.specialist_registry:
            all_tools.extend(SPECIALIST_TOOLS)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        max_turns = 20  # Allow many turns for thorough requirements gathering
        turn = 0
        tools_used = []
        build_initiated = False
        analysis_result = None

        while turn < max_turns and not build_initiated:
            turn += 1

            try:
                response = await self.llm_provider.create_completion(
                    messages=messages,
                    max_tokens=3072,
                    temperature=0.2,
                    tools=all_tools,
                    response_format={"type": "json_object"},
                )

                assistant_message = {
                    "role": "assistant",
                    "content": response.content or ""
                }

                # Check for tool calls
                tool_calls = getattr(response, 'tool_calls', None)

                if tool_calls:
                    assistant_message["tool_calls"] = tool_calls
                    messages.append(assistant_message)

                    for tool_call in tool_calls:
                        tool_name = tool_call.function.name
                        tools_used.append(tool_name)

                        logger.info("ba_tool_call", turn=turn, tool=tool_name)

                        # Parse arguments
                        try:
                            args_str = tool_call.function.arguments
                            if args_str is None or args_str == "":
                                args = {}
                            else:
                                args = json.loads(args_str)
                        except (json.JSONDecodeError, TypeError, AttributeError):
                            args = {}

                        # Handle user interaction tools
                        if tool_name == "ask_user_question":
                            # Ask user via callback
                            question = args.get("question", "")
                            question_context = args.get("context", "")
                            options = args.get("options", [])

                            logger.info("asking_user", question=question[:100])

                            # Call user callback
                            user_response = await user_callback(
                                question=question,
                                context=question_context,
                                options=options
                            )

                            tool_result = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps({
                                    "user_response": user_response,
                                    "status": "answered"
                                })
                            }
                            messages.append(tool_result)

                        elif tool_name == "confirm_understanding":
                            # Confirm understanding with user
                            summary = args.get("summary", "")
                            key_points = args.get("key_points", [])

                            logger.info("confirming_understanding")

                            # Present confirmation to user
                            confirmation_question = f"""Please confirm my understanding:

{summary}

Key points:
{chr(10).join(f'  - {point}' for point in key_points)}

Is this correct? (yes/no/corrections)"""

                            user_response = await user_callback(
                                question=confirmation_question,
                                context="Confirming requirements before build",
                                options=["yes", "no", "add corrections"]
                            )

                            tool_result = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps({
                                    "user_response": user_response,
                                    "confirmed": user_response.lower().startswith("y")
                                })
                            }
                            messages.append(tool_result)

                        elif tool_name == "initiate_build":
                            # Build initiated!
                            requirements_complete = args.get("requirements_complete", False)
                            confidence_level = args.get("confidence_level", "low")
                            ready_to_build = args.get("ready_to_build", False)

                            logger.info(
                                "build_initiated",
                                complete=requirements_complete,
                                confidence=confidence_level,
                                ready=ready_to_build
                            )

                            if requirements_complete and ready_to_build and confidence_level == "high":
                                build_initiated = True

                                tool_result = {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps({
                                        "status": "build_starting",
                                        "message": "Requirements confirmed. Starting build process..."
                                    })
                                }
                                messages.append(tool_result)
                            else:
                                tool_result = {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps({
                                        "status": "not_ready",
                                        "message": "Requirements not complete or confidence too low. Continue gathering requirements."
                                    })
                                }
                                messages.append(tool_result)

                        # Handle design context tools
                        elif self.design_tool_handler and tool_name in [t["function"]["name"] for t in DESIGN_CONTEXT_TOOLS]:
                            tool_result_data = self.design_tool_handler.handle_tool_call(
                                tool_name=tool_name,
                                arguments=args
                            )

                            tool_result = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps(tool_result_data)
                            }
                            messages.append(tool_result)

                        # Handle specialist consultation tools
                        elif self.specialist_registry and tool_name in self.specialist_tool_map:
                            specialist_domain = self.specialist_tool_map[tool_name]
                            specialist = self.specialist_registry.get_specialist(specialist_domain)

                            logger.info(
                                "ba_consulting_specialist",
                                tool=tool_name,
                                domain=specialist_domain.value,
                                query=args.get("query", "")[:100]
                            )

                            if specialist:
                                try:
                                    # Delegate to specialist analyze method
                                    report = await specialist.analyze(
                                        code=args.get("query", ""),  # Use query as code input
                                        context={"project_path": project_path}
                                    )

                                    # Extract recommendations or summary from report
                                    if isinstance(report, dict):
                                        specialist_response = json.dumps(report)
                                    else:
                                        # SpecialistReport object - extract summary
                                        specialist_response = f"Domain: {report.domain}\nSummary: {report.summary}\nRecommendations: {len(report.recommendations)}"

                                    tool_result = {
                                        "role": "tool",
                                        "tool_call_id": tool_call.id,
                                        "content": json.dumps({
                                            "specialist": specialist_domain.value,
                                            "response": specialist_response,
                                            "status": "success"
                                        })
                                    }
                                    messages.append(tool_result)

                                    logger.info(
                                        "ba_specialist_consulted",
                                        domain=specialist_domain.value,
                                        response_length=len(specialist_response)
                                    )

                                except Exception as e:
                                    logger.error(
                                        "ba_specialist_error",
                                        domain=specialist_domain.value,
                                        error=str(e)
                                    )
                                    tool_result = {
                                        "role": "tool",
                                        "tool_call_id": tool_call.id,
                                        "content": json.dumps({
                                            "error": f"Specialist consultation failed: {str(e)}"
                                        })
                                    }
                                    messages.append(tool_result)
                            else:
                                tool_result = {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps({
                                        "error": f"Specialist {specialist_domain.value} not available"
                                    })
                                }
                                messages.append(tool_result)

                        else:
                            # Unknown tool
                            tool_result = {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps({"error": f"Unknown tool: {tool_name}"})
                            }
                            messages.append(tool_result)

                    # Continue loop to process tool results
                    continue

                else:
                    # No tool calls, just assistant response
                    messages.append(assistant_message)

                    # Try to extract final analysis from response
                    if response.content:
                        try:
                            extracted = extract_json_from_response(response.content)
                            if extracted and "refined_requirements" in extracted:
                                analysis_result = extracted
                                break
                        except Exception:
                            pass

            except Exception as e:
                logger.error("interactive_analysis_error", turn=turn, error=str(e))
                break

        # Build RequirementsAnalysis from final state
        if not analysis_result:
            # Extract from messages or use fallback
            logger.warning("No structured analysis result, creating from conversation")
            analysis_result = {
                "refined_requirements": initial_request,
                "clear_objectives": ["Implement user request"],
                "success_criteria": ["Request is implemented"],
                "affected_subsystems": [],
                "affected_modules": [],
                "change_type": "enhancement",
                "complexity_estimate": "medium",
                "assumptions": ["Interactive analysis completed"],
                "open_questions": [],
                "risks": [],
                "proposed_changes": []
            }

        requirements = RequirementsAnalysis(
            raw_request=initial_request,
            refined_requirements=analysis_result.get("refined_requirements", initial_request),
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
            "interactive_analysis_complete",
            build_initiated=build_initiated,
            turns=turn,
            tools_used=len(set(tools_used))
        )

        return requirements
