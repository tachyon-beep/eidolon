import ast
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class FunctionInfo:
    """Information about a function or method"""
    name: str
    line_start: int
    line_end: int
    args: List[str]
    returns: str
    docstring: str
    complexity: int
    is_async: bool
    decorators: List[str]
    calls: List[str]  # Functions this function calls
    called_by: List[str] = None  # Functions that call this (populated later)


@dataclass
class ClassInfo:
    """Information about a class"""
    name: str
    line_start: int
    line_end: int
    methods: List[FunctionInfo]
    bases: List[str]
    docstring: str


@dataclass
class ModuleInfo:
    """Information about a Python module"""
    file_path: str
    imports: List[str]
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    lines_of_code: int
    docstring: str


class CodeAnalyzer:
    """Analyzes Python code using AST parsing"""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)

    def analyze_directory(self, path: str = None) -> List[ModuleInfo]:
        """Analyze all Python files in a directory"""
        target_path = self.base_path / (path or "")
        modules = []

        for py_file in target_path.rglob("*.py"):
            try:
                module_info = self.analyze_file(str(py_file))
                modules.append(module_info)
            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")
                continue

        return modules

    def analyze_file(self, file_path: str) -> ModuleInfo:
        """Analyze a single Python file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source, filename=file_path)

        return ModuleInfo(
            file_path=file_path,
            imports=self._extract_imports(tree),
            functions=self._extract_functions(tree),
            classes=self._extract_classes(tree),
            lines_of_code=len(source.splitlines()),
            docstring=ast.get_docstring(tree) or ""
        )

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports

    def _extract_functions(self, tree: ast.AST, parent_class=None) -> List[FunctionInfo]:
        """Extract function definitions"""
        functions = []

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._parse_function(node)
                functions.append(func_info)

        return functions

    def _extract_classes(self, tree: ast.AST) -> List[ClassInfo]:
        """Extract class definitions"""
        classes = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_info = ClassInfo(
                    name=node.name,
                    line_start=node.lineno,
                    line_end=node.end_lineno or node.lineno,
                    methods=self._extract_methods(node),
                    bases=[self._get_base_name(base) for base in node.bases],
                    docstring=ast.get_docstring(node) or ""
                )
                classes.append(class_info)

        return classes

    def _extract_methods(self, class_node: ast.ClassDef) -> List[FunctionInfo]:
        """Extract methods from a class"""
        methods = []
        for node in class_node.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._parse_function(node)
                methods.append(method_info)
        return methods

    def _parse_function(self, node: ast.FunctionDef) -> FunctionInfo:
        """Parse a function/method node"""
        args = [arg.arg for arg in node.args.args]

        # Get return annotation
        returns = ""
        if node.returns:
            returns = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)

        # Get decorators
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            else:
                decorators.append(ast.unparse(decorator) if hasattr(ast, 'unparse') else str(decorator))

        # Extract function calls
        calls = self._extract_function_calls(node)

        return FunctionInfo(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            args=args,
            returns=returns,
            docstring=ast.get_docstring(node) or "",
            complexity=self._calculate_complexity(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            decorators=decorators,
            calls=calls,
            called_by=[]
        )

    def _extract_function_calls(self, node: ast.AST) -> List[str]:
        """Extract all function calls made within this function"""
        calls = []

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Get the function name
                func_name = None
                if isinstance(child.func, ast.Name):
                    # Simple function call: foo()
                    func_name = child.func.id
                elif isinstance(child.func, ast.Attribute):
                    # Method call: obj.method() or module.func()
                    func_name = child.func.attr
                    # Try to get the full qualified name
                    if isinstance(child.func.value, ast.Name):
                        func_name = f"{child.func.value.id}.{child.func.attr}"

                if func_name and func_name not in calls:
                    calls.append(func_name)

        return calls

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity (simplified)"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Each decision point adds 1 to complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _get_base_name(self, base: ast.expr) -> str:
        """Get the name of a base class"""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return ast.unparse(base) if hasattr(ast, 'unparse') else str(base)
        return str(base)

    def detect_code_smells(self, module_info: ModuleInfo) -> List[Dict[str, Any]]:
        """Detect potential code smells"""
        smells = []

        # Check for long functions
        for func in module_info.functions:
            if func.line_end - func.line_start > 50:
                smells.append({
                    "type": "long_function",
                    "severity": "medium",
                    "location": f"{module_info.file_path}:{func.line_start}",
                    "message": f"Function '{func.name}' is too long ({func.line_end - func.line_start} lines)"
                })

            # Check for high complexity
            if func.complexity > 10:
                smells.append({
                    "type": "high_complexity",
                    "severity": "high",
                    "location": f"{module_info.file_path}:{func.line_start}",
                    "message": f"Function '{func.name}' has high complexity ({func.complexity})"
                })

            # Check for missing docstrings
            if not func.docstring and not func.name.startswith('_'):
                smells.append({
                    "type": "missing_docstring",
                    "severity": "low",
                    "location": f"{module_info.file_path}:{func.line_start}",
                    "message": f"Function '{func.name}' lacks documentation"
                })

        # Check for classes
        for cls in module_info.classes:
            # Check for God classes
            if len(cls.methods) > 20:
                smells.append({
                    "type": "god_class",
                    "severity": "high",
                    "location": f"{module_info.file_path}:{cls.line_start}",
                    "message": f"Class '{cls.name}' has too many methods ({len(cls.methods)})"
                })

            # Check for missing docstrings
            if not cls.docstring:
                smells.append({
                    "type": "missing_docstring",
                    "severity": "low",
                    "location": f"{module_info.file_path}:{cls.line_start}",
                    "message": f"Class '{cls.name}' lacks documentation"
                })

        return smells

    def generate_summary(self, module_info: ModuleInfo) -> str:
        """Generate a markdown summary of the module"""
        summary = f"# {Path(module_info.file_path).name}\n\n"

        if module_info.docstring:
            summary += f"{module_info.docstring}\n\n"

        summary += f"**Lines of Code:** {module_info.lines_of_code}\n\n"

        if module_info.functions:
            summary += f"## Functions ({len(module_info.functions)})\n\n"
            for func in module_info.functions:
                summary += f"- `{func.name}({', '.join(func.args)})` (lines {func.line_start}-{func.line_end})\n"
                if func.complexity > 5:
                    summary += f"  - ⚠️ Complexity: {func.complexity}\n"

        if module_info.classes:
            summary += f"\n## Classes ({len(module_info.classes)})\n\n"
            for cls in module_info.classes:
                summary += f"- `{cls.name}` (lines {cls.line_start}-{cls.line_end})\n"
                summary += f"  - Methods: {len(cls.methods)}\n"

        return summary

    def build_call_graph(self, modules: List[ModuleInfo]) -> Dict[str, Any]:
        """Build a call graph for the entire codebase"""
        # Create a mapping of function name -> FunctionInfo
        all_functions = {}

        for module in modules:
            module_name = Path(module.file_path).stem

            # Add top-level functions
            for func in module.functions:
                key = f"{module_name}.{func.name}"
                all_functions[key] = {
                    'info': func,
                    'module': module.file_path,
                    'qualified_name': key
                }

            # Add class methods
            for cls in module.classes:
                for method in cls.methods:
                    key = f"{module_name}.{cls.name}.{method.name}"
                    all_functions[key] = {
                        'info': method,
                        'module': module.file_path,
                        'qualified_name': key
                    }

        # Build reverse call graph (who calls whom)
        for func_key, func_data in all_functions.items():
            func_info = func_data['info']

            for called_func_name in func_info.calls:
                # Try to find the called function in our mapping
                # This is simplified - in reality we'd need import resolution
                for candidate_key in all_functions.keys():
                    if candidate_key.endswith(called_func_name) or candidate_key.endswith(f".{called_func_name}"):
                        called_func = all_functions[candidate_key]['info']
                        if called_func.called_by is None:
                            called_func.called_by = []
                        if func_key not in called_func.called_by:
                            called_func.called_by.append(func_key)

        return {
            'functions': all_functions,
            'orphaned': [k for k, v in all_functions.items() if not v['info'].called_by],
            'hotspots': sorted(
                [(k, len(v['info'].called_by or [])) for k, v in all_functions.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

    def get_function_context(self, func_info: FunctionInfo, call_graph: Dict[str, Any],
                            module_info: ModuleInfo) -> Dict[str, Any]:
        """Get context for a function including callers and callees"""
        context = {
            'function': func_info.name,
            'calls': func_info.calls,
            'called_by': func_info.called_by or [],
            'caller_code': [],
            'callee_code': []
        }

        # Get source code for this module
        with open(module_info.file_path, 'r') as f:
            lines = f.readlines()

        # Get code for functions that call this one
        for caller_name in (func_info.called_by or [])[:3]:  # Limit to 3 callers
            if caller_name in call_graph['functions']:
                caller_func = call_graph['functions'][caller_name]['info']
                caller_module = call_graph['functions'][caller_name]['module']

                try:
                    with open(caller_module, 'r') as f:
                        caller_lines = f.readlines()
                    code = ''.join(caller_lines[caller_func.line_start - 1:caller_func.line_end])
                    context['caller_code'].append({
                        'name': caller_name,
                        'code': code[:500]  # Limit size
                    })
                except:
                    pass

        # Get code for functions this one calls
        for callee_name in func_info.calls[:3]:  # Limit to 3 callees
            # Find the callee in our call graph
            for candidate_key, candidate_data in call_graph['functions'].items():
                if candidate_key.endswith(callee_name) or candidate_key.endswith(f".{callee_name}"):
                    callee_func = candidate_data['info']
                    callee_module = candidate_data['module']

                    try:
                        with open(callee_module, 'r') as f:
                            callee_lines = f.readlines()
                        code = ''.join(callee_lines[callee_func.line_start - 1:callee_func.line_end])
                        context['callee_code'].append({
                            'name': candidate_key,
                            'code': code[:500]  # Limit size
                        })
                        break
                    except:
                        pass

        return context
