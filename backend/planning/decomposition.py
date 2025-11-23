"""
Task decomposition strategies for each agent tier

Each decomposer uses AI to break down a high-level task into
concrete subtasks for the next tier down.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid

from models import Task, TaskType, TaskStatus, TaskPriority
from llm_providers import LLMProvider
from logging_config import get_logger

# Phase 2.5 improvements: structured outputs and role-based prompting
from planning.agent_selector import IntelligentAgentSelector, AgentRole
from planning.prompt_templates import PromptTemplateLibrary
from planning.improved_decomposition import extract_json_from_response

logger = get_logger(__name__)


class SystemDecomposer:
    """
    Decomposes user requests into subsystem-level tasks

    User: "Add user authentication with JWT"
    → api subsystem: Add /login and /logout endpoints
    → services subsystem: Implement JWT authentication service
    → models subsystem: Add User model with password hashing
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        use_intelligent_selection: bool = True,
        use_review_loop: bool = True,
        review_min_score: float = 75.0,
        review_max_iterations: int = 2,
        design_tool_handler: Optional[Any] = None
    ):
        """
        Initialize SystemDecomposer with Phase 2.5, Phase 3, and Phase 4C improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
            use_review_loop: Whether to use review-and-revise loops (Phase 3, default: True)
            review_min_score: Minimum acceptable quality score for review (0-100, default: 75.0)
            review_max_iterations: Maximum revision attempts (default: 2)
            design_tool_handler: Optional DesignContextToolHandler for interactive design (Phase 4C)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection
        self.use_review_loop = use_review_loop
        self.review_min_score = review_min_score
        self.review_max_iterations = review_max_iterations

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

        # Phase 3: Review loop
        if use_review_loop:
            from planning.review_loop import ReviewLoop
            self.review_loop = ReviewLoop(llm_provider)
        else:
            self.review_loop = None

        # Phase 4C: Interactive design with tool calling
        self.design_tool_handler = design_tool_handler

    async def decompose(
        self,
        user_request: str,
        project_path: str,
        subsystems: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose user request into subsystem tasks using Phase 2.5 and Phase 3 improvements

        Args:
            user_request: High-level feature request from user
            project_path: Path to project
            subsystems: List of subsystems (directories) in project
            context: Additional context

        Returns:
            List of subsystem-level tasks with dependencies
        """
        context = context or {}

        # Generate initial decomposition plan
        initial_plan = await self._decompose_internal(
            user_request, project_path, subsystems, context
        )

        # Phase 3: Review and revise if enabled
        if self.review_loop and not context.get("skip_review", False):
            # Define revision function for review loop
            async def revise_func(
                is_revision: bool = True,
                revision_feedback: str = None,
                previous_output: Dict[str, Any] = None,
                **kwargs
            ) -> Dict[str, Any]:
                """Revise the decomposition based on review feedback"""
                revision_context = {
                    **context,
                    "is_revision": is_revision,
                    "revision_feedback": revision_feedback,
                    "previous_output": previous_output
                }
                return await self._decompose_internal(
                    user_request, project_path, subsystems, revision_context
                )

            # Run review-and-revise loop
            final_plan = await self.review_loop.review_and_revise(
                initial_output=initial_plan,
                primary_agent_func=revise_func,
                review_context={
                    "tier": "system",
                    "type": "system_decomposition",
                    "original_request": user_request,
                    "project_path": project_path,
                    "subsystems": subsystems
                },
                min_score=self.review_min_score,
                max_iterations=self.review_max_iterations
            )
        else:
            final_plan = initial_plan

        # Convert plan to Task objects
        return self._plan_to_tasks(final_plan, user_request, project_path, context)

    async def _decompose_internal(
        self,
        user_request: str,
        project_path: str,
        subsystems: List[str],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Internal method: Generate decomposition plan (supports revisions)

        Args:
            user_request: High-level feature request
            project_path: Path to project
            subsystems: List of subsystems
            context: Additional context (including revision feedback if this is a revision)

        Returns:
            Decomposition plan dict with subsystem_tasks
        """
        context = context or {}
        is_revision = context.get("is_revision", False)
        revision_feedback = context.get("revision_feedback", None)

        # Phase 2.5 Step 1: Intelligent agent role selection
        agent_role = AgentRole.DESIGN  # Default role
        if self.agent_selector and not is_revision:  # Only select role once, not on revisions
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=user_request,
                    project_context={
                        "subsystems": subsystems,
                        "project_path": project_path
                    },
                    use_llm=True  # Use LLM-powered selection for better accuracy
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    reasoning=selection.get("reasoning", "")
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default DESIGN role")
                agent_role = AgentRole.DESIGN

        # Phase 2.5 Step 2: Get role-based prompts
        prompts = PromptTemplateLibrary.get_system_decomposer_prompt(
            user_request=user_request,
            project_path=project_path,
            subsystems=subsystems,
            role=agent_role
        )

        # Phase 3: Add revision feedback to prompt if this is a revision
        if is_revision and revision_feedback:
            prompts["user"] += f"\n\n---\n**REVISION REQUEST**\n\nYour previous decomposition received the following review feedback. Please revise to address these issues:\n\n{revision_feedback}\n\nProvide an improved decomposition that addresses all the feedback."

        # Phase 4C: Add design exploration guidance if tools available
        if self.design_tool_handler and not is_revision:
            prompts["user"] += f"\n\n**Interactive Design Tools Available:**\n"
            prompts["user"] += f"Explore before finalizing system architecture:\n"
            prompts["user"] += f"- get_existing_modules: See all existing modules\n"
            prompts["user"] += f"- get_subsystem_architecture: Understand subsystem structures\n"
            prompts["user"] += f"- search_similar_modules: Find related functionality\n"
            prompts["user"] += f"- propose_design_option: Propose and get feedback on architecture\n"
            prompts["user"] += f"- request_requirement_clarification: Ask about unclear requirements\n"
            prompts["user"] += f"- validate_design_decision: Check system-level design choices\n"

        # Phase 2.5 Step 3 + Phase 4C: Call LLM with tool calling support
        messages = [
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["user"]}
        ]

        # Phase 4C: Multi-turn design conversation
        max_turns = 6
        turn = 0
        plan = None

        # Check if design tools are available
        use_design_tools = self.design_tool_handler is not None and not is_revision

        while turn < max_turns:
            turn += 1

            try:
                call_params = {
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": 0.0
                }

                if use_design_tools:
                    from design_context_tools import DESIGN_CONTEXT_TOOLS
                    call_params["tools"] = DESIGN_CONTEXT_TOOLS
                    call_params["tool_choice"] = "auto"
                else:
                    call_params["response_format"] = {"type": "json_object"}

                response = await self.llm_provider.create_completion(**call_params)

            except (TypeError, Exception) as e:
                logger.warning(f"Advanced features not supported: {e}, using regular mode")
                response = await self.llm_provider.create_completion(
                    messages=messages,
                    max_tokens=4096,
                    temperature=0.0
                )

            # Phase 4C: Check if LLM made design tool calls
            tool_calls = getattr(response, 'tool_calls', None)

            if tool_calls and use_design_tools:
                logger.info(
                    "design_tool_calls_requested",
                    user_request=user_request[:50],
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

                    logger.info(
                        "executing_design_tool_call",
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

            # No tool calls - process as final plan response
            plan = extract_json_from_response(response.content)

            if plan and "subsystem_tasks" in plan:
                break
            elif response.content and not tool_calls:
                logger.warning(f"No valid plan on turn {turn}, continuing...")
                continue
            else:
                logger.warning(f"Empty response on turn {turn}, continuing...")
                continue

        if not plan or "subsystem_tasks" not in plan:
            # Fallback: create a simple task structure
            logger.warning("Failed to parse LLM response, using fallback")
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

        return plan

    def _plan_to_tasks(
        self,
        plan: Dict[str, Any],
        user_request: str,
        project_path: str,
        context: Dict[str, Any]
    ) -> List[Task]:
        """
        Convert decomposition plan to Task objects

        Args:
            plan: Decomposition plan dict with subsystem_tasks
            user_request: Original user request
            project_path: Path to project
            context: Additional context

        Returns:
            List of Task objects with resolved dependencies
        """
        # Create Task objects
        tasks = []
        for i, subtask_def in enumerate(plan.get("subsystem_tasks", [])):
            task = Task(
                id=f"T-SYS-{uuid.uuid4().hex[:8]}",
                parent_task_id=None,  # Root task
                type=TaskType(subtask_def.get("type", "modify_existing")),
                scope="SUBSYSTEM",
                target=subtask_def.get("subsystem", "unknown"),
                instruction=subtask_def.get("instruction", ""),
                context={
                    "user_request": user_request,
                    "project_path": project_path,
                    **context
                },
                dependencies=[],  # Will be populated based on dependency names
                priority=self._parse_priority(subtask_def.get("priority", "medium")),
                estimated_complexity=subtask_def.get("complexity", "medium")
            )
            tasks.append(task)

        # Resolve dependencies (convert names to task IDs)
        task_by_subsystem = {t.target: t for t in tasks}
        for i, subtask_def in enumerate(plan.get("subsystem_tasks", [])):
            for dep_name in subtask_def.get("dependencies", []):
                if dep_name in task_by_subsystem:
                    tasks[i].dependencies.append(task_by_subsystem[dep_name].id)

        logger.info(
            "system_decomposition_complete",
            tasks=len(tasks),
            understanding=plan.get("understanding", "")
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


class SubsystemDecomposer:
    """
    Decomposes subsystem tasks into module tasks

    Subsystem: "Implement JWT authentication service"
    → auth_service.py: Create AuthService class
    → token_service.py: Create TokenService for JWT generation

    Phase 3: Includes review-and-revise loop for subsystem design quality
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        use_intelligent_selection: bool = True,
        use_review_loop: bool = True,
        review_min_score: float = 75.0,
        review_max_iterations: int = 2,
        design_tool_handler: Optional[Any] = None
    ):
        """
        Initialize SubsystemDecomposer with Phase 2.5, Phase 3, and Phase 4C improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
            use_review_loop: Whether to use review-and-revise loop (default: True)
            review_min_score: Minimum quality score for acceptance (default: 75.0)
            review_max_iterations: Maximum revision iterations (default: 2)
            design_tool_handler: Optional DesignContextToolHandler for interactive design (Phase 4C)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection
        self.use_review_loop = use_review_loop
        self.review_min_score = review_min_score
        self.review_max_iterations = review_max_iterations

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

        # Phase 3: Review loop for quality improvement
        from planning.review_loop import ReviewLoop
        self.review_loop = ReviewLoop(llm_provider) if use_review_loop else None

        # Phase 4C: Interactive design with tool calling
        self.design_tool_handler = design_tool_handler

    async def decompose(
        self,
        task: Task,
        existing_modules: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose subsystem task into module tasks using Phase 2.5 and Phase 3 improvements

        Args:
            task: Subsystem-level task
            existing_modules: List of existing module files in subsystem
            context: Additional context

        Returns:
            List of module-level tasks
        """
        context = context or {}

        # Generate initial decomposition plan
        initial_plan = await self._decompose_internal(task, existing_modules, context)

        # Phase 3: Review and revise if enabled
        if self.review_loop and not context.get("skip_review", False):
            logger.info("starting_review_loop", subsystem=task.target)

            # Wrapper function for revision calls
            async def revise_func(
                task=task,
                existing_modules=existing_modules,
                context=None,
                revision_feedback=None,
                previous_output=None,
                is_revision=False,
                **kwargs
            ):
                """Wrapper to call _decompose_internal with revision context"""
                revision_context = {
                    **(context or {}),
                    "is_revision": is_revision,
                    "revision_feedback": revision_feedback,
                    "previous_output": previous_output
                }
                return await self._decompose_internal(task, existing_modules, revision_context)

            # Review and potentially revise
            try:
                final_plan = await self.review_loop.review_and_revise(
                    initial_output=initial_plan,
                    primary_agent_func=revise_func,
                    review_context={
                        "tier": "subsystem",
                        "type": "subsystem_decomposition",
                        "original_request": task.instruction,
                        "subsystem": task.target
                    },
                    min_score=self.review_min_score,
                    max_iterations=self.review_max_iterations
                )
            except Exception as e:
                logger.error("review_loop_failed", error=str(e))
                # Use initial plan if review fails
                final_plan = initial_plan
        else:
            # No review loop, use initial plan
            final_plan = initial_plan

        # Convert final plan to Task objects
        return self._plan_to_tasks(final_plan, task, context)

    async def _decompose_internal(
        self,
        task: Task,
        existing_modules: List[str],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Internal method to generate decomposition plan (called by both initial and revisions)

        Args:
            task: Subsystem-level task
            existing_modules: Existing modules in subsystem
            context: Context including revision feedback if this is a revision

        Returns:
            Dict with decomposition plan (module_tasks)
        """
        context = context or {}
        is_revision = context.get("is_revision", False)
        revision_feedback = context.get("revision_feedback", None)

        # Phase 2.5 Step 1: Intelligent agent role selection
        agent_role = AgentRole.DESIGN  # Default role
        if self.agent_selector and not is_revision:
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=task.instruction,
                    project_context={
                        "subsystem": task.target,
                        "existing_modules": existing_modules
                    },
                    use_llm=True
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    subsystem=task.target
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default DESIGN role")
                agent_role = AgentRole.DESIGN

        # Phase 2.5 Step 2: Get role-based prompts
        prompts = PromptTemplateLibrary.get_subsystem_decomposer_prompt(
            subsystem_task=task.instruction,
            target_subsystem=task.target,
            existing_modules=existing_modules,
            role=agent_role
        )

        # Phase 3: Add revision feedback to prompt if this is a revision
        if is_revision and revision_feedback:
            prompts["user"] += f"\n\n---\n**REVISION REQUEST**\n\nYour previous decomposition received the following review feedback. Please revise to address these issues:\n\n{revision_feedback}\n\nProvide an improved decomposition that addresses all the feedback."

        # Phase 4C: Add design exploration guidance if tools available
        if self.design_tool_handler and not is_revision:
            prompts["user"] += f"\n\n**Interactive Design Tools Available:**\n"
            prompts["user"] += f"Explore before finalizing subsystem design:\n"
            prompts["user"] += f"- get_existing_modules: See existing modules in this subsystem\n"
            prompts["user"] += f"- get_subsystem_architecture: Understand subsystem structure\n"
            prompts["user"] += f"- search_similar_modules: Find similar subsystems/patterns\n"
            prompts["user"] += f"- propose_design_option: Propose and get feedback\n"
            prompts["user"] += f"- validate_design_decision: Check design choices\n"

        # Phase 2.5 Step 3 + Phase 4C: Call LLM with tool calling support
        messages = [
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["user"]}
        ]

        # Phase 4C: Multi-turn design conversation
        max_turns = 6
        turn = 0
        plan = None

        # Check if design tools are available
        use_design_tools = self.design_tool_handler is not None and not is_revision

        while turn < max_turns:
            turn += 1

            try:
                call_params = {
                    "messages": messages,
                    "max_tokens": 2048,
                    "temperature": 0.0
                }

                if use_design_tools:
                    from design_context_tools import DESIGN_CONTEXT_TOOLS
                    call_params["tools"] = DESIGN_CONTEXT_TOOLS
                    call_params["tool_choice"] = "auto"
                else:
                    call_params["response_format"] = {"type": "json_object"}

                response = await self.llm_provider.create_completion(**call_params)

            except (TypeError, Exception) as e:
                logger.warning(f"Advanced features not supported: {e}, using regular mode")
                response = await self.llm_provider.create_completion(
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.0
                )

            # Phase 4C: Check if LLM made design tool calls
            tool_calls = getattr(response, 'tool_calls', None)

            if tool_calls and use_design_tools:
                logger.info(
                    "design_tool_calls_requested",
                    subsystem=task.target,
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

                    logger.info(
                        "executing_design_tool_call",
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

            # No tool calls - process as final plan response
            plan = extract_json_from_response(response.content)

            if plan and "module_tasks" in plan:
                break
            elif response.content and not tool_calls:
                logger.warning(f"No valid plan on turn {turn}, continuing...")
                continue
            else:
                logger.warning(f"Empty response on turn {turn}, continuing...")
                continue

        if not plan or "module_tasks" not in plan:
            # Fallback: Use existing modules if available, otherwise create main.py
            logger.warning("Failed to parse LLM response, using fallback")
            if existing_modules:
                module_name = existing_modules[0]
                if task.target != "root":
                    module_name = f"{task.target}/{module_name}"
            else:
                module_name = "main.py" if task.target == "root" else f"{task.target}/main.py"

            plan = {
                "module_tasks": [
                    {
                        "module": module_name,
                        "action": "modify_existing" if existing_modules else "create_new",
                        "instruction": task.instruction,
                        "dependencies": [],
                        "complexity": "medium"
                    }
                ]
            }

        logger.info(
            "subsystem_plan_generated",
            subsystem=task.target,
            modules=len(plan.get("module_tasks", [])),
            is_revision=is_revision,
            design_turns_used=turn if use_design_tools else 0,
            design_tools_enabled=use_design_tools
        )

        return plan

    def _plan_to_tasks(
        self,
        plan: Dict[str, Any],
        parent_task: Task,
        context: Dict[str, Any]
    ) -> List[Task]:
        """Convert decomposition plan to Task objects"""
        tasks = []
        for module_def in plan.get("module_tasks", []):
            t = Task(
                id=f"T-MOD-{uuid.uuid4().hex[:8]}",
                parent_task_id=parent_task.id,
                type=TaskType(module_def.get("action", "modify_existing")),
                scope="MODULE",
                target=module_def.get("module", "unknown.py"),
                instruction=module_def.get("instruction", ""),
                context={**parent_task.context, **context},
                estimated_complexity=module_def.get("complexity", "medium")
            )
            tasks.append(t)

        logger.info(
            "subsystem_decomposition_complete",
            subsystem=parent_task.target,
            total_modules=len(tasks)
        )

        return tasks


class ModuleDecomposer:
    """
    Decomposes module tasks into class/function tasks

    Module: "Create AuthService class"
    → AuthService class: Create class with login/verify methods
    → authenticate_user() function: Standalone helper function

    Phase 3: Includes review-and-revise loop for module design quality
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        use_intelligent_selection: bool = True,
        use_review_loop: bool = True,
        review_min_score: float = 75.0,
        review_max_iterations: int = 2,
        design_tool_handler: Optional[Any] = None
    ):
        """
        Initialize ModuleDecomposer with Phase 2.5, Phase 3, and Phase 4C improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
            use_review_loop: Whether to use review-and-revise loop (default: True)
            review_min_score: Minimum quality score for acceptance (default: 75.0)
            review_max_iterations: Maximum revision iterations (default: 2)
            design_tool_handler: Optional DesignContextToolHandler for interactive design (Phase 4C)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection
        self.use_review_loop = use_review_loop
        self.review_min_score = review_min_score
        self.review_max_iterations = review_max_iterations

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

        # Phase 3: Review loop for quality improvement
        from planning.review_loop import ReviewLoop
        self.review_loop = ReviewLoop(llm_provider) if use_review_loop else None

        # Phase 4C: Interactive design with tool calling
        self.design_tool_handler = design_tool_handler

    async def decompose(
        self,
        task: Task,
        existing_classes: List[str],
        existing_functions: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose module task into class/function tasks using Phase 2.5 and Phase 3 improvements

        Args:
            task: Module-level task
            existing_classes: Existing classes in module
            existing_functions: Existing functions in module
            context: Additional context

        Returns:
            List of class/function-level tasks
        """
        context = context or {}

        # Generate initial decomposition plan
        initial_plan = await self._decompose_internal(
            task, existing_classes, existing_functions, context
        )

        # Phase 3: Review and revise if enabled
        if self.review_loop and not context.get("skip_review", False):
            logger.info("starting_review_loop", module=task.target)

            # Wrapper function for revision calls
            async def revise_func(
                task=task,
                existing_classes=existing_classes,
                existing_functions=existing_functions,
                context=None,
                revision_feedback=None,
                previous_output=None,
                is_revision=False,
                **kwargs
            ):
                """Wrapper to call _decompose_internal with revision context"""
                revision_context = {
                    **(context or {}),
                    "is_revision": is_revision,
                    "revision_feedback": revision_feedback,
                    "previous_output": previous_output
                }
                return await self._decompose_internal(
                    task, existing_classes, existing_functions, revision_context
                )

            # Review and potentially revise
            try:
                final_plan = await self.review_loop.review_and_revise(
                    initial_output=initial_plan,
                    primary_agent_func=revise_func,
                    review_context={
                        "tier": "module",
                        "type": "module_decomposition",
                        "original_request": task.instruction,
                        "module": task.target
                    },
                    min_score=self.review_min_score,
                    max_iterations=self.review_max_iterations
                )
            except Exception as e:
                logger.error("review_loop_failed", error=str(e))
                # Use initial plan if review fails
                final_plan = initial_plan
        else:
            # No review loop, use initial plan
            final_plan = initial_plan

        # Convert final plan to Task objects
        return self._plan_to_tasks(final_plan, task, context)

    async def _decompose_internal(
        self,
        task: Task,
        existing_classes: List[str],
        existing_functions: List[str],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Internal method to generate decomposition plan (called by both initial and revisions)

        Args:
            task: Module-level task
            existing_classes: Existing classes in module
            existing_functions: Existing functions in module
            context: Context including revision feedback if this is a revision

        Returns:
            Dict with decomposition plan (class_tasks, function_tasks)
        """
        context = context or {}
        is_revision = context.get("is_revision", False)
        revision_feedback = context.get("revision_feedback", None)

        # Phase 2.5 Step 1: Intelligent agent role selection
        agent_role = AgentRole.DESIGN  # Default role
        if self.agent_selector and not is_revision:
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=task.instruction,
                    project_context={
                        "module": task.target,
                        "existing_classes": existing_classes,
                        "existing_functions": existing_functions
                    },
                    use_llm=True
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    module=task.target
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default DESIGN role")
                agent_role = AgentRole.DESIGN

        # Phase 2.5 Step 2: Get role-based prompts
        prompts = PromptTemplateLibrary.get_module_decomposer_prompt(
            module_task=task.instruction,
            target_module=task.target,
            existing_classes=existing_classes,
            existing_functions=existing_functions,
            role=agent_role
        )

        # Phase 3: Add revision feedback to prompt if this is a revision
        if is_revision and revision_feedback:
            prompts["user"] += f"\n\n---\n**REVISION REQUEST**\n\nYour previous decomposition received the following review feedback. Please revise to address these issues:\n\n{revision_feedback}\n\nProvide an improved decomposition that addresses all the feedback."

        # Phase 4C: Add design exploration guidance if tools available
        if self.design_tool_handler and not is_revision:
            prompts["user"] += f"\n\n**Interactive Design Tools Available:**\n"
            prompts["user"] += f"You can use these tools to explore before finalizing your design:\n"
            prompts["user"] += f"- get_existing_modules: See what modules already exist\n"
            prompts["user"] += f"- analyze_module_pattern: Understand patterns used in existing modules\n"
            prompts["user"] += f"- search_similar_modules: Find modules with similar responsibilities\n"
            prompts["user"] += f"- propose_design_option: Propose and get feedback on a design\n"
            prompts["user"] += f"- request_requirement_clarification: Ask about unclear requirements\n"
            prompts["user"] += f"- validate_design_decision: Check if a design choice is good\n"
            prompts["user"] += f"\nFeel free to explore the codebase and validate your design before committing!"

        # Phase 2.5 Step 3 + Phase 4C: Call LLM with tool calling support
        messages = [
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["user"]}
        ]

        # Phase 4C: Multi-turn design conversation
        max_turns = 6  # Allow more turns for design exploration
        turn = 0
        plan = None

        # Check if design tools are available
        use_design_tools = self.design_tool_handler is not None and not is_revision

        while turn < max_turns:
            turn += 1

            try:
                # Prepare API call parameters
                call_params = {
                    "messages": messages,
                    "max_tokens": 2048,
                    "temperature": 0.0
                }

                # Add design tools if available (Phase 4C)
                if use_design_tools:
                    from design_context_tools import DESIGN_CONTEXT_TOOLS
                    call_params["tools"] = DESIGN_CONTEXT_TOOLS
                    call_params["tool_choice"] = "auto"
                else:
                    # Phase 2.5: Structured output
                    call_params["response_format"] = {"type": "json_object"}

                response = await self.llm_provider.create_completion(**call_params)

            except (TypeError, Exception) as e:
                # Fallback if tools/response_format not supported
                logger.warning(f"Advanced features not supported: {e}, using regular mode")
                response = await self.llm_provider.create_completion(
                    messages=messages,
                    max_tokens=2048,
                    temperature=0.0
                )

            # Phase 4C: Check if LLM made design tool calls
            tool_calls = getattr(response, 'tool_calls', None)

            if tool_calls and use_design_tools:
                # LLM requested design tools - execute them
                logger.info(
                    "design_tool_calls_requested",
                    module=task.target,
                    count=len(tool_calls),
                    turn=turn
                )

                # Add assistant's message with tool calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": tool_calls
                })

                # Execute each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info(
                        "executing_design_tool_call",
                        tool=tool_name,
                        args=tool_args
                    )

                    # Execute tool via handler
                    tool_result = self.design_tool_handler.handle_tool_call(
                        tool_name=tool_name,
                        arguments=tool_args
                    )

                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })

                # Continue conversation loop (LLM will see tool results)
                continue

            # No tool calls - process as final plan response
            # Phase 2.5 Step 4: Extract JSON with improved parsing
            plan = extract_json_from_response(response.content)

            if plan and ("class_tasks" in plan or "function_tasks" in plan):
                # Valid plan received
                break
            elif response.content and not tool_calls:
                # Response but no valid JSON - continue to allow retry
                logger.warning(f"No valid plan on turn {turn}, continuing...")
                continue
            else:
                # Empty response - continue
                logger.warning(f"Empty response on turn {turn}, continuing...")
                continue

        if not plan or ("class_tasks" not in plan and "function_tasks" not in plan):
            # Fallback: Try to extract function/class names from instruction
            logger.warning("Failed to parse LLM response, using fallback")
            function_tasks = []
            class_tasks = []

            import re
            # Look for function patterns like "add multiply() function" or "create divide()"
            func_pattern = r'\b(\w+)\s*\([^)]*\)'  # Matches function_name()
            matches = re.findall(func_pattern, task.instruction)

            if matches:
                for func_name in matches:
                    if func_name.lower() not in ['if', 'when', 'then', 'with', 'for', 'while']:
                        function_tasks.append({
                            "function_name": func_name,
                            "action": "create_new",
                            "instruction": f"Implement {func_name} function"
                        })

            plan = {
                "class_tasks": class_tasks,
                "function_tasks": function_tasks
            }

        logger.info(
            "module_plan_generated",
            module=task.target,
            classes=len(plan.get("class_tasks", [])),
            functions=len(plan.get("function_tasks", [])),
            is_revision=is_revision,
            design_turns_used=turn if use_design_tools else 0,
            design_tools_enabled=use_design_tools
        )

        return plan

    def _plan_to_tasks(
        self,
        plan: Dict[str, Any],
        parent_task: Task,
        context: Dict[str, Any]
    ) -> List[Task]:
        """Convert decomposition plan to Task objects"""
        tasks = []

        # Create class tasks
        for class_def in plan.get("class_tasks", []):
            t = Task(
                id=f"T-CLS-{uuid.uuid4().hex[:8]}",
                parent_task_id=parent_task.id,
                type=TaskType(class_def.get("action", "create_new")),
                scope="CLASS",
                target=f"{parent_task.target}::{class_def.get('class_name', 'UnknownClass')}",
                instruction=class_def.get("instruction", ""),
                context={**parent_task.context, "methods": class_def.get("methods", []), **context}
            )
            tasks.append(t)

        # Create function tasks
        for func_def in plan.get("function_tasks", []):
            t = Task(
                id=f"T-FNC-{uuid.uuid4().hex[:8]}",
                parent_task_id=parent_task.id,
                type=TaskType(func_def.get("action", "create_new")),
                scope="FUNCTION",
                target=f"{parent_task.target}::{func_def.get('function_name', 'unknown_function')}",
                instruction=func_def.get("instruction", ""),
                context={**parent_task.context, **context}
            )
            tasks.append(t)

        logger.info(
            "module_decomposition_complete",
            module=parent_task.target,
            total_tasks=len(tasks),
            classes=len(plan.get("class_tasks", [])),
            functions=len(plan.get("function_tasks", []))
        )

        return tasks


class ClassDecomposer:
    """
    Decomposes class tasks into method tasks

    Class: "Create AuthService with login/verify"
    → __init__() method: Initialize dependencies
    → login() method: Authenticate and generate token
    → verify_token() method: Validate JWT token

    Phase 3: Includes review-and-revise loop for class design quality
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        use_intelligent_selection: bool = True,
        use_review_loop: bool = True,
        review_min_score: float = 75.0,
        review_max_iterations: int = 2
    ):
        """
        Initialize ClassDecomposer with Phase 2.5 and Phase 3 improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
            use_review_loop: Whether to use review-and-revise loop (default: True)
            review_min_score: Minimum quality score for acceptance (default: 75.0)
            review_max_iterations: Maximum revision iterations (default: 2)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection
        self.use_review_loop = use_review_loop
        self.review_min_score = review_min_score
        self.review_max_iterations = review_max_iterations

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

        # Phase 3: Review loop for quality improvement
        from planning.review_loop import ReviewLoop
        self.review_loop = ReviewLoop(llm_provider) if use_review_loop else None

    async def decompose(
        self,
        task: Task,
        existing_methods: List[str],
        context: Dict[str, Any] = None
    ) -> List[Task]:
        """
        Decompose class task into method tasks using Phase 2.5 and Phase 3 improvements

        Args:
            task: Class-level task
            existing_methods: Existing methods in class
            context: Additional context

        Returns:
            List of method (function)-level tasks
        """
        context = context or {}

        # Get suggested methods from context
        suggested_methods = task.context.get("methods", [])

        # Generate initial decomposition plan
        initial_plan = await self._decompose_internal(
            task, suggested_methods, existing_methods, context
        )

        # Phase 3: Review and revise if enabled
        if self.review_loop and not context.get("skip_review", False):
            logger.info("starting_review_loop", class_name=task.target)

            # Wrapper function for revision calls
            async def revise_func(
                task=task,
                suggested_methods=suggested_methods,
                existing_methods=existing_methods,
                context=None,
                revision_feedback=None,
                previous_output=None,
                is_revision=False,
                **kwargs
            ):
                """Wrapper to call _decompose_internal with revision context"""
                revision_context = {
                    **(context or {}),
                    "is_revision": is_revision,
                    "revision_feedback": revision_feedback,
                    "previous_output": previous_output
                }
                return await self._decompose_internal(
                    task, suggested_methods, existing_methods, revision_context
                )

            # Review and potentially revise
            try:
                final_plan = await self.review_loop.review_and_revise(
                    initial_output=initial_plan,
                    primary_agent_func=revise_func,
                    review_context={
                        "tier": "class",
                        "type": "class_decomposition",
                        "original_request": task.instruction,
                        "class_name": task.target
                    },
                    min_score=self.review_min_score,
                    max_iterations=self.review_max_iterations
                )
            except Exception as e:
                logger.error("review_loop_failed", error=str(e))
                # Use initial plan if review fails
                final_plan = initial_plan
        else:
            # No review loop, use initial plan
            final_plan = initial_plan

        # Convert final plan to Task objects
        return self._plan_to_tasks(final_plan, task, context)

    async def _decompose_internal(
        self,
        task: Task,
        suggested_methods: List[str],
        existing_methods: List[str],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Internal method to generate decomposition plan (called by both initial and revisions)

        Args:
            task: Class-level task
            suggested_methods: Suggested methods from parent
            existing_methods: Existing methods in class
            context: Context including revision feedback if this is a revision

        Returns:
            Dict with decomposition plan (methods)
        """
        context = context or {}
        is_revision = context.get("is_revision", False)
        revision_feedback = context.get("revision_feedback", None)

        # Phase 2.5 Step 1: Intelligent agent role selection
        agent_role = AgentRole.DESIGN  # Default role
        if self.agent_selector and not is_revision:
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=task.instruction,
                    project_context={
                        "class": task.target,
                        "suggested_methods": suggested_methods,
                        "existing_methods": existing_methods
                    },
                    use_llm=True
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    class_name=task.target
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default DESIGN role")
                agent_role = AgentRole.DESIGN

        # Phase 2.5 Step 2: Get role-based prompts
        prompts = PromptTemplateLibrary.get_class_decomposer_prompt(
            class_task=task.instruction,
            target_class=task.target,
            suggested_methods=suggested_methods,
            existing_methods=existing_methods,
            role=agent_role
        )

        # Phase 3: Add revision feedback to prompt if this is a revision
        if is_revision and revision_feedback:
            prompts["user"] += f"\n\n---\n**REVISION REQUEST**\n\nYour previous decomposition received the following review feedback. Please revise to address these issues:\n\n{revision_feedback}\n\nProvide an improved decomposition that addresses all the feedback."

        # Phase 2.5 Step 3: Call LLM with structured output support
        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=2048,
                temperature=0.0,
                response_format={"type": "json_object"}  # Structured output
            )
        except (TypeError, Exception) as e:
            # Fallback if response_format not supported
            logger.warning(f"Structured output not supported: {e}, using regular mode")
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": prompts["system"]},
                    {"role": "user", "content": prompts["user"]}
                ],
                max_tokens=2048,
                temperature=0.0
            )

        # Phase 2.5 Step 4: Extract JSON with improved parsing
        plan = extract_json_from_response(response.content)

        if not plan or "methods" not in plan:
            logger.warning("Failed to parse LLM response, using fallback")
            plan = {"methods": []}

        logger.info(
            "class_plan_generated",
            class_name=task.target,
            methods=len(plan.get("methods", [])),
            is_revision=is_revision
        )

        return plan

    def _plan_to_tasks(
        self,
        plan: Dict[str, Any],
        parent_task: Task,
        context: Dict[str, Any]
    ) -> List[Task]:
        """Convert decomposition plan to Task objects"""
        tasks = []
        for method_def in plan.get("methods", []):
            t = Task(
                id=f"T-MTH-{uuid.uuid4().hex[:8]}",
                parent_task_id=parent_task.id,
                type=TaskType(method_def.get("action", "create_new")),
                scope="FUNCTION",
                target=f"{parent_task.target}.{method_def.get('name', 'unknown_method')}",
                instruction=method_def.get("instruction", ""),
                context={
                    **parent_task.context,
                    "signature": method_def.get("signature", ""),
                    **context
                }
            )
            tasks.append(t)

        logger.info(
            "class_decomposition_complete",
            class_name=parent_task.target,
            total_methods=len(tasks)
        )

        return tasks


class FunctionPlanner:
    """
    Plans function implementation (leaf node - generates actual code)

    Function: "Authenticate user and return JWT token"
    → Generates actual Python code
    → Generates unit tests

    Phase 3: Includes review-and-revise loop for code quality
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        use_intelligent_selection: bool = True,
        use_review_loop: bool = True,
        review_min_score: float = 75.0,
        review_max_iterations: int = 2,
        code_graph: Optional[Any] = None,
        tool_handler: Optional[Any] = None
    ):
        """
        Initialize FunctionPlanner with Phase 2.5, Phase 3, and Phase 4 improvements

        Args:
            llm_provider: LLM provider for making API calls
            use_intelligent_selection: Whether to use intelligent agent role selection (default: True)
            use_review_loop: Whether to use review-and-revise loop (default: True)
            review_min_score: Minimum quality score for code acceptance (default: 75.0)
            review_max_iterations: Maximum revision iterations (default: 2)
            code_graph: Optional code graph for context enrichment (Phase 4)
            tool_handler: Optional CodeContextToolHandler for interactive context fetching (Phase 4)
        """
        self.llm_provider = llm_provider
        self.use_intelligent_selection = use_intelligent_selection
        self.use_review_loop = use_review_loop
        self.review_min_score = review_min_score
        self.review_max_iterations = review_max_iterations

        # Phase 2.5: Intelligent agent selection
        self.agent_selector = IntelligentAgentSelector(llm_provider) if use_intelligent_selection else None

        # Phase 3: Review loop for quality improvement
        from planning.review_loop import ReviewLoop
        self.review_loop = ReviewLoop(llm_provider) if use_review_loop else None

        # Phase 4: Code graph and interactive tool calling
        self.code_graph = code_graph
        self.tool_handler = tool_handler

    async def generate_implementation(
        self,
        task: Task,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate actual code implementation for function using Phase 2.5 and Phase 3 improvements

        Args:
            task: Function-level task
            context: Additional context (existing code, dependencies, etc.)

        Returns:
            Dict with 'code', 'tests', 'explanation', and optionally '_review_metadata'
        """
        context = context or {}

        # Generate initial implementation
        initial_output = await self._generate_code_internal(task, context)

        # Phase 3: Review and revise if enabled
        if self.review_loop and not context.get("skip_review", False):
            logger.info("starting_review_loop", function=task.target)

            # Wrapper function for revision calls
            async def revise_func(
                task=task,
                context=None,
                revision_feedback=None,
                previous_output=None,
                is_revision=False,
                **kwargs
            ):
                """Wrapper to call _generate_code_internal with revision context"""
                revision_context = {
                    **(context or {}),
                    "is_revision": is_revision,
                    "revision_feedback": revision_feedback,
                    "previous_output": previous_output
                }
                return await self._generate_code_internal(task, revision_context)

            # Review and potentially revise
            try:
                final_output = await self.review_loop.review_and_revise(
                    initial_output=initial_output,
                    primary_agent_func=revise_func,
                    review_context={
                        "tier": "function",
                        "type": "code_implementation",
                        "original_request": task.instruction,
                        "function_name": task.target.split("::")[-1]
                    },
                    min_score=self.review_min_score,
                    max_iterations=self.review_max_iterations
                )
                return final_output
            except Exception as e:
                logger.error("review_loop_failed", error=str(e))
                # Return initial output if review fails
                return initial_output
        else:
            # No review loop, return initial output
            return initial_output

    async def _generate_code_internal(
        self,
        task: Task,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Internal method to generate code (called by both initial generation and revisions)

        Args:
            task: Function-level task
            context: Context including revision feedback if this is a revision

        Returns:
            Dict with 'code', 'explanation'
        """
        context = context or {}

        signature = task.context.get("signature", "")
        module_path = task.target.split("::")[0]
        function_name = task.target.split("::")[-1]

        is_revision = context.get("is_revision", False)
        revision_feedback = context.get("revision_feedback", None)

        # Phase 2.5 Step 1: Intelligent agent role selection
        # For code generation, default to IMPLEMENTATION role
        agent_role = AgentRole.IMPLEMENTATION
        if self.agent_selector and not is_revision:
            try:
                selection = await self.agent_selector.select_agent(
                    user_request=task.instruction,
                    project_context={
                        "function": task.target,
                        "signature": signature,
                        "module": module_path
                    },
                    use_llm=False  # Use heuristic for speed (code gen is always IMPLEMENTATION)
                )
                agent_role = selection["role"]
                logger.info(
                    "agent_role_selected",
                    role=agent_role.value,
                    confidence=selection.get("confidence", 0.0),
                    function=function_name
                )
            except Exception as e:
                logger.warning(f"Agent selection failed: {e}, using default IMPLEMENTATION role")
                agent_role = AgentRole.IMPLEMENTATION

        # Phase 2.5 Step 2: Get role-based prompts
        # Build module context string
        module_context = f"Module: {module_path}\n"
        if signature:
            module_context += f"Signature: {signature}\n"
        module_context += f"Task: {task.instruction}"

        prompts = PromptTemplateLibrary.get_function_generator_prompt(
            function_name=function_name,
            instruction=task.instruction,
            module_context=module_context,
            role=agent_role
        )

        # Phase 3: Add revision feedback to prompt if this is a revision
        if is_revision and revision_feedback:
            prompts["user"] += f"\n\n---\n**REVISION REQUEST**\n\nYour previous implementation received the following review feedback. Please revise the code to address these issues:\n\n{revision_feedback}\n\nProvide an improved implementation that addresses all the feedback."

        # Phase 4: Add rich context from code graph if available
        if context.get("rich_context"):
            rich_ctx = context["rich_context"]
            context_info = f"\n\n**Available Code Context:**\n"
            context_info += f"- This function is called by {len(rich_ctx.get('callers', []))} other functions\n"
            context_info += f"- This function calls {len(rich_ctx.get('callees', []))} other functions\n"
            context_info += f"- Related classes: {len(rich_ctx.get('related_classes', []))}\n"
            context_info += f"\nYou can use the following tools to fetch more context as needed:\n"
            context_info += f"- get_function_definition: Get source code of a specific function\n"
            context_info += f"- get_function_callers: See who calls a function\n"
            context_info += f"- get_function_callees: See what a function calls\n"
            context_info += f"- get_class_definition: Get a class's source code\n"
            context_info += f"- get_module_overview: Get overview of a module\n"
            context_info += f"- search_functions: Search for functions by name\n"
            prompts["user"] += context_info

        # Phase 2.5 Step 3 + Phase 4: Call LLM with tool calling support
        messages = [
            {"role": "system", "content": prompts["system"]},
            {"role": "user", "content": prompts["user"]}
        ]

        # Phase 4: Multi-turn conversation with tool calling
        max_turns = 5  # Prevent infinite loops
        turn = 0
        result = None

        # Check if tool calling is available
        use_tools = self.tool_handler is not None and not is_revision

        while turn < max_turns:
            turn += 1

            try:
                # Prepare API call parameters
                call_params = {
                    "messages": messages,
                    "max_tokens": 3072,
                    "temperature": 0.0
                }

                # Add tools if available (Phase 4)
                if use_tools:
                    from code_context_tools import CODE_CONTEXT_TOOLS
                    call_params["tools"] = CODE_CONTEXT_TOOLS
                    call_params["tool_choice"] = "auto"
                else:
                    # Phase 2.5: Structured output
                    call_params["response_format"] = {"type": "json_object"}

                response = await self.llm_provider.create_completion(**call_params)

            except (TypeError, Exception) as e:
                # Fallback if tools/response_format not supported
                logger.warning(f"Advanced features not supported: {e}, using regular mode")
                response = await self.llm_provider.create_completion(
                    messages=messages,
                    max_tokens=3072,
                    temperature=0.0
                )

            # Phase 4: Check if LLM made tool calls
            tool_calls = getattr(response, 'tool_calls', None)

            if tool_calls and use_tools:
                # LLM requested tool calls - execute them
                logger.info(
                    "tool_calls_requested",
                    function=function_name,
                    count=len(tool_calls),
                    turn=turn
                )

                # Add assistant's message with tool calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": tool_calls
                })

                # Execute each tool call
                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info(
                        "executing_tool_call",
                        tool=tool_name,
                        args=tool_args
                    )

                    # Execute tool via handler
                    tool_result = self.tool_handler.handle_tool_call(
                        tool_name=tool_name,
                        arguments=tool_args
                    )

                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })

                # Continue conversation loop (LLM will see tool results)
                continue

            # No tool calls - process as code response
            # Phase 2.5 Step 4: Extract JSON or code from response
            plan = extract_json_from_response(response.content)
            if plan and "code" in plan:
                result = plan
                break
            elif response.content:
                # If no JSON, treat entire response as code
                logger.warning("No JSON in response, treating as direct code")
                result = {
                    "code": response.content.strip(),
                    "explanation": "Generated implementation"
                }
                break
            else:
                # Empty response, continue loop
                logger.warning(f"Empty response on turn {turn}, continuing...")
                continue

        # Validate we got some code
        if not result or not result.get("code"):
            logger.error("Failed to generate code after all turns, using placeholder")
            result = {
                "code": f"def {function_name}():\n    '''TODO: {task.instruction}'''\n    pass",
                "explanation": "Placeholder implementation (code generation failed)"
            }

        logger.info(
            "function_code_generated",
            function=function_name,
            code_length=len(result.get("code", "")),
            is_revision=is_revision,
            turns_used=turn,
            tools_enabled=use_tools
        )

        return result
