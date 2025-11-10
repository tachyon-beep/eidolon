"""FunctionAgent analyzes individual functions for bugs."""

from datetime import datetime
from typing import Optional

from ..llm.client import LLMClient
from .base import Agent, Scope
from .models import Analysis, Finding
from .static_checks import StaticAnalyzer


class FunctionAgent(Agent):
    """Analyzes a single function for bugs, performance, and security issues."""

    def __init__(
        self,
        function_id: str,
        function_name: str,
        source_code: str,
        file_path: str,
        memory_store: "MemoryStore",
        llm: Optional[LLMClient] = None,
        commit_sha: Optional[str] = None,
    ):
        """Initialize function agent.

        Args:
            function_id: Unique identifier (e.g., "auth.login.validate_token")
            function_name: Name of the function
            source_code: Complete source code (file or module containing function)
            file_path: Path to file
            memory_store: Storage for persistent memory
            llm: Optional LLM client for deep analysis
            commit_sha: Git commit SHA (for change tracking)
        """
        super().__init__(
            agent_id=f"function:{function_id}",
            scope=Scope(type="function", id=function_id, path=file_path),
            memory_store=memory_store,
        )
        self.function_name = function_name
        self.source_code = source_code
        self.file_path = file_path
        self.llm = llm
        self.commit_sha = commit_sha or "unknown"

    async def analyze(self) -> list[Finding]:
        """Analyze the function for issues.

        Returns:
            List of findings
        """
        findings = []

        # Check if we've analyzed this code before
        previous = await self.memory.get_analyses(commit_sha=self.commit_sha)

        # Step 1: Static analysis
        static_findings = self._run_static_checks()
        findings.extend(static_findings)

        # Step 2: LLM deep analysis (if available)
        if self.llm:
            llm_findings = await self._llm_analyze(previous)
            findings.extend(llm_findings)

        # Tag all findings with this agent
        for finding in findings:
            finding.agent_id = self.agent_id

        # Record this analysis
        analysis = Analysis(
            timestamp=datetime.utcnow(),
            commit_sha=self.commit_sha,
            trigger="audit",
            findings=findings,
            reasoning=self._build_reasoning(findings, static_findings, previous),
            confidence=self._calculate_confidence(findings, static_findings),
            metadata={
                "function_name": self.function_name,
                "file_path": self.file_path,
                "static_checks": len(static_findings),
                "llm_checks": len(findings) - len(static_findings),
            },
        )

        await self.memory.record_analysis(analysis)
        self.findings = findings

        return findings

    def _run_static_checks(self) -> list[Finding]:
        """Run static analysis checks.

        Returns:
            List of findings from static analysis
        """
        analyzer = StaticAnalyzer(self.source_code, self.file_path)

        if analyzer.tree is None:
            return [
                Finding(
                    location=f"{self.file_path}:1",
                    severity="critical",
                    type="bug",
                    description="Syntax error prevents analysis",
                )
            ]

        # Find the function node
        import ast

        for node in ast.walk(analyzer.tree):
            if isinstance(node, ast.FunctionDef) and node.name == self.function_name:
                return analyzer.analyze_function(node)

        return []

    async def _llm_analyze(
        self, previous_analyses: list["AnalysisRecord"]
    ) -> list[Finding]:
        """Use LLM for deep reasoning about the function.

        Args:
            previous_analyses: Past analyses (for context)

        Returns:
            List of findings from LLM
        """
        # Build prompt with context
        prompt = self._build_llm_prompt(previous_analyses)

        # Call LLM with caching
        cache_key = self.llm.make_cache_key(
            self.function_name, self.commit_sha, self.source_code[:200]
        )

        try:
            response = await self.llm.complete(
                prompt=prompt, json_mode=True, cache_key=cache_key
            )

            # Parse findings from LLM response
            return self._parse_llm_findings(response)

        except Exception as e:
            # If LLM fails, return a finding about the failure
            return [
                Finding(
                    location=f"{self.file_path}:1",
                    severity="info",
                    type="architecture",
                    description=f"LLM analysis failed: {str(e)}",
                )
            ]

    def _build_llm_prompt(self, previous_analyses: list["AnalysisRecord"]) -> str:
        """Build prompt for LLM analysis.

        Args:
            previous_analyses: Past analyses for context

        Returns:
            Prompt string
        """
        prompt = f"""Analyze this Python function for potential bugs, security issues, and logic errors.

Function: {self.function_name}
File: {self.file_path}

Code:
```python
{self.source_code}
```

Focus on:
1. Logic errors (off-by-one, wrong comparisons, edge cases)
2. Security issues (injection, validation, authentication)
3. Race conditions or concurrency issues
4. Error handling gaps
5. Data validation issues

"""

        # Add context from previous analyses
        if previous_analyses:
            prompt += f"\nNote: I previously analyzed this function {len(previous_analyses)} time(s).\n"
            if len(previous_analyses) > 0:
                latest = previous_analyses[0]
                prompt += f"Last analysis found {len(latest.findings)} issues.\n"

        prompt += """
Return a JSON array of findings:
[
  {
    "line": <line_number>,
    "severity": "critical" | "high" | "medium" | "low",
    "type": "bug" | "security" | "performance" | "architecture",
    "description": "Clear description of the issue",
    "suggested_fix": "How to fix it"
  }
]

If no issues found, return empty array: []
"""

        return prompt

    def _parse_llm_findings(self, response: dict | str) -> list[Finding]:
        """Parse LLM response into Finding objects.

        Args:
            response: LLM response (JSON or string)

        Returns:
            List of findings
        """
        findings = []

        # Handle both dict and list responses
        if isinstance(response, str):
            return []

        items = response if isinstance(response, list) else response.get("findings", [])

        for item in items:
            try:
                line = item.get("line", 1)
                findings.append(
                    Finding(
                        location=f"{self.file_path}:{line}",
                        severity=item.get("severity", "medium"),
                        type=item.get("type", "bug"),
                        description=item["description"],
                        suggested_fix=item.get("suggested_fix"),
                    )
                )
            except (KeyError, TypeError):
                # Skip malformed findings
                continue

        return findings

    def _build_reasoning(
        self,
        all_findings: list[Finding],
        static_findings: list[Finding],
        previous_analyses: list["AnalysisRecord"],
    ) -> str:
        """Build reasoning explanation for this analysis.

        Args:
            all_findings: All findings (static + LLM)
            static_findings: Just static findings
            previous_analyses: Past analyses

        Returns:
            Reasoning text
        """
        parts = [
            f"Analyzed function '{self.function_name}' in {self.file_path}.",
            f"Static analysis found {len(static_findings)} issues.",
        ]

        llm_count = len(all_findings) - len(static_findings)
        if llm_count > 0:
            parts.append(f"Deep LLM analysis found {llm_count} additional issues.")

        if previous_analyses:
            parts.append(
                f"This is analysis #{len(previous_analyses) + 1} for this code."
            )

        if not all_findings:
            parts.append("No issues found - function appears correct.")

        return " ".join(parts)

    def _calculate_confidence(
        self, all_findings: list[Finding], static_findings: list[Finding]
    ) -> float:
        """Calculate confidence score for this analysis.

        Args:
            all_findings: All findings
            static_findings: Static findings (high confidence)

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not all_findings:
            # No findings - high confidence it's correct
            return 0.95

        # Static findings have high confidence
        static_ratio = len(static_findings) / len(all_findings)

        # Base confidence + bonus for static checks
        base = 0.7
        static_bonus = static_ratio * 0.2

        return min(base + static_bonus, 0.95)
