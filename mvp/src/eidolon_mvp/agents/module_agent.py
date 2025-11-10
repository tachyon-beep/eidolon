"""ModuleAgent coordinates FunctionAgents to analyze entire modules."""

import ast
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..llm.client import LLMClient
from .base import Agent, Scope
from .function_agent import FunctionAgent
from .models import Analysis, Finding, Report
from .parallel import ParallelExecutor, ProgressTracker


class ModuleAgent(Agent):
    """Analyzes a Python module by coordinating FunctionAgents."""

    def __init__(
        self,
        module_path: str,
        source_code: str,
        memory_store: "MemoryStore",
        llm: Optional[LLMClient] = None,
        commit_sha: Optional[str] = None,
        max_concurrent: int = 10,
    ):
        """Initialize module agent.

        Args:
            module_path: Path to module file
            source_code: Complete module source code
            memory_store: Storage for persistent memory
            llm: Optional LLM client for deep analysis
            commit_sha: Git commit SHA
            max_concurrent: Max concurrent function agents
        """
        super().__init__(
            agent_id=f"module:{module_path}",
            scope=Scope(type="module", path=module_path),
            memory_store=memory_store,
        )
        self.module_path = module_path
        self.source_code = source_code
        self.llm = llm
        self.commit_sha = commit_sha or "unknown"
        self.function_agents: list[FunctionAgent] = []
        self.executor = ParallelExecutor(max_concurrent=max_concurrent)

    async def analyze(self) -> list[Finding]:
        """Analyze the module by coordinating function agents.

        Returns:
            List of all findings from module and functions
        """
        findings = []

        # Parse module to find functions
        functions = self._extract_functions()
        print(f"Module {self.module_path}: found {len(functions)} functions")

        # Spawn FunctionAgent for each function
        self.function_agents = []
        for func_name, func_node in functions:
            function_id = self._make_function_id(func_name)

            agent = FunctionAgent(
                function_id=function_id,
                function_name=func_name,
                source_code=self.source_code,
                file_path=self.module_path,
                memory_store=self.memory.store,
                llm=self.llm,
                commit_sha=self.commit_sha,
            )

            # Ensure function agent exists in DB
            await self.memory.store.ensure_agent_exists(
                agent.agent_id,
                "function",
                {"function_name": func_name, "module": self.module_path},
            )

            self.function_agents.append(agent)

        # Record hierarchy
        await self._record_hierarchy()

        # Run all function agents in parallel
        print(f"Analyzing {len(self.function_agents)} functions in parallel...")
        tracker = ProgressTracker(total=len(self.function_agents), verbose=True)

        results = await self.executor.execute_all(
            agents=self.function_agents,
            operation=lambda agent: agent.analyze(),
            on_progress=tracker.update,
        )

        tracker.finish()

        # Aggregate findings
        for agent, result in results:
            if isinstance(result, Exception):
                tracker.record_error(agent.agent_id, result)
                # Add error as finding
                findings.append(
                    Finding(
                        location=f"{self.module_path}:1",
                        severity="high",
                        type="bug",
                        description=f"Analysis failed for {agent.function_name}: {result}",
                        agent_id=self.agent_id,
                    )
                )
            else:
                # result is list of findings
                findings.extend(result)

        # Module-level architecture checks
        module_findings = self._check_module_architecture()
        findings.extend(module_findings)

        # Record this analysis
        analysis = Analysis(
            timestamp=datetime.utcnow(),
            commit_sha=self.commit_sha,
            trigger="audit",
            findings=findings,
            reasoning=self._build_reasoning(findings, len(functions)),
            confidence=self._calculate_confidence(findings, len(tracker.errors)),
            metadata={
                "module_path": self.module_path,
                "function_count": len(functions),
                "functions_with_issues": sum(
                    1 for _, r in results if isinstance(r, list) and len(r) > 0
                ),
                "failed_analyses": len(tracker.errors),
            },
        )

        await self.memory.record_analysis(analysis)
        self.findings = findings

        return findings

    def _extract_functions(self) -> list[tuple[str, ast.FunctionDef]]:
        """Extract all function definitions from module.

        Returns:
            List of (function_name, function_node) tuples
        """
        try:
            tree = ast.parse(self.source_code)
        except SyntaxError:
            return []

        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Only top-level functions (not nested)
                if self._is_top_level_function(tree, node):
                    functions.append((node.name, node))

        return functions

    def _is_top_level_function(
        self, tree: ast.Module, func_node: ast.FunctionDef
    ) -> bool:
        """Check if function is at module level (not nested in class/function).

        Args:
            tree: Module AST
            func_node: Function node to check

        Returns:
            True if top-level function
        """
        # Simple heuristic: check if it's directly in module body
        return func_node in tree.body

    def _make_function_id(self, func_name: str) -> str:
        """Generate function ID from module path and function name.

        Args:
            func_name: Function name

        Returns:
            Function ID (e.g., "src.auth.login.validate_token")
        """
        # Convert file path to module-like ID
        path = Path(self.module_path)
        parts = []

        # Remove .py extension
        if path.suffix == ".py":
            parts.append(path.stem)
        else:
            parts.append(path.name)

        # Add function name
        parts.append(func_name)

        return ".".join(parts)

    def _check_module_architecture(self) -> list[Finding]:
        """Check module-level architecture issues.

        Returns:
            List of findings
        """
        findings = []

        # Check module length
        line_count = len(self.source_code.split("\n"))
        if line_count > 1000:
            findings.append(
                Finding(
                    location=f"{self.module_path}:1",
                    severity="medium",
                    type="architecture",
                    description=f"Module is very long ({line_count} lines). "
                    f"Consider splitting into smaller modules.",
                    agent_id=self.agent_id,
                )
            )

        # Check for missing docstring
        try:
            tree = ast.parse(self.source_code)
            has_docstring = (
                isinstance(tree.body[0], ast.Expr)
                and isinstance(tree.body[0].value, ast.Constant)
                and isinstance(tree.body[0].value.value, str)
            )

            if not has_docstring:
                findings.append(
                    Finding(
                        location=f"{self.module_path}:1",
                        severity="low",
                        type="style",
                        description="Module missing docstring",
                        suggested_fix="Add module-level docstring explaining purpose",
                        agent_id=self.agent_id,
                    )
                )
        except (SyntaxError, IndexError):
            pass

        # Check imports (basic checks)
        findings.extend(self._check_imports())

        return findings

    def _check_imports(self) -> list[Finding]:
        """Check import statements for issues.

        Returns:
            List of findings
        """
        findings = []

        try:
            tree = ast.parse(self.source_code)

            # Check for wildcard imports
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        if alias.name == "*":
                            findings.append(
                                Finding(
                                    location=f"{self.module_path}:{node.lineno}",
                                    severity="medium",
                                    type="style",
                                    description=f"Wildcard import from {node.module}. "
                                    f"Makes code harder to understand.",
                                    suggested_fix="Import specific names instead",
                                    agent_id=self.agent_id,
                                )
                            )

        except SyntaxError:
            pass

        return findings

    async def _record_hierarchy(self):
        """Record parent-child relationships in database."""
        # Record that this module coordinates its functions
        for func_agent in self.function_agents:
            try:
                await self.memory.store.pool.connection().__aenter__().execute(
                    """
                    INSERT INTO agent_hierarchy (parent_agent_id, child_agent_id, relationship_type)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (self.agent_id, func_agent.agent_id, "coordinates"),
                )
            except:
                # Hierarchy tracking is non-critical
                pass

    def report(self) -> Report:
        """Generate hierarchical report.

        Returns:
            Report with module and function findings
        """
        # Get reports from all function agents
        child_reports = [agent.report() for agent in self.function_agents]

        return Report(
            agent_id=self.agent_id,
            scope=self.scope,
            findings=self.findings,
            summary=self._build_summary(),
            children=child_reports,
            metadata={
                "module_path": self.module_path,
                "function_count": len(self.function_agents),
                "total_findings": sum(len(r.findings) for r in child_reports)
                + len(self.findings),
            },
        )

    def _build_reasoning(self, findings: list[Finding], function_count: int) -> str:
        """Build reasoning for module analysis.

        Args:
            findings: All findings
            function_count: Number of functions analyzed

        Returns:
            Reasoning text
        """
        parts = [
            f"Analyzed module {self.module_path} with {function_count} functions.",
        ]

        if function_count > 0:
            functions_with_issues = len(
                [agent for agent in self.function_agents if len(agent.findings) > 0]
            )
            parts.append(
                f"{functions_with_issues}/{function_count} functions have issues."
            )

        module_findings = [f for f in findings if f.agent_id == self.agent_id]
        if module_findings:
            parts.append(f"Found {len(module_findings)} module-level issues.")

        if not findings:
            parts.append("No issues found - module looks good!")

        return " ".join(parts)

    def _calculate_confidence(self, findings: list[Finding], error_count: int) -> float:
        """Calculate confidence score.

        Args:
            findings: All findings
            error_count: Number of failed analyses

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if error_count > 0:
            # Lower confidence if some analyses failed
            return max(0.5, 0.9 - (error_count * 0.1))

        if not findings:
            return 0.9

        # More findings = slightly lower confidence
        return max(0.7, 0.9 - (len(findings) * 0.01))

    def _build_summary(self) -> str:
        """Build summary including child agents."""
        module_findings = [f for f in self.findings if f.agent_id == self.agent_id]
        function_findings = [f for f in self.findings if f.agent_id != self.agent_id]

        parts = [
            f"Module: {len(module_findings)} issues",
            f"Functions: {len(function_findings)} issues across {len(self.function_agents)} functions",
        ]

        return ", ".join(parts)
