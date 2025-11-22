"""
Test Generator Module

Generates unit tests for implemented functions and classes.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import subprocess
import sys

from llm_providers import LLMProvider
from logging_config import get_logger

logger = get_logger(__name__)


class TestGenerator:
    """
    Generates unit tests for code

    Uses AI to generate comprehensive test cases covering:
    - Normal cases
    - Edge cases
    - Error cases
    - Boundary conditions
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    async def generate_function_tests(
        self,
        function_code: str,
        function_name: str,
        module_path: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate unit tests for a function

        Args:
            function_code: The function implementation
            function_name: Name of the function
            module_path: Path to module containing function
            context: Additional context (dependencies, etc.)

        Returns:
            Dict with test_code, test_count, coverage_estimate
        """
        context = context or {}

        prompt = f"""Generate comprehensive unit tests for this Python function.

Function to test:
```python
{function_code}
```

Module: {module_path}
Function: {function_name}

Your task:
1. Generate pytest test cases covering:
   - Normal/happy path cases
   - Edge cases (empty inputs, None, etc.)
   - Error cases (invalid inputs, exceptions)
   - Boundary conditions
2. Use descriptive test names (test_function_name_with_condition)
3. Include docstrings explaining what each test verifies
4. Mock external dependencies if needed

Respond in JSON format:
{{
  "test_code": "import pytest\\n\\ndef test_...",
  "test_count": 5,
  "coverage_estimate": 85.0,
  "explanation": "Brief explanation of test strategy"
}}"""

        response = await self.llm_provider.create_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.1  # Slightly higher for variety in test cases
        )

        # Parse response
        import json
        try:
            result = json.loads(response.content)
        except:
            # Fallback: generate basic test
            result = {
                "test_code": f'''import pytest

def test_{function_name}_basic():
    """Test basic functionality of {function_name}"""
    # TODO: Implement test
    pass
''',
                "test_count": 1,
                "coverage_estimate": 30.0,
                "explanation": "Basic placeholder test"
            }

        logger.info(
            "tests_generated",
            function=function_name,
            test_count=result.get("test_count", 0),
            coverage=result.get("coverage_estimate", 0)
        )

        return result

    async def generate_class_tests(
        self,
        class_code: str,
        class_name: str,
        module_path: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate unit tests for a class

        Args:
            class_code: The class implementation
            class_name: Name of the class
            module_path: Path to module containing class
            context: Additional context

        Returns:
            Dict with test_code, test_count, coverage_estimate
        """
        context = context or {}

        prompt = f"""Generate comprehensive unit tests for this Python class.

Class to test:
```python
{class_code}
```

Module: {module_path}
Class: {class_name}

Your task:
1. Create test class (Test{class_name})
2. Test each method with multiple cases
3. Test initialization
4. Test class properties and invariants
5. Use fixtures for setup/teardown
6. Mock dependencies

Respond in JSON format:
{{
  "test_code": "import pytest\\n\\nclass Test{class_name}:\\n...",
  "test_count": 10,
  "coverage_estimate": 90.0,
  "explanation": "Brief explanation"
}}"""

        response = await self.llm_provider.create_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.1
        )

        # Parse response
        import json
        try:
            result = json.loads(response.content)
        except:
            result = {
                "test_code": f'''import pytest

class Test{class_name}:
    """Tests for {class_name}"""

    def test_initialization(self):
        """Test {class_name} can be initialized"""
        # TODO: Implement test
        pass
''',
                "test_count": 1,
                "coverage_estimate": 30.0,
                "explanation": "Basic placeholder test"
            }

        return result


class TestRunner:
    """
    Runs generated tests and reports results
    """

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def run_tests(
        self,
        test_file_path: str,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Run tests using pytest

        Args:
            test_file_path: Path to test file (relative to project)
            timeout: Timeout in seconds

        Returns:
            Dict with passed, failed, error, output
        """
        full_path = self.project_path / test_file_path

        if not full_path.exists():
            return {
                "success": False,
                "error": f"Test file not found: {test_file_path}",
                "passed": 0,
                "failed": 0,
                "total": 0
            }

        try:
            # Run pytest with JSON output
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    str(full_path),
                    "-v",
                    "--tb=short",
                    f"--timeout={timeout}"
                ],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )

            # Parse output (simplified - in production would use pytest-json-report)
            output = result.stdout + result.stderr

            # Count passed/failed from output
            passed = output.count(" PASSED")
            failed = output.count(" FAILED")
            errors = output.count(" ERROR")
            total = passed + failed + errors

            success = result.returncode == 0

            logger.info(
                "tests_run",
                file=test_file_path,
                passed=passed,
                failed=failed,
                errors=errors,
                success=success
            )

            return {
                "success": success,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "total": total,
                "output": output,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            logger.error("test_timeout", file=test_file_path, timeout=timeout)
            return {
                "success": False,
                "error": f"Tests timed out after {timeout}s",
                "passed": 0,
                "failed": 0,
                "total": 0,
                "output": ""
            }

        except Exception as e:
            logger.error("test_run_failed", file=test_file_path, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "passed": 0,
                "failed": 0,
                "total": 0,
                "output": ""
            }

    def run_module_tests(
        self,
        module_path: str,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Run all tests for a module

        Args:
            module_path: Path to module (e.g., "services/auth_service.py")
            timeout: Timeout in seconds

        Returns:
            Dict with test results
        """
        # Derive test file path (e.g., "tests/test_auth_service.py")
        module_name = Path(module_path).stem
        test_file = f"tests/test_{module_name}.py"

        return self.run_tests(test_file, timeout=timeout)

    def calculate_coverage(
        self,
        source_path: str,
        test_path: str
    ) -> Dict[str, Any]:
        """
        Calculate code coverage

        Args:
            source_path: Path to source module
            test_path: Path to test file

        Returns:
            Dict with coverage percentage and details
        """
        try:
            # Run pytest with coverage
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    str(self.project_path / test_path),
                    f"--cov={self.project_path / source_path}",
                    "--cov-report=json",
                    "--cov-report=term"
                ],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60
            )

            # Parse coverage from output (simplified)
            output = result.stdout + result.stderr

            # Look for coverage percentage in output
            # Format: "TOTAL   100   50   50%"
            import re
            match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
            coverage_pct = float(match.group(1)) if match else 0.0

            return {
                "success": True,
                "coverage": coverage_pct,
                "output": output
            }

        except Exception as e:
            logger.error("coverage_calculation_failed", error=str(e))
            return {
                "success": False,
                "coverage": 0.0,
                "error": str(e)
            }
