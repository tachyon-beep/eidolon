"""Static analysis checks for Python code."""

import ast
from typing import Optional

from .models import Finding


class StaticAnalyzer:
    """Performs static analysis on Python AST."""

    def __init__(self, source_code: str, file_path: str):
        """Initialize analyzer.

        Args:
            source_code: Python source code
            file_path: Path to file (for error messages)
        """
        self.source_code = source_code
        self.file_path = file_path
        self.tree: Optional[ast.AST] = None

        try:
            self.tree = ast.parse(source_code)
        except SyntaxError as e:
            # Can't analyze if syntax is broken
            self.tree = None
            self.syntax_error = e

    def analyze_function(self, function_node: ast.FunctionDef) -> list[Finding]:
        """Analyze a function node.

        Args:
            function_node: AST node for function

        Returns:
            List of findings
        """
        if self.tree is None:
            return []

        findings = []
        findings.extend(self._check_complexity(function_node))
        findings.extend(self._check_unclosed_resources(function_node))
        findings.extend(self._check_null_safety(function_node))
        findings.extend(self._check_exception_handling(function_node))
        findings.extend(self._check_unused_variables(function_node))

        return findings

    def _check_complexity(self, node: ast.FunctionDef) -> list[Finding]:
        """Check cyclomatic complexity (simplified McCabe)."""
        findings = []

        # Count decision points
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        if complexity > 10:
            findings.append(
                Finding(
                    location=f"{self.file_path}:{node.lineno}",
                    severity="high" if complexity > 15 else "medium",
                    type="performance",
                    description=f"Function has high complexity ({complexity}). "
                    f"Consider breaking into smaller functions.",
                    suggested_fix="Refactor into smaller, focused functions",
                )
            )

        return findings

    def _check_unclosed_resources(self, node: ast.FunctionDef) -> list[Finding]:
        """Check for file handles or resources not in context managers."""
        findings = []

        for child in ast.walk(node):
            # Look for open() calls not in 'with' statement
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == "open":
                    # Check if this is inside a 'with' statement
                    if not self._is_in_with_statement(node, child):
                        findings.append(
                            Finding(
                                location=f"{self.file_path}:{child.lineno}",
                                severity="high",
                                type="bug",
                                description="File opened without context manager. "
                                "May not be closed properly on error.",
                                suggested_fix="Use 'with open(...) as f:' instead",
                                code_snippet=ast.unparse(child),
                            )
                        )

        return findings

    def _check_null_safety(self, node: ast.FunctionDef) -> list[Finding]:
        """Check for potential None access without checks."""
        findings = []

        # Track variables that might be None
        possible_none_vars = set()

        for child in ast.walk(node):
            # Track assignments of None
            if isinstance(child, ast.Assign):
                if isinstance(child.value, ast.Constant) and child.value.value is None:
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            possible_none_vars.add(target.id)

            # Track function calls that might return None
            if isinstance(child, ast.Assign):
                if isinstance(child.value, ast.Call):
                    # Common functions that might return None
                    if isinstance(child.value.func, ast.Attribute):
                        if child.value.func.attr in ["get", "find", "search"]:
                            for target in child.targets:
                                if isinstance(target, ast.Name):
                                    possible_none_vars.add(target.id)

            # Check for attribute access on possible None
            if isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name):
                    if child.value.id in possible_none_vars:
                        # Check if there's a None check nearby
                        if not self._has_none_check_before(node, child, child.value.id):
                            findings.append(
                                Finding(
                                    location=f"{self.file_path}:{child.lineno}",
                                    severity="high",
                                    type="bug",
                                    description=f"Accessing attribute on '{child.value.id}' "
                                    f"which might be None",
                                    suggested_fix=f"Add None check: if {child.value.id} is not None:",
                                    code_snippet=ast.unparse(child),
                                )
                            )

        return findings

    def _check_exception_handling(self, node: ast.FunctionDef) -> list[Finding]:
        """Check for bad exception handling patterns."""
        findings = []

        for child in ast.walk(node):
            if isinstance(child, ast.ExceptHandler):
                # Bare except (catches everything)
                if child.type is None:
                    findings.append(
                        Finding(
                            location=f"{self.file_path}:{child.lineno}",
                            severity="medium",
                            type="bug",
                            description="Bare 'except:' catches all exceptions including "
                            "KeyboardInterrupt and SystemExit",
                            suggested_fix="Catch specific exception types: except ValueError:",
                        )
                    )

                # Empty except block
                if len(child.body) == 1 and isinstance(child.body[0], ast.Pass):
                    findings.append(
                        Finding(
                            location=f"{self.file_path}:{child.lineno}",
                            severity="medium",
                            type="bug",
                            description="Empty except block silently swallows errors",
                            suggested_fix="Log the error or handle it explicitly",
                        )
                    )

        return findings

    def _check_unused_variables(self, node: ast.FunctionDef) -> list[Finding]:
        """Check for variables that are assigned but never used."""
        findings = []

        # Get all variable assignments
        assigned = set()
        used = set()

        for child in ast.walk(node):
            # Track assignments
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        assigned.add(target.id)

            # Track usage
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                used.add(child.id)

        # Find unused (but exclude common patterns like _)
        unused = assigned - used
        unused = {v for v in unused if not v.startswith("_")}

        for var in unused:
            findings.append(
                Finding(
                    location=f"{self.file_path}:{node.lineno}",
                    severity="low",
                    type="style",
                    description=f"Variable '{var}' is assigned but never used",
                    suggested_fix=f"Remove unused variable or prefix with _ if intentional",
                )
            )

        return findings

    def _is_in_with_statement(
        self, function_node: ast.FunctionDef, target_node: ast.AST
    ) -> bool:
        """Check if a node is inside a 'with' statement."""
        # Simple check: walk the function and see if target is in a With body
        for child in ast.walk(function_node):
            if isinstance(child, ast.With):
                for item in ast.walk(child):
                    if item is target_node:
                        return True
        return False

    def _has_none_check_before(
        self, function_node: ast.FunctionDef, target_node: ast.AST, var_name: str
    ) -> bool:
        """Check if there's a None check for variable before usage."""
        # Simplified: check if there's any comparison with None
        for child in ast.walk(function_node):
            if isinstance(child, ast.Compare):
                if isinstance(child.left, ast.Name) and child.left.id == var_name:
                    for op in child.ops:
                        if isinstance(op, (ast.IsNot, ast.Is)):
                            return True
        return False


def analyze_function_code(
    function_name: str, source_code: str, file_path: str
) -> list[Finding]:
    """Convenience function to analyze a function's code.

    Args:
        function_name: Name of function to analyze
        source_code: Complete source code containing the function
        file_path: Path to file

    Returns:
        List of findings
    """
    analyzer = StaticAnalyzer(source_code, file_path)

    if analyzer.tree is None:
        return [
            Finding(
                location=f"{file_path}:1",
                severity="critical",
                type="bug",
                description="Syntax error prevents analysis",
            )
        ]

    # Find the function node
    for node in ast.walk(analyzer.tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return analyzer.analyze_function(node)

    return []
