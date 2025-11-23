"""
Code Graph Analyzer - Phase 4

Parses entire Python project to build a comprehensive code graph:
- Functions, classes, modules, imports
- Call graph (who calls what)
- Dependency graph (what imports what)
- Type information from hints
- Optional LLM-generated descriptions for UX

This runs BEFORE orchestration to provide context to all decomposers.
"""

import ast
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx

from eidolon.llm_providers import LLMProvider
from eidolon.logging_config import get_logger

logger = get_logger(__name__)


class CodeElementType(Enum):
    """Type of code element"""
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    MODULE = "module"
    SUBSYSTEM = "subsystem"


@dataclass
class CodeElement:
    """A single code element (function, class, etc.)"""
    id: str  # Unique identifier (e.g., "module.py::MyClass::method")
    name: str
    type: CodeElementType
    file_path: Path
    line_number: int

    # Code details
    source_code: str = ""
    docstring: Optional[str] = None
    signature: Optional[str] = None  # For functions/methods

    # Type information
    return_type: Optional[str] = None
    param_types: Dict[str, str] = field(default_factory=dict)

    # Dependencies
    imports: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)  # Functions/methods this calls
    called_by: List[str] = field(default_factory=list)  # Functions that call this
    uses_classes: List[str] = field(default_factory=list)

    # Parent relationships
    parent_class: Optional[str] = None
    parent_module: Optional[str] = None
    parent_subsystem: Optional[str] = None

    # LLM-generated metadata (optional)
    ai_description: Optional[str] = None
    ai_purpose: Optional[str] = None
    ai_complexity: Optional[str] = None  # "simple", "medium", "complex"

    # Metrics
    lines_of_code: int = 0
    cyclomatic_complexity: int = 0


@dataclass
class CodeGraph:
    """Complete graph of a codebase"""
    project_path: Path

    # All elements indexed by ID
    elements: Dict[str, CodeElement] = field(default_factory=dict)

    # Organized by type
    functions: Dict[str, CodeElement] = field(default_factory=dict)
    classes: Dict[str, CodeElement] = field(default_factory=dict)
    modules: Dict[str, CodeElement] = field(default_factory=dict)
    subsystems: Dict[str, CodeElement] = field(default_factory=dict)

    # NetworkX graphs for analysis
    call_graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    import_graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    dependency_graph: nx.DiGraph = field(default_factory=nx.DiGraph)

    # Statistics
    total_lines: int = 0
    total_functions: int = 0
    total_classes: int = 0
    total_modules: int = 0


class CodeGraphAnalyzer:
    """
    Analyzes Python projects to build comprehensive code graphs

    This is the FIRST step before orchestration - it creates a map
    of the entire codebase that decomposers can use for context.
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        generate_ai_descriptions: bool = False
    ):
        """
        Initialize analyzer

        Args:
            llm_provider: Optional LLM for generating descriptions
            generate_ai_descriptions: Whether to use LLM to describe code elements
        """
        self.llm_provider = llm_provider
        self.generate_ai_descriptions = generate_ai_descriptions

    async def analyze_project(
        self,
        project_path: Path,
        exclude_patterns: List[str] = None
    ) -> CodeGraph:
        """
        Analyze entire project and build code graph

        Args:
            project_path: Root path of project
            exclude_patterns: Patterns to exclude (e.g., ["test_*", ".*"])

        Returns:
            Complete CodeGraph with all elements and relationships
        """
        logger.info("code_analysis_started", project_path=str(project_path))

        exclude_patterns = exclude_patterns or [
            "test_*",
            "*_test.py",
            ".*",
            "__pycache__",
            "venv",
            "env",
            ".venv"
        ]

        graph = CodeGraph(project_path=project_path)

        # Step 1: Discover all Python files
        python_files = self._discover_python_files(project_path, exclude_patterns)
        logger.info("python_files_discovered", count=len(python_files))

        # Step 2: Parse each file with AST
        for py_file in python_files:
            try:
                await self._parse_file(py_file, graph)
            except Exception as e:
                logger.warning("file_parse_failed", file=str(py_file), error=str(e))

        # Step 3: Build relationship graphs
        self._build_call_graph(graph)
        self._build_import_graph(graph)
        self._build_dependency_graph(graph)

        # Step 4: Calculate metrics
        self._calculate_metrics(graph)

        # Step 5: Optional AI descriptions
        if self.generate_ai_descriptions and self.llm_provider:
            await self._generate_ai_descriptions(graph)

        logger.info(
            "code_analysis_complete",
            functions=graph.total_functions,
            classes=graph.total_classes,
            modules=graph.total_modules,
            total_lines=graph.total_lines
        )

        return graph

    def _discover_python_files(
        self,
        project_path: Path,
        exclude_patterns: List[str]
    ) -> List[Path]:
        """Find all Python files in project"""
        import fnmatch

        python_files = []

        for py_file in project_path.rglob("*.py"):
            # Check if file matches any exclude pattern
            relative_path = py_file.relative_to(project_path)

            excluded = False
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(str(relative_path), pattern) or \
                   fnmatch.fnmatch(py_file.name, pattern):
                    excluded = True
                    break

            if not excluded:
                python_files.append(py_file)

        return sorted(python_files)

    async def _parse_file(self, file_path: Path, graph: CodeGraph):
        """Parse a single Python file using AST"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning("ast_parse_failed", file=str(file_path), error=str(e))
            return

        # Determine module and subsystem
        relative_path = file_path.relative_to(graph.project_path)
        module_name = str(relative_path.with_suffix(''))
        subsystem_name = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"

        # Create module element
        module_id = module_name
        module_element = CodeElement(
            id=module_id,
            name=module_name,
            type=CodeElementType.MODULE,
            file_path=file_path,
            line_number=1,
            source_code=content,
            docstring=ast.get_docstring(tree),
            parent_subsystem=subsystem_name,
            lines_of_code=len(content.splitlines())
        )

        graph.elements[module_id] = module_element
        graph.modules[module_id] = module_element
        graph.total_modules += 1
        graph.total_lines += module_element.lines_of_code

        # Parse top-level imports
        imports = self._extract_imports(tree)
        module_element.imports = imports

        # Visit all nodes in AST
        visitor = CodeVisitor(
            graph=graph,
            file_path=file_path,
            module_name=module_name,
            subsystem_name=subsystem_name
        )
        visitor.visit(tree)

        # Update totals
        graph.total_functions += visitor.function_count
        graph.total_classes += visitor.class_count

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract all import statements"""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return imports

    def _build_call_graph(self, graph: CodeGraph):
        """Build directed graph of function calls"""
        logger.info("building_call_graph")

        for element in graph.elements.values():
            if element.type in (CodeElementType.FUNCTION, CodeElementType.METHOD):
                # Add node
                graph.call_graph.add_node(element.id, element=element)

                # Add edges for calls
                for called_func in element.calls:
                    # Try to resolve the called function to an element ID
                    resolved_id = self._resolve_function_call(called_func, element, graph)
                    if resolved_id and resolved_id in graph.elements:
                        graph.call_graph.add_edge(element.id, resolved_id)

                        # Update called_by relationship
                        if resolved_id in graph.elements:
                            graph.elements[resolved_id].called_by.append(element.id)

    def _build_import_graph(self, graph: CodeGraph):
        """Build directed graph of module imports"""
        logger.info("building_import_graph")

        for element in graph.modules.values():
            graph.import_graph.add_node(element.id, element=element)

            for imported_module in element.imports:
                # Try to find module in graph
                if imported_module in graph.modules:
                    graph.import_graph.add_edge(element.id, imported_module)

    def _build_dependency_graph(self, graph: CodeGraph):
        """Build combined dependency graph (imports + calls)"""
        logger.info("building_dependency_graph")

        # Combine import and call graphs
        graph.dependency_graph = nx.compose(graph.import_graph, graph.call_graph)

    def _calculate_metrics(self, graph: CodeGraph):
        """Calculate code metrics"""
        logger.info("calculating_metrics")

        for element in graph.elements.values():
            if element.type in (CodeElementType.FUNCTION, CodeElementType.METHOD):
                # Calculate cyclomatic complexity (simplified)
                complexity = self._calculate_cyclomatic_complexity(element.source_code)
                element.cyclomatic_complexity = complexity

    def _calculate_cyclomatic_complexity(self, source_code: str) -> int:
        """
        Calculate cyclomatic complexity (simplified)

        Real formula: E - N + 2P (edges - nodes + 2*components)
        Simple approximation: count decision points + 1
        """
        decision_keywords = ['if', 'elif', 'for', 'while', 'and', 'or', 'except']

        complexity = 1  # Base complexity
        for keyword in decision_keywords:
            # Simple word boundary check
            complexity += source_code.count(f' {keyword} ')
            complexity += source_code.count(f'\n{keyword} ')

        return complexity

    def _resolve_function_call(
        self,
        call_name: str,
        caller_element: CodeElement,
        graph: CodeGraph
    ) -> Optional[str]:
        """
        Resolve a function call name to an element ID

        This is heuristic-based - tries common patterns
        """
        # Try same module first
        same_module_id = f"{caller_element.parent_module}::{call_name}"
        if same_module_id in graph.elements:
            return same_module_id

        # Try imported modules
        for imported_module in caller_element.imports:
            potential_id = f"{imported_module}::{call_name}"
            if potential_id in graph.elements:
                return potential_id

        # Try all elements (last resort)
        for element_id, element in graph.elements.items():
            if element.name == call_name:
                return element_id

        return None

    async def _generate_ai_descriptions(self, graph: CodeGraph):
        """Use LLM to generate human-friendly descriptions"""
        logger.info("generating_ai_descriptions")

        # Only describe functions and classes (not every line of code)
        elements_to_describe = [
            e for e in graph.elements.values()
            if e.type in (CodeElementType.FUNCTION, CodeElementType.METHOD, CodeElementType.CLASS)
        ]

        logger.info("ai_description_targets", count=len(elements_to_describe))

        # Batch processing to avoid rate limits
        batch_size = 5
        for i in range(0, len(elements_to_describe), batch_size):
            batch = elements_to_describe[i:i+batch_size]

            for element in batch:
                try:
                    description = await self._generate_element_description(element)
                    element.ai_description = description.get("description")
                    element.ai_purpose = description.get("purpose")
                    element.ai_complexity = description.get("complexity")
                except Exception as e:
                    logger.warning(
                        "ai_description_failed",
                        element=element.id,
                        error=str(e)
                    )

    async def _generate_element_description(
        self,
        element: CodeElement
    ) -> Dict[str, str]:
        """Generate AI description for a single element"""

        prompt = f"""Analyze this {element.type.value}:

```python
{element.source_code[:500]}  # Truncated to 500 chars
```

Provide a brief analysis:
1. One-sentence description of what it does
2. Purpose/role in the codebase
3. Complexity level (simple/medium/complex)

Respond in JSON format:
{{
  "description": "One sentence description",
  "purpose": "Role/purpose in codebase",
  "complexity": "simple|medium|complex"
}}
"""

        response = await self.llm_provider.create_completion(
            messages=[
                {"role": "system", "content": "You are a code analyst. Provide concise, accurate descriptions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.0
        )

        # Parse JSON response
        import json
        try:
            result = json.loads(response.content)
            return result
        except json.JSONDecodeError:
            # Fallback
            return {
                "description": "Unable to parse",
                "purpose": "Unknown",
                "complexity": "unknown"
            }

    def get_context_for_function(
        self,
        function_id: str,
        graph: CodeGraph,
        max_depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get rich context for a function to pass to LLM

        This is what gets sent to FunctionPlanner when modifying code!

        Args:
            function_id: ID of function (e.g., "module.py::func_name")
            graph: Code graph
            max_depth: How deep to traverse call graph

        Returns:
            Rich context dict with callers, callees, related code
        """
        if function_id not in graph.elements:
            return {}

        element = graph.elements[function_id]

        context = {
            "function": {
                "name": element.name,
                "signature": element.signature,
                "docstring": element.docstring,
                "file": str(element.file_path),
                "line": element.line_number
            },
            "callers": [],
            "callees": [],
            "related_classes": [],
            "imports": element.imports,
            "complexity": element.cyclomatic_complexity,
            "ai_description": element.ai_description,
            "ai_purpose": element.ai_purpose
        }

        # Get direct callers (functions that call this)
        for caller_id in element.called_by:
            if caller_id in graph.elements:
                caller = graph.elements[caller_id]
                context["callers"].append({
                    "name": caller.name,
                    "file": str(caller.file_path),
                    "line": caller.line_number,
                    "signature": caller.signature
                })

        # Get direct callees (functions this calls)
        for call_name in element.calls:
            resolved_id = self._resolve_function_call(call_name, element, graph)
            if resolved_id and resolved_id in graph.elements:
                callee = graph.elements[resolved_id]
                context["callees"].append({
                    "name": callee.name,
                    "file": str(callee.file_path),
                    "line": callee.line_number,
                    "signature": callee.signature,
                    "docstring": callee.docstring
                })

        # Get related classes
        for class_name in element.uses_classes:
            if class_name in graph.classes:
                cls = graph.classes[class_name]
                context["related_classes"].append({
                    "name": cls.name,
                    "docstring": cls.docstring,
                    "file": str(cls.file_path)
                })

        return context


class CodeVisitor(ast.NodeVisitor):
    """AST visitor to extract code elements"""

    def __init__(
        self,
        graph: CodeGraph,
        file_path: Path,
        module_name: str,
        subsystem_name: str
    ):
        self.graph = graph
        self.file_path = file_path
        self.module_name = module_name
        self.subsystem_name = subsystem_name
        self.current_class = None
        self.function_count = 0
        self.class_count = 0

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition"""
        self.class_count += 1

        class_id = f"{self.module_name}::{node.name}"

        # Extract source code for this class
        source_lines = self.file_path.read_text().splitlines()
        class_source = '\n'.join(source_lines[node.lineno-1:node.end_lineno])

        element = CodeElement(
            id=class_id,
            name=node.name,
            type=CodeElementType.CLASS,
            file_path=self.file_path,
            line_number=node.lineno,
            source_code=class_source,
            docstring=ast.get_docstring(node),
            parent_module=self.module_name,
            parent_subsystem=self.subsystem_name,
            lines_of_code=node.end_lineno - node.lineno + 1 if node.end_lineno else 0
        )

        self.graph.elements[class_id] = element
        self.graph.classes[class_id] = element

        # Visit methods
        self.current_class = class_id
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function/method definition"""
        self.function_count += 1

        if self.current_class:
            # This is a method
            func_id = f"{self.current_class}::{node.name}"
            element_type = CodeElementType.METHOD
            parent_class = self.current_class
        else:
            # Top-level function
            func_id = f"{self.module_name}::{node.name}"
            element_type = CodeElementType.FUNCTION
            parent_class = None

        # Extract source code
        source_lines = self.file_path.read_text().splitlines()
        func_source = '\n'.join(source_lines[node.lineno-1:node.end_lineno])

        # Extract signature
        args = [arg.arg for arg in node.args.args]
        returns = ast.unparse(node.returns) if node.returns else None
        signature = f"{node.name}({', '.join(args)}) -> {returns}" if returns else f"{node.name}({', '.join(args)})"

        # Extract parameter types
        param_types = {}
        for arg in node.args.args:
            if arg.annotation:
                param_types[arg.arg] = ast.unparse(arg.annotation)

        # Extract function calls
        calls = self._extract_calls(node)

        element = CodeElement(
            id=func_id,
            name=node.name,
            type=element_type,
            file_path=self.file_path,
            line_number=node.lineno,
            source_code=func_source,
            docstring=ast.get_docstring(node),
            signature=signature,
            return_type=returns,
            param_types=param_types,
            parent_class=parent_class,
            parent_module=self.module_name,
            parent_subsystem=self.subsystem_name,
            calls=calls,
            lines_of_code=node.end_lineno - node.lineno + 1 if node.end_lineno else 0
        )

        self.graph.elements[func_id] = element
        self.graph.functions[func_id] = element

        # Don't visit nested functions
        # self.generic_visit(node)

    def _extract_calls(self, node: ast.FunctionDef) -> List[str]:
        """Extract all function calls within a function"""
        calls = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)

        return list(set(calls))  # Unique calls
