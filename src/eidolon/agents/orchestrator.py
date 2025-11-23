import asyncio
import os
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
import time

from eidolon.models import Agent, AgentScope, AgentStatus, Card, CardType, CardStatus, ProposedFix
from eidolon.analysis import CodeAnalyzer, ModuleInfo, SubsystemInfo
from eidolon.storage import Database
from eidolon.cache import CacheManager
from eidolon.git_integration import GitManager, GitChanges
from eidolon.resilience import (
    retry_with_backoff,
    with_timeout,
    TimeoutConfig,
    RetryConfig,
    AI_API_BREAKER,
    AI_RATE_LIMITER
)
from eidolon.logging_config import get_logger
from eidolon.llm_providers import create_provider, LLMProvider

logger = get_logger(__name__)


class AgentOrchestrator:
    """Orchestrates the hierarchical agent system with parallel execution"""

    def __init__(self, db: Database,
                 llm_provider: Optional[LLMProvider] = None,
                 max_concurrent_functions: int = 10,
                 max_concurrent_modules: int = 3,
                 enable_cache: bool = True):
        self.db = db

        # Initialize LLM provider (auto-detects from environment if not provided)
        self.llm_provider = llm_provider or create_provider()
        logger.info(
            "orchestrator_llm_provider",
            provider=self.llm_provider.get_provider_name(),
            model=self.llm_provider.get_model_name()
        )

        self.analyzer = CodeAnalyzer()
        self.call_graph = None  # Will be populated during analysis

        # Cache management
        self.enable_cache = enable_cache
        self.cache = CacheManager() if enable_cache else None

        # Concurrency control
        self.max_concurrent_functions = max_concurrent_functions
        self.max_concurrent_modules = max_concurrent_modules
        self.function_semaphore = asyncio.Semaphore(max_concurrent_functions)
        self.module_semaphore = asyncio.Semaphore(max_concurrent_modules)

        # Progress tracking
        self.progress = {
            'total_modules': 0,
            'completed_modules': 0,
            'total_functions': 0,
            'completed_functions': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': [],
            'current_activity': 'Initializing...',
            'activities': []  # Recent activity log (last 10 items)
        }
        self._activity_callback = None  # Callback for real-time activity updates

    async def initialize(self):
        """Initialize the orchestrator (async setup)"""
        if self.cache:
            await self.cache.initialize()

    def _log_activity(self, activity: str, level: str = "info"):
        """Log an activity and update progress tracking"""
        import time

        activity_entry = {
            'message': activity,
            'level': level,
            'timestamp': time.time()
        }

        # Update current activity
        self.progress['current_activity'] = activity

        # Add to recent activities (keep last 10)
        self.progress['activities'].append(activity_entry)
        if len(self.progress['activities']) > 10:
            self.progress['activities'].pop(0)

        # Also log to standard logger
        logger.info("orchestrator_activity", activity=activity, level=level)

        # Call activity callback if set (for real-time WebSocket updates)
        if self._activity_callback:
            asyncio.create_task(self._activity_callback(activity_entry))

    def set_activity_callback(self, callback):
        """Set a callback function for real-time activity updates"""
        self._activity_callback = callback

    async def _call_ai_with_resilience(
        self,
        max_tokens: int,
        messages: list,
        estimated_tokens: int = 1000,
        response_format: Optional[Dict[str, Any]] = None
    ):
        """
        Call AI API with full resilience patterns: timeout, retry, circuit breaker, rate limiting

        Args:
            max_tokens: Max tokens in response
            messages: Messages to send
            estimated_tokens: Estimated token usage for rate limiting
            response_format: Structured response preferences (defaults to text)

        Returns:
            LLMResponse from provider

        Raises:
            Exception: If all retries exhausted or circuit breaker open
        """
        # Rate limiting - wait if necessary
        await AI_RATE_LIMITER.acquire(estimated_tokens)

        # Log AI API call
        self._log_activity(f"🤖 Calling LLM ({self.llm_provider.get_model_name()})")

        api_response_format = response_format or {"type": "text"}

        # Define the actual API call using provider abstraction
        async def make_api_call():
            return await self.llm_provider.create_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.0,
                response_format=api_response_format,
            )

        # Wrap with timeout
        async def call_with_timeout():
            return await with_timeout(
                make_api_call,
                timeout=TimeoutConfig.AI_API_TIMEOUT,
                timeout_message=f"AI API call timed out after {TimeoutConfig.AI_API_TIMEOUT}s"
            )

        # Wrap with circuit breaker
        async def call_with_breaker():
            return await AI_API_BREAKER.call(call_with_timeout)

        # Wrap with retry logic
        response = await retry_with_backoff(
            call_with_breaker,
            config=RetryConfig()
        )

        # Update rate limiter with actual token usage
        actual_tokens = response.input_tokens + response.output_tokens
        AI_RATE_LIMITER.record_actual_tokens(actual_tokens)

        return response

    async def analyze_codebase(self, path: str) -> Agent:
        """
        Start hierarchical analysis of a codebase with 5-tier hierarchy.
        SYSTEM → SUBSYSTEM (optional) → MODULE → CLASS (optional) → FUNCTION
        Returns the system-level agent.
        """
        # Create system-level agent
        self._log_activity(f"📊 Creating system agent for {path}")
        system_agent = Agent(
            id="",  # Will be generated by DB
            scope=AgentScope.SYSTEM,
            target=path,
            status=AgentStatus.ANALYZING
        )
        system_agent = await self.db.create_agent(system_agent)

        # Analyze the codebase structure
        self._log_activity(f"🔍 Scanning codebase structure...")
        self.analyzer.base_path = Path(path)
        modules = self.analyzer.analyze_directory()

        # Build call graph for cross-file dependency analysis
        self._log_activity(f"🕸️ Building call graph ({len(modules)} modules)")
        logger.info("building_call_graph")
        self.call_graph = self.analyzer.build_call_graph(modules)
        logger.info(
            "call_graph_built",
            functions=len(self.call_graph['functions']),
            orphaned=len(self.call_graph['orphaned'])
        )

        # Group modules into subsystems based on directory structure
        subsystems = self.analyzer.group_modules_into_subsystems(modules)

        # Initialize progress tracking
        total_functions = sum(
            len(m.functions) + sum(len(c.methods) for c in m.classes)
            for m in modules
        )
        total_classes = sum(len(m.classes) for m in modules)

        self.progress = {
            'total_modules': len(modules),
            'completed_modules': 0,
            'total_classes': total_classes,
            'completed_classes': 0,
            'total_functions': total_functions,
            'completed_functions': 0,
            'total_subsystems': len(subsystems),
            'completed_subsystems': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': [],
            'current_activity': 'Initializing...',
            'activities': []
        }
        logger.info(
            "starting_5tier_analysis",
            subsystems=len(subsystems),
            modules=len(modules),
            classes=total_classes,
            functions=total_functions,
            max_concurrent_modules=self.max_concurrent_modules,
            max_concurrent_functions=self.max_concurrent_functions
        )

        # Deploy agents based on whether we have subsystems
        if subsystems:
            # Deploy subsystem-level agents IN PARALLEL
            self._log_activity(f"🚀 Deploying {len(subsystems)} subsystem agents")
            subsystem_tasks = [
                self._deploy_subsystem_agent(system_agent.id, subsystem_info)
                for subsystem_info in subsystems
            ]
            subsystem_agents = await asyncio.gather(*subsystem_tasks, return_exceptions=True)

            # Process results and track errors
            for i, result in enumerate(subsystem_agents):
                if isinstance(result, Exception):
                    error_msg = f"Subsystem {subsystems[i].name} failed: {str(result)}"
                    print(f"ERROR: {error_msg}")
                    self.progress['errors'].append(error_msg)
                else:
                    system_agent.children_ids.append(result.id)
        else:
            # No subsystems - deploy modules directly under system
            self._log_activity(f"🚀 Deploying {len(modules)} module agents")
            module_tasks = [
                self._deploy_module_agent(system_agent.id, module_info)
                for module_info in modules
            ]
            module_agents = await asyncio.gather(*module_tasks, return_exceptions=True)

            # Process results and track errors
            for i, result in enumerate(module_agents):
                if isinstance(result, Exception):
                    error_msg = f"Module {modules[i].file_path} failed: {str(result)}"
                    print(f"ERROR: {error_msg}")
                    self.progress['errors'].append(error_msg)
                else:
                    system_agent.children_ids.append(result.id)

        logger.info(
            "analysis_complete",
            completed_subsystems=self.progress['completed_subsystems'],
            total_subsystems=len(subsystems),
            completed_modules=self.progress['completed_modules'],
            total_modules=len(modules),
            completed_classes=self.progress['completed_classes'],
            total_classes=total_classes,
            completed_functions=self.progress['completed_functions'],
            total_functions=total_functions,
            errors=len(self.progress['errors'])
        )

        # Run system-level analysis
        await self._run_system_analysis(system_agent, modules)

        # Update system agent
        system_agent.update_status(AgentStatus.COMPLETED)
        await self.db.update_agent(system_agent)

        return system_agent

    async def analyze_incremental(
        self,
        path: str,
        base: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform incremental analysis - only analyze files that have changed since last analysis.

        Args:
            path: Path to the codebase
            base: Git reference to compare against (branch/commit). Defaults to last analysis or HEAD.

        Returns:
            Dict with analysis results and statistics
        """
        session_id = str(uuid.uuid4())
        path_obj = Path(path)

        # Initialize git manager
        git_manager = GitManager(path)

        # Check if it's a git repository
        if not git_manager.is_git_repo():
            return {
                'error': 'Not a git repository. Incremental analysis requires git.',
                'suggestion': 'Run full analysis instead, or initialize git repository.'
            }

        # Get git metadata
        current_commit = git_manager.get_current_commit()
        current_branch = git_manager.get_current_branch()

        # Get last analysis session to determine what changed
        last_session = await self.db.get_last_analysis_session(str(path_obj.absolute()))

        # Determine base reference for comparison
        if base is None:
            # Use last analysis commit or HEAD
            base = last_session['git_commit'] if last_session else 'HEAD'

        print(f"\n🔄 Incremental Analysis")
        print(f"Repository: {path}")
        print(f"Current commit: {current_commit}")
        print(f"Comparing against: {base}")

        # Get changed Python files
        try:
            git_changes = git_manager.get_changed_python_files(base=base)
        except Exception as e:
            return {
                'error': f'Failed to detect git changes: {str(e)}',
                'suggestion': 'Check git status and try again.'
            }

        print(f"\n📊 Changes Detected:")
        print(f"  Modified: {len(git_changes.modified)} files")
        print(f"  Added: {len(git_changes.added)} files")
        print(f"  Deleted: {len(git_changes.deleted)} files")
        print(f"  Total to analyze: {len(git_changes.all_changed)} files")

        # If no changes, return early
        if not git_changes.all_changed and not git_changes.deleted:
            return {
                'status': 'no_changes',
                'message': 'No Python files have changed since last analysis',
                'stats': {
                    'files_analyzed': 0,
                    'files_skipped': 0,
                    'cache_hits': 0,
                    'cache_misses': 0
                }
            }

        # Create analysis session
        await self.db.create_analysis_session(
            session_id=session_id,
            path=str(path_obj.absolute()),
            mode='incremental',
            git_commit=current_commit,
            git_branch=current_branch
        )

        # Analyze directory to get all modules
        self.analyzer.base_path = path_obj
        all_modules = self.analyzer.analyze_directory()

        # Filter to only changed files
        changed_file_set = set(git_changes.all_changed)
        modules_to_analyze = [
            m for m in all_modules
            if any(Path(m.file_path).samefile(path_obj / changed_file)
                   for changed_file in changed_file_set
                   if (path_obj / changed_file).exists())
        ]

        print(f"\n🎯 Analysis Plan:")
        print(f"  Total modules in codebase: {len(all_modules)}")
        print(f"  Modules to analyze: {len(modules_to_analyze)}")
        print(f"  Modules skipped (unchanged): {len(all_modules) - len(modules_to_analyze)}")

        # Invalidate cache for deleted files
        for deleted_file in git_changes.deleted:
            if self.cache:
                await self.cache.invalidate_file(str(path_obj / deleted_file))
                print(f"  ❌ Invalidated cache for deleted file: {deleted_file}")

        # Build call graph for cross-file dependency analysis
        print("\n🔗 Building call graph...")
        self.call_graph = self.analyzer.build_call_graph(all_modules)  # Use all modules for complete graph

        # Create system-level agent for this incremental analysis
        system_agent = Agent(
            id="",
            scope=AgentScope.SYSTEM,
            target=path,
            status=AgentStatus.ANALYZING,
            session_id=session_id
        )
        system_agent = await self.db.create_agent(system_agent)

        # Initialize progress tracking
        total_functions = sum(
            len(m.functions) + sum(len(c.methods) for c in m.classes)
            for m in modules_to_analyze
        )
        total_classes = sum(len(m.classes) for m in modules_to_analyze)

        self.progress = {
            'total_modules': len(modules_to_analyze),
            'completed_modules': 0,
            'total_classes': total_classes,
            'completed_classes': 0,
            'total_functions': total_functions,
            'completed_functions': 0,
            'total_subsystems': 0,  # Incremental doesn't use subsystems
            'completed_subsystems': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': [],
            'current_activity': 'Initializing...',
            'activities': []
        }

        print(f"\n🚀 Starting incremental analysis (5-tier hierarchy):")
        print(f"  Modules: {len(modules_to_analyze)}")
        print(f"  Classes: {total_classes}")
        print(f"  Functions: {total_functions}")
        print(f"  Concurrency: {self.max_concurrent_modules} modules, {self.max_concurrent_functions} functions")

        # Deploy module-level agents IN PARALLEL (only for changed files)
        module_tasks = [
            self._deploy_module_agent(system_agent.id, module_info)
            for module_info in modules_to_analyze
        ]

        module_agents = await asyncio.gather(*module_tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(module_agents):
            if isinstance(result, Exception):
                error_msg = f"Module {modules_to_analyze[i].file_path} failed: {str(result)}"
                print(f"ERROR: {error_msg}")
                self.progress['errors'].append(error_msg)
            else:
                system_agent.children_ids.append(result.id)

        print(f"\n✅ Incremental analysis complete!")
        print(f"  Modules analyzed: {self.progress['completed_modules']}/{len(modules_to_analyze)}")
        print(f"  Classes analyzed: {self.progress['completed_classes']}/{total_classes}")
        print(f"  Functions analyzed: {self.progress['completed_functions']}/{total_functions}")
        print(f"  Cache hits: {self.progress['cache_hits']}")
        print(f"  Cache misses: {self.progress['cache_misses']}")
        print(f"  Errors: {len(self.progress['errors'])}")

        # Run system-level analysis (only on changed modules)
        if modules_to_analyze:
            await self._run_system_analysis(system_agent, modules_to_analyze)

        # Update system agent
        system_agent.update_status(AgentStatus.COMPLETED)
        await self.db.update_agent(system_agent)

        # Update analysis session with results
        files_analyzed = [m.file_path for m in modules_to_analyze]
        files_skipped = [m.file_path for m in all_modules if m not in modules_to_analyze]

        await self.db.update_analysis_session(
            session_id=session_id,
            files_analyzed=files_analyzed,
            files_skipped=files_skipped,
            total_modules=len(modules_to_analyze),
            total_functions=total_functions,
            cache_hits=self.progress['cache_hits'],
            cache_misses=self.progress['cache_misses']
        )

        return {
            'status': 'completed',
            'session_id': session_id,
            'agent_id': system_agent.id,
            'git_info': {
                'commit': current_commit,
                'branch': current_branch,
                'base_reference': base
            },
            'changes': {
                'modified': len(git_changes.modified),
                'added': len(git_changes.added),
                'deleted': len(git_changes.deleted)
            },
            'stats': {
                'files_analyzed': len(files_analyzed),
                'files_skipped': len(files_skipped),
                'modules_analyzed': len(modules_to_analyze),
                'functions_analyzed': total_functions,
                'cache_hits': self.progress['cache_hits'],
                'cache_misses': self.progress['cache_misses'],
                'errors': len(self.progress['errors'])
            },
            'hierarchy': await self.get_agent_hierarchy(system_agent.id)
        }

    async def _deploy_subsystem_agent(self, parent_id: str, subsystem_info: SubsystemInfo) -> Agent:
        """
        Deploy an agent for a subsystem (directory/package).
        Coordinates analysis of all modules and nested subsystems within.
        """
        subsystem_agent = Agent(
            id="",
            scope=AgentScope.SUBSYSTEM,
            target=subsystem_info.directory,
            status=AgentStatus.ANALYZING,
            parent_id=parent_id
        )
        subsystem_agent = await self.db.create_agent(subsystem_agent)

        # Deploy child subsystem agents IN PARALLEL (for nested directories)
        child_tasks = []
        for child_subsystem in subsystem_info.subsystems:
            task = self._deploy_subsystem_agent(subsystem_agent.id, child_subsystem)
            child_tasks.append(task)

        # Deploy module agents IN PARALLEL
        for module in subsystem_info.modules:
            task = self._deploy_module_agent(subsystem_agent.id, module)
            child_tasks.append(task)

        # Execute all child agents concurrently
        child_agents = await asyncio.gather(*child_tasks, return_exceptions=True)

        # Process results
        for i, result in enumerate(child_agents):
            if isinstance(result, Exception):
                error_msg = f"Child agent failed in subsystem {subsystem_info.name}: {str(result)}"
                print(f"  ERROR: {error_msg}")
                self.progress['errors'].append(error_msg)
            else:
                subsystem_agent.children_ids.append(result.id)

        # Run subsystem-level analysis
        await self._run_subsystem_analysis(subsystem_agent, subsystem_info)

        subsystem_agent.update_status(AgentStatus.COMPLETED)
        await self.db.update_agent(subsystem_agent)

        # Update progress
        self.progress['completed_subsystems'] += 1
        logger.info(
            "subsystem_complete",
            name=subsystem_info.name,
            modules=len(subsystem_info.modules),
            nested_subsystems=len(subsystem_info.subsystems)
        )

        return subsystem_agent

    async def _deploy_module_agent(self, parent_id: str, module_info: ModuleInfo) -> Agent:
        """Deploy an agent for a module (file) with parallel function analysis"""
        # Use semaphore for rate limiting at module level
        async with self.module_semaphore:
            module_name = Path(module_info.file_path).name
            self._log_activity(f"📄 Analyzing module: {module_name}")

            module_agent = Agent(
                id="",
                scope=AgentScope.MODULE,
                target=module_info.file_path,
                status=AgentStatus.ANALYZING,
                parent_id=parent_id
            )
            module_agent = await self.db.create_agent(module_agent)

            # Collect tasks for classes and standalone functions
            child_tasks = []

            # Deploy CLASS agents for each class (which will deploy function agents for methods)
            for cls in module_info.classes:
                task = self._deploy_class_agent(
                    module_agent.id,
                    module_info,
                    cls
                )
                child_tasks.append(task)

            # Deploy FUNCTION agents for standalone functions (not in classes)
            for func in module_info.functions:
                task = self._deploy_function_agent(
                    module_agent.id,
                    module_info,
                    func.name,
                    func
                )
                child_tasks.append(task)

            # Run ALL child agents (classes and functions) IN PARALLEL
            child_agents = await asyncio.gather(*child_tasks, return_exceptions=True)

            # Process results and track errors
            valid_agents = []
            for i, result in enumerate(child_agents):
                if isinstance(result, Exception):
                    error_msg = f"Child agent failed in module {module_info.file_path}: {str(result)}"
                    print(f"  ERROR: {error_msg}")
                    self.progress['errors'].append(error_msg)
                else:
                    valid_agents.append(result)
                    module_agent.children_ids.append(result.id)

            # Run module-level analysis
            await self._run_module_analysis(module_agent, module_info, valid_agents)

            module_agent.update_status(AgentStatus.COMPLETED)
            await self.db.update_agent(module_agent)

            # Update progress
            self.progress['completed_modules'] += 1
            print(f"  Module {self.progress['completed_modules']}/{self.progress['total_modules']} complete: {module_info.file_path}")

            return module_agent

    async def _deploy_class_agent(
        self,
        parent_id: str,
        module_info: ModuleInfo,
        class_info: Any
    ) -> Agent:
        """
        Deploy an agent for a class.
        Coordinates analysis of all methods within the class.
        """
        class_agent = Agent(
            id="",
            scope=AgentScope.CLASS,
            target=f"{module_info.file_path}::{class_info.name}",
            status=AgentStatus.ANALYZING,
            parent_id=parent_id
        )
        class_agent = await self.db.create_agent(class_agent)

        # Deploy FUNCTION agents for all methods IN PARALLEL
        method_tasks = []
        for method in class_info.methods:
            task = self._deploy_function_agent(
                class_agent.id,
                module_info,
                f"{class_info.name}.{method.name}",
                method
            )
            method_tasks.append(task)

        # Execute all method agents concurrently
        method_agents = await asyncio.gather(*method_tasks, return_exceptions=True)

        # Process results
        valid_method_agents = []
        for i, result in enumerate(method_agents):
            if isinstance(result, Exception):
                error_msg = f"Method analysis failed in class {class_info.name}: {str(result)}"
                print(f"  ERROR: {error_msg}")
                self.progress['errors'].append(error_msg)
            else:
                valid_method_agents.append(result)
                class_agent.children_ids.append(result.id)

        # Run class-level analysis
        await self._run_class_analysis(class_agent, module_info, class_info, valid_method_agents)

        class_agent.update_status(AgentStatus.COMPLETED)
        await self.db.update_agent(class_agent)

        # Update progress
        self.progress['completed_classes'] += 1

        return class_agent

    async def _deploy_function_agent(
        self,
        parent_id: str,
        module_info: ModuleInfo,
        func_name: str,
        func_info: Any
    ) -> Agent:
        """Deploy an agent for a function with rate limiting and caching"""
        # Check cache first (outside semaphore to avoid blocking)
        cached_result = None
        if self.cache:
            cached_result = await self.cache.get_cached_result(
                module_info.file_path,
                'Function',
                func_name
            )

        if cached_result:
            # Cache hit - restore from cache without API call
            self.progress['cache_hits'] += 1
            self.progress['completed_functions'] += 1

            func_agent = Agent(
                id="",
                scope=AgentScope.FUNCTION,
                target=f"{module_info.file_path}::{func_name}",
                status=AgentStatus.COMPLETED,
                parent_id=parent_id,
                findings=cached_result.findings,
                total_tokens=0,  # No API call made
                total_cost=0.0
            )
            func_agent = await self.db.create_agent(func_agent)

            # Restore cards from cache
            for card_data in cached_result.cards_data:
                card = Card(**card_data)
                card.owner_agent = func_agent.id
                await self.db.create_card(card)
                func_agent.cards_created.append(card.id)

            await self.db.update_agent(func_agent)

            return func_agent

        # Cache miss - perform analysis with semaphore
        self.progress['cache_misses'] += 1

        async with self.function_semaphore:
            func_agent = Agent(
                id="",
                scope=AgentScope.FUNCTION,
                target=f"{module_info.file_path}::{func_name}",
                status=AgentStatus.ANALYZING,
                parent_id=parent_id
            )
            func_agent = await self.db.create_agent(func_agent)

            # Analyze the function
            await self._run_function_analysis(func_agent, module_info, func_info)

            func_agent.update_status(AgentStatus.COMPLETED)
            await self.db.update_agent(func_agent)

            # Store in cache for future use
            if self.cache:
                # Collect card data for caching
                cards_data = []
                for card_id in func_agent.cards_created:
                    card = await self.db.get_card(card_id)
                    if card:
                        cards_data.append(card.model_dump())

                await self.cache.store_result(
                    module_info.file_path,
                    'Function',
                    func_name,
                    func_agent.findings,
                    cards_data,
                    {
                        'complexity': func_info.complexity,
                        'line_count': func_info.line_end - func_info.line_start,
                        'is_async': func_info.is_async
                    }
                )

            # Update progress
            self.progress['completed_functions'] += 1

            return func_agent

    async def _run_function_analysis(self, agent: Agent, module_info: ModuleInfo, func_info: Any):
        """Run AI-powered analysis on a function with cross-file context"""
        start_time = time.time()

        # Read the actual source code
        with open(module_info.file_path, 'r') as f:
            lines = f.readlines()
            func_source = ''.join(lines[func_info.line_start - 1:func_info.line_end])

        # Get function context from call graph
        context_info = self.analyzer.get_function_context(func_info, self.call_graph, module_info)

        # Build enhanced context with caller/callee information
        context_parts = [
            f"You are analyzing a function in a Python codebase.\n",
            f"File: {module_info.file_path}",
            f"Function: {func_info.name}",
            f"Lines: {func_info.line_start}-{func_info.line_end}",
            f"Complexity: {func_info.complexity}\n",
            f"Source:\n```python\n{func_source}\n```\n"
        ]

        # Add caller context
        if context_info['called_by']:
            context_parts.append(f"**Called by:** {', '.join(context_info['called_by'][:3])}\n")
            if context_info['caller_code']:
                context_parts.append("**Caller code (for context):**")
                for caller in context_info['caller_code']:
                    context_parts.append(f"\n```python\n# {caller['name']}\n{caller['code']}\n```")

        # Add callee context
        if context_info['calls']:
            context_parts.append(f"\n**Calls:** {', '.join(context_info['calls'][:3])}\n")
            if context_info['callee_code']:
                context_parts.append("**Called function code (for context):**")
                for callee in context_info['callee_code']:
                    context_parts.append(f"\n```python\n# {callee['name']}\n{callee['code']}\n```")

        # Add analysis instructions
        context_parts.append("""
Analyze this function for:
1. Potential bugs or errors (especially at call boundaries)
2. Code smells or anti-patterns
3. Opportunities for improvement
4. Security concerns
5. Inconsistencies with callers/callees

For EACH issue found, provide:
- A clear description of the problem
- If fixable, provide the FIXED CODE as a code block

Format your response like this:
## Issues Found

### Issue 1: [Brief title]
**Problem:** [Description]
**Severity:** [High/Medium/Low]

**Fix:**
```python
[corrected code here]
```

Be specific and focus on actionable fixes.""")

        context = '\n'.join(context_parts)
        agent.add_message("user", context)

        # Call AI API with higher token limit for fixes (with resilience)
        try:
            response = await self._call_ai_with_resilience(
                max_tokens=2048,
                messages=[{"role": "user", "content": context}],
                estimated_tokens=2500
            )

            analysis = response.content
            tokens_in = response.input_tokens
            tokens_out = response.output_tokens

            latency = (time.time() - start_time) * 1000
            agent.add_message("assistant", analysis, tokens_in, tokens_out, latency_ms=latency)

            # Parse findings
            findings = [line.strip() for line in analysis.split('\n') if line.strip().startswith('-')]
            agent.findings.extend(findings)

            # Try to extract a proposed fix from the response
            proposed_fix = self._extract_proposed_fix(analysis, module_info, func_info, func_source)

            # Create card with fix if available
            if findings or proposed_fix:
                card = Card(
                    id="",
                    type=CardType.REVIEW,
                    title=f"Analysis: {func_info.name}",
                    summary=analysis,
                    owner_agent=agent.id,
                    status=CardStatus.PROPOSED if proposed_fix else CardStatus.NEW,
                    proposed_fix=proposed_fix
                )
                card.links.code.append(f"{module_info.file_path}:{func_info.line_start}")
                card.metrics.confidence = 0.7 if proposed_fix else 0.8

                card = await self.db.create_card(card)
                agent.cards_created.append(card.id)

        except Exception as e:
            agent.add_message("system", f"Error during analysis: {str(e)}")
            agent.update_status(AgentStatus.ERROR)

    async def _run_subsystem_analysis(self, agent: Agent, subsystem_info: SubsystemInfo):
        """
        Run AI-powered analysis on a subsystem (directory/package).
        Coordinates findings from child subsystems and modules.
        """
        start_time = time.time()

        # Collect child findings from all child agents
        child_findings = []
        for child_id in agent.children_ids:
            child_agent = await self.db.get_agent(child_id)
            if child_agent:
                child_findings.extend(child_agent.findings)

        # Count modules and classes in this subsystem
        num_modules = len(subsystem_info.modules)
        num_subsystems = len(subsystem_info.subsystems)
        total_classes = sum(len(m.classes) for m in subsystem_info.modules)
        total_functions = sum(
            len(m.functions) + sum(len(c.methods) for c in m.classes)
            for m in subsystem_info.modules
        )

        context = f"""You are analyzing a subsystem (package/directory) in a Python codebase.

Subsystem: {subsystem_info.name}
Directory: {subsystem_info.directory}
Nested subsystems: {num_subsystems}
Modules: {num_modules}
Classes: {total_classes}
Functions: {total_functions}

Key findings from child agents (modules/subsystems):
{chr(10).join(f'- {f}' for f in child_findings[:15])}  # Limit to first 15

Provide a subsystem-level assessment focusing on:
1. Package cohesion and organization
2. Inter-module dependencies and coupling
3. Architectural patterns and violations
4. API design and boundaries
5. Cross-cutting concerns

Be concise and focus on subsystem-level patterns."""

        agent.add_message("user", context)

        try:
            response = await self._call_ai_with_resilience(
                max_tokens=1536,
                messages=[{"role": "user", "content": context}],
                estimated_tokens=2000
            )

            analysis = response.content
            tokens_in = response.input_tokens
            tokens_out = response.output_tokens

            latency = (time.time() - start_time) * 1000
            agent.add_message("assistant", analysis, tokens_in, tokens_out, latency_ms=latency)

            findings = [line.strip() for line in analysis.split('\n') if line.strip().startswith('-')]
            agent.findings.extend(findings)

            # Create subsystem-level card
            if findings:
                card = Card(
                    id="",
                    type=CardType.ARCHITECTURE,
                    title=f"Subsystem Review: {subsystem_info.name}",
                    summary=analysis,
                    owner_agent=agent.id,
                    status=CardStatus.NEW
                )
                card.links.code.append(subsystem_info.directory)

                card = await self.db.create_card(card)
                agent.cards_created.append(card.id)

        except Exception as e:
            agent.add_message("system", f"Error during subsystem analysis: {str(e)}")
            agent.update_status(AgentStatus.ERROR)

    async def _run_module_analysis(self, agent: Agent, module_info: ModuleInfo, child_agents: List[Agent]):
        """Run AI-powered analysis on a module"""
        start_time = time.time()

        # Collect child findings
        child_findings = []
        for child in child_agents:
            child_findings.extend(child.findings)

        # Detect code smells
        smells = self.analyzer.detect_code_smells(module_info)

        summary = self.analyzer.generate_summary(module_info)

        context = f"""You are analyzing a Python module as part of a hierarchical code review.

{summary}

Function-level findings from child agents:
{chr(10).join(f'- {f}' for f in child_findings[:10])}  # Limit to first 10

Code smells detected:
{chr(10).join(f'- {s["message"]} ({s["severity"]})' for s in smells)}

Provide a module-level assessment:
1. Overall code quality
2. Architectural concerns
3. Key refactoring opportunities
4. Integration issues

Be concise and focus on high-level patterns."""

        agent.add_message("user", context)

        try:
            response = await self._call_ai_with_resilience(
                max_tokens=1024,
                messages=[{"role": "user", "content": context}],
                estimated_tokens=1500
            )

            analysis = response.content
            tokens_in = response.input_tokens
            tokens_out = response.output_tokens

            latency = (time.time() - start_time) * 1000
            agent.add_message("assistant", analysis, tokens_in, tokens_out, latency_ms=latency)

            findings = [line.strip() for line in analysis.split('\n') if line.strip().startswith('-')]
            agent.findings.extend(findings)

            # Create module-level card
            if findings or smells:
                card = Card(
                    id="",
                    type=CardType.REVIEW,
                    title=f"Module Review: {Path(module_info.file_path).name}",
                    summary=f"## AI Analysis\n\n{analysis}\n\n## Code Smells\n\n" +
                           '\n'.join(f"- {s['message']}" for s in smells),
                    owner_agent=agent.id,
                    status=CardStatus.NEW
                )
                card.links.code.append(module_info.file_path)

                card = await self.db.create_card(card)
                agent.cards_created.append(card.id)

        except Exception as e:
            agent.add_message("system", f"Error during analysis: {str(e)}")
            agent.update_status(AgentStatus.ERROR)

    async def _run_class_analysis(
        self,
        agent: Agent,
        module_info: ModuleInfo,
        class_info: Any,
        method_agents: List[Agent]
    ):
        """
        Run AI-powered analysis on a class.
        Focuses on class-level design patterns, SOLID principles, and cohesion.
        """
        start_time = time.time()

        # Collect method findings
        method_findings = []
        for method_agent in method_agents:
            method_findings.extend(method_agent.findings)

        # Read class source code
        with open(module_info.file_path, 'r') as f:
            lines = f.readlines()
            class_source = ''.join(lines[class_info.line_start - 1:class_info.line_end])

        context = f"""You are analyzing a Python class as part of a hierarchical code review.

File: {module_info.file_path}
Class: {class_info.name}
Base classes: {', '.join(class_info.bases) if class_info.bases else 'None'}
Methods: {len(class_info.methods)}
Lines: {class_info.line_start}-{class_info.line_end}

Class source:
```python
{class_source[:2000]}  # Limit to first 2000 chars
```

Method-level findings:
{chr(10).join(f'- {f}' for f in method_findings[:10])}  # Limit to first 10

Provide a class-level assessment focusing on:
1. SOLID principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion)
2. Class cohesion - do methods work together toward a single purpose?
3. Design patterns used or misused
4. Encapsulation and information hiding
5. Class size and complexity (should it be split?)

Be concise and focus on architectural/design issues."""

        agent.add_message("user", context)

        try:
            response = await self._call_ai_with_resilience(
                max_tokens=1536,
                messages=[{"role": "user", "content": context}],
                estimated_tokens=2000
            )

            analysis = response.content
            tokens_in = response.input_tokens
            tokens_out = response.output_tokens

            latency = (time.time() - start_time) * 1000
            agent.add_message("assistant", analysis, tokens_in, tokens_out, latency_ms=latency)

            findings = [line.strip() for line in analysis.split('\n') if line.strip().startswith('-')]
            agent.findings.extend(findings)

            # Create class-level card
            if findings:
                card = Card(
                    id="",
                    type=CardType.REVIEW,
                    title=f"Class Review: {class_info.name}",
                    summary=analysis,
                    owner_agent=agent.id,
                    status=CardStatus.NEW
                )
                card.links.code.append(f"{module_info.file_path}:{class_info.line_start}")

                card = await self.db.create_card(card)
                agent.cards_created.append(card.id)

        except Exception as e:
            agent.add_message("system", f"Error during class analysis: {str(e)}")
            agent.update_status(AgentStatus.ERROR)

    async def _run_system_analysis(self, agent: Agent, modules: List[ModuleInfo]):
        """Run system-level analysis"""
        start_time = time.time()

        # Get all module agents
        module_agents = []
        for agent_id in agent.children_ids:
            module_agent = await self.db.get_agent(agent_id)
            if module_agent:
                module_agents.append(module_agent)

        # Aggregate findings
        all_findings = []
        for module_agent in module_agents:
            all_findings.extend(module_agent.findings)

        context = f"""You are conducting a system-level code review of a Python codebase.

Total modules: {len(modules)}
Total lines of code: {sum(m.lines_of_code for m in modules)}

Key findings from module-level agents:
{chr(10).join(f'- {f}' for f in all_findings[:20])}  # Top 20 findings

Provide a system-level assessment:
1. Overall architecture quality
2. Critical issues requiring immediate attention
3. Strategic refactoring recommendations
4. Code health score (0-100)

Focus on the big picture and prioritize actionable insights."""

        agent.add_message("user", context)

        try:
            response = await self._call_ai_with_resilience(
                max_tokens=2048,
                messages=[{"role": "user", "content": context}],
                estimated_tokens=2500
            )

            analysis = response.content
            tokens_in = response.input_tokens
            tokens_out = response.output_tokens

            latency = (time.time() - start_time) * 1000
            agent.add_message("assistant", analysis, tokens_in, tokens_out, latency_ms=latency)

            findings = [line.strip() for line in analysis.split('\n') if line.strip().startswith('-')]
            agent.findings.extend(findings)

            # Create system-level card
            card = Card(
                id="",
                type=CardType.ARCHITECTURE,
                title="System-Level Code Review",
                summary=analysis,
                owner_agent=agent.id,
                status=CardStatus.PROPOSED,
                priority="P1"
            )

            card = await self.db.create_card(card)
            agent.cards_created.append(card.id)

        except Exception as e:
            agent.add_message("system", f"Error during analysis: {str(e)}")
            agent.update_status(AgentStatus.ERROR)

    def _extract_proposed_fix(self, analysis: str, module_info: ModuleInfo,
                             func_info: Any, original_code: str) -> Optional[ProposedFix]:
        """Extract and validate a proposed fix from the AI's analysis"""
        import re
        import ast as python_ast

        # Try to find code blocks in the response
        code_blocks = re.findall(r'```python\n(.*?)```', analysis, re.DOTALL)

        if not code_blocks:
            return None

        # Take the first code block as the proposed fix
        fixed_code = code_blocks[0].strip()

        # Extract explanation from the analysis
        explanation_parts = []
        current_section = None

        for line in analysis.split('\n'):
            if line.startswith('**Problem:**'):
                current_section = 'problem'
                explanation_parts.append(line)
            elif line.startswith('**Fix:**'):
                current_section = 'fix'
            elif current_section == 'problem' and line.strip():
                explanation_parts.append(line)

        explanation = '\n'.join(explanation_parts) if explanation_parts else analysis[:500]

        # Validate the proposed fix with AST
        validation_errors = []
        validated = False

        try:
            python_ast.parse(fixed_code)
            validated = True
        except SyntaxError as e:
            validation_errors.append(f"Syntax error: {str(e)}")

        # Create ProposedFix object
        proposed_fix = ProposedFix(
            original_code=original_code,
            fixed_code=fixed_code,
            explanation=explanation,
            file_path=module_info.file_path,
            line_start=func_info.line_start,
            line_end=func_info.line_end,
            confidence=0.75,
            validated=validated,
            validation_errors=validation_errors
        )

        return proposed_fix

    async def get_agent_hierarchy(self, root_agent_id: str) -> Dict[str, Any]:
        """Get the full agent hierarchy as a tree"""
        root = await self.db.get_agent(root_agent_id)
        if not root:
            return {}

        async def build_tree(agent: Agent) -> Dict[str, Any]:
            children = []
            for child_id in agent.children_ids:
                child = await self.db.get_agent(child_id)
                if child:
                    children.append(await build_tree(child))

            return {
                "id": agent.id,
                "scope": agent.scope,
                "target": agent.target,
                "status": agent.status,
                "findings_count": len(agent.findings),
                "cards_count": len(agent.cards_created),
                "children": children
            }

        return await build_tree(root)

    def get_progress(self) -> Dict[str, Any]:
        """Get current analysis progress"""
        return {
            **self.progress,
            'percentage': round(
                (self.progress['completed_functions'] / self.progress['total_functions'] * 100)
                if self.progress['total_functions'] > 0 else 0
            )
        }

    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache:
            return {
                'enabled': False,
                'total_entries': 0,
                'total_size_bytes': 0,
                'hit_rate': 0.0
            }

        stats = await self.cache.get_statistics()
        return {
            'enabled': True,
            'total_entries': stats.total_entries,
            'total_size_bytes': stats.total_size_bytes,
            'total_size_mb': round(stats.total_size_bytes / (1024 * 1024), 2),
            'session_hits': stats.hits,
            'session_misses': stats.misses,
            'hit_rate': round(stats.hit_rate, 1),
            'oldest_entry': stats.oldest_entry,
            'newest_entry': stats.newest_entry,
            'most_accessed_file': stats.most_accessed_file
        }

    async def clear_cache(self) -> int:
        """Clear the analysis cache"""
        if not self.cache:
            return 0
        return await self.cache.clear_all()

    async def invalidate_file_cache(self, file_path: str) -> int:
        """Invalidate cache for a specific file"""
        if not self.cache:
            return 0
        return await self.cache.invalidate_file(file_path)
