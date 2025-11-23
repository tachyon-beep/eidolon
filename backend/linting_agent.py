"""
Specialist Linting Agents - Phase 6

Sits between code generation (Tier 4) and file writing (Tier 5) as Tier 4.5.

Responsibilities:
1. Run linters on generated code (ruff, mypy, etc.)
2. Categorize errors by severity
3. Auto-fix simple issues with ruff --fix
4. Use LLM to fix complex issues that can't be auto-fixed
5. Ensure Python 3.12+ compatibility
6. Track what was fixed

Flow:
  Code Generated (Tier 4)
    ↓
  Linting Agent (Tier 4.5 - Phase 6)
    - Run ruff for style/errors
    - Run mypy for type checking
    - Auto-fix simple issues
    - LLM fixes complex issues
    ↓
  Write to Disk (Tier 5)

This ensures all code is clean, type-safe, and Py 3.12+ compatible!
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import json
import tempfile

from llm_providers import LLMProvider
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class LintIssue:
    """A single linting issue"""
    tool: str  # "ruff", "mypy", etc.
    severity: str  # "error", "warning", "info"
    code: str  # Error code (e.g., "E501", "F401")
    message: str
    line: int
    column: int
    fixable: bool  # Can ruff auto-fix this?


@dataclass
class LintingResult:
    """Result of linting pass"""
    success: bool
    original_code: str
    fixed_code: str

    # Issues found
    total_issues: int = 0
    errors: int = 0
    warnings: int = 0

    # Fixes applied
    auto_fixed: int = 0  # Fixed by ruff --fix
    llm_fixed: int = 0   # Fixed by LLM
    unfixed: int = 0     # Couldn't fix

    # Details
    issues_found: List[LintIssue] = field(default_factory=list)
    fixes_applied: List[str] = field(default_factory=list)

    # Metadata
    linters_run: List[str] = field(default_factory=list)
    llm_turns_used: int = 0


class LintingAgent:
    """
    Phase 6: Specialist Linting Agent

    Runs linters and fixes code quality issues automatically.
    Ensures Python 3.12+ compatibility and best practices.
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        use_ruff: bool = True,
        use_mypy: bool = True,
        use_llm_fixes: bool = True,
        target_python_version: str = "3.12"
    ):
        """
        Initialize Linting Agent

        Args:
            llm_provider: LLM provider for complex fixes
            use_ruff: Use ruff linter (recommended)
            use_mypy: Use mypy type checker
            use_llm_fixes: Use LLM to fix complex issues
            target_python_version: Target Python version (default: 3.12)
        """
        self.llm_provider = llm_provider
        self.use_ruff = use_ruff
        self.use_mypy = use_mypy
        self.use_llm_fixes = use_llm_fixes
        self.target_python_version = target_python_version

        # Check if tools are available
        self.ruff_available = self._check_tool_available("ruff")
        self.mypy_available = self._check_tool_available("mypy")

        if use_ruff and not self.ruff_available:
            logger.warning("ruff not available - install with: pip install ruff")
        if use_mypy and not self.mypy_available:
            logger.warning("mypy not available - install with: pip install mypy")

    def _check_tool_available(self, tool: str) -> bool:
        """Check if a linting tool is installed"""
        try:
            subprocess.run(
                [tool, "--version"],
                capture_output=True,
                timeout=5
            )
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def lint_and_fix(
        self,
        code: str,
        filename: str = "temp.py",
        context: Optional[Dict[str, Any]] = None
    ) -> LintingResult:
        """
        Lint code and apply fixes

        Args:
            code: Python code to lint
            filename: Filename (for context)
            context: Additional context

        Returns:
            LintingResult with fixed code and metadata
        """
        context = context or {}

        logger.info("linting_started", filename=filename, code_length=len(code))

        result = LintingResult(
            success=False,
            original_code=code,
            fixed_code=code
        )

        current_code = code

        # Step 1: Run ruff and auto-fix
        if self.use_ruff and self.ruff_available:
            current_code, ruff_result = await self._run_ruff(current_code, filename)
            result.linters_run.append("ruff")
            result.issues_found.extend(ruff_result["issues"])
            result.auto_fixed += ruff_result["auto_fixed"]
            result.fixes_applied.extend(ruff_result["fixes"])

        # Step 2: Run mypy for type checking
        if self.use_mypy and self.mypy_available:
            mypy_result = await self._run_mypy(current_code, filename)
            result.linters_run.append("mypy")
            result.issues_found.extend(mypy_result["issues"])

        # Step 3: Use LLM to fix remaining complex issues
        if self.use_llm_fixes and self.llm_provider:
            remaining_issues = [
                issue for issue in result.issues_found
                if issue.severity == "error" and not issue.fixable
            ]

            if remaining_issues:
                current_code, llm_result = await self._llm_fix_issues(
                    current_code,
                    remaining_issues,
                    filename
                )
                result.llm_fixed = llm_result["fixed_count"]
                result.llm_turns_used = llm_result["turns_used"]
                result.fixes_applied.extend(llm_result["fixes"])

        # Final validation - re-run linters to confirm
        if self.ruff_available:
            final_issues = await self._check_ruff(current_code, filename)
            result.total_issues = len(final_issues)
            result.errors = len([i for i in final_issues if i.severity == "error"])
            result.warnings = len([i for i in final_issues if i.severity == "warning"])
        else:
            # Count from initial scan
            result.total_issues = len(result.issues_found)
            result.errors = len([i for i in result.issues_found if i.severity == "error"])
            result.warnings = len([i for i in result.issues_found if i.severity == "warning"])

        result.unfixed = result.errors  # Remaining errors
        result.fixed_code = current_code
        result.success = result.errors == 0

        logger.info(
            "linting_complete",
            filename=filename,
            success=result.success,
            total_issues=result.total_issues,
            auto_fixed=result.auto_fixed,
            llm_fixed=result.llm_fixed,
            unfixed=result.unfixed
        )

        return result

    async def _run_ruff(
        self,
        code: str,
        filename: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Run ruff linter and auto-fix"""

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Run ruff check with JSON output
            check_result = subprocess.run(
                [
                    "ruff", "check",
                    temp_path,
                    "--output-format=json",
                    f"--target-version=py{self.target_python_version.replace('.', '')}"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            issues = []
            if check_result.stdout:
                try:
                    ruff_output = json.loads(check_result.stdout)
                    for item in ruff_output:
                        issues.append(LintIssue(
                            tool="ruff",
                            severity="error" if item.get("code", "").startswith("E") else "warning",
                            code=item.get("code", ""),
                            message=item.get("message", ""),
                            line=item.get("location", {}).get("row", 0),
                            column=item.get("location", {}).get("column", 0),
                            fixable=item.get("fix", {}).get("applicability") == "safe"
                        ))
                except json.JSONDecodeError:
                    logger.warning("Failed to parse ruff JSON output")

            # Run ruff fix to auto-fix
            fix_result = subprocess.run(
                [
                    "ruff", "check",
                    temp_path,
                    "--fix",
                    f"--target-version=py{self.target_python_version.replace('.', '')}"
                ],
                capture_output=True,
                timeout=30
            )

            # Read fixed code
            with open(temp_path, 'r') as f:
                fixed_code = f.read()

            auto_fixed = len([i for i in issues if i.fixable])
            fixes = [f"ruff auto-fixed {i.code}: {i.message}" for i in issues if i.fixable]

            return fixed_code, {
                "issues": issues,
                "auto_fixed": auto_fixed,
                "fixes": fixes
            }

        finally:
            # Clean up temp file
            Path(temp_path).unlink(missing_ok=True)

    async def _check_ruff(self, code: str, filename: str) -> List[LintIssue]:
        """Check code with ruff (no fixing)"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                [
                    "ruff", "check",
                    temp_path,
                    "--output-format=json",
                    f"--target-version=py{self.target_python_version.replace('.', '')}"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            issues = []
            if result.stdout:
                try:
                    ruff_output = json.loads(result.stdout)
                    for item in ruff_output:
                        issues.append(LintIssue(
                            tool="ruff",
                            severity="error" if item.get("code", "").startswith("E") else "warning",
                            code=item.get("code", ""),
                            message=item.get("message", ""),
                            line=item.get("location", {}).get("row", 0),
                            column=item.get("location", {}).get("column", 0),
                            fixable=item.get("fix", {}).get("applicability") == "safe"
                        ))
                except json.JSONDecodeError:
                    pass

            return issues

        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def _run_mypy(self, code: str, filename: str) -> Dict[str, Any]:
        """Run mypy type checker"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            result = subprocess.run(
                [
                    "mypy",
                    temp_path,
                    "--python-version", self.target_python_version,
                    "--no-error-summary"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            issues = []
            if result.stdout:
                # Parse mypy output (line:col: error: message)
                for line in result.stdout.split('\n'):
                    if ':' in line and 'error:' in line:
                        parts = line.split(':')
                        if len(parts) >= 4:
                            try:
                                line_num = int(parts[1].strip())
                                message = ':'.join(parts[3:]).strip()
                                issues.append(LintIssue(
                                    tool="mypy",
                                    severity="error",
                                    code="type-error",
                                    message=message,
                                    line=line_num,
                                    column=0,
                                    fixable=False  # mypy issues need manual fixing
                                ))
                            except ValueError:
                                pass

            return {"issues": issues}

        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def _llm_fix_issues(
        self,
        code: str,
        issues: List[LintIssue],
        filename: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Use LLM to fix complex linting issues"""

        if not self.llm_provider or not issues:
            return code, {"fixed_count": 0, "turns_used": 0, "fixes": []}

        # Build prompt with issues
        system_prompt = f"""You are a Python code linting expert specializing in Python {self.target_python_version}+.

Your task is to fix linting errors in Python code while preserving functionality.

Rules:
1. Fix ONLY the specific errors mentioned
2. Preserve all functionality
3. Follow Python {self.target_python_version}+ best practices
4. Use modern Python features when appropriate
5. Maintain code style and formatting
6. Return the complete fixed code in JSON format

Output JSON with:
{{
  "fixed_code": "complete fixed code here",
  "fixes_applied": ["description of fix 1", "description of fix 2"]
}}"""

        # List issues
        issues_desc = "\n".join([
            f"Line {i.line}: [{i.tool}/{i.code}] {i.message}"
            for i in issues
        ])

        user_prompt = f"""Fix the following linting errors in this Python code:

**Errors to fix:**
{issues_desc}

**Code to fix:**
```python
{code}
```

Return the fixed code in JSON format."""

        try:
            response = await self.llm_provider.create_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=4096,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            from utils.json_utils import extract_json_from_response
            result = extract_json_from_response(response.content)

            if result and "fixed_code" in result:
                fixed_code = result["fixed_code"]
                fixes = result.get("fixes_applied", [])

                return fixed_code, {
                    "fixed_count": len(fixes),
                    "turns_used": 1,
                    "fixes": fixes
                }

        except Exception as e:
            logger.error("llm_fix_failed", error=str(e))

        # Fallback: return original code
        return code, {"fixed_count": 0, "turns_used": 0, "fixes": []}
