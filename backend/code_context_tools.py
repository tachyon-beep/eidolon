"""
Interactive Code Context Tools - Phase 4 Enhancement

Provides tool-calling interface for agents to request specific code context
from the code graph on-demand, instead of dumping everything upfront.

Benefits:
- Token efficient: Only fetch what's needed
- More focused: Agent sees exactly what it asks for
- Scalable: Works with large codebases
"""

from typing import Dict, Any, List, Optional
from code_graph import CodeGraph, CodeElement
from logging_config import get_logger

logger = get_logger(__name__)


# Tool specifications for LLM function calling
CODE_CONTEXT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_function_definition",
            "description": "Get the complete source code and signature of a specific function or method",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Name of the function (e.g., 'calculate_total' or 'User.validate_email')"
                    },
                    "module_path": {
                        "type": "string",
                        "description": "Optional module path to narrow search (e.g., 'services/orders.py')"
                    }
                },
                "required": ["function_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_function_callers",
            "description": "Get list of all functions that call a specific function",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Name of the function to find callers for"
                    }
                },
                "required": ["function_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_function_callees",
            "description": "Get list of all functions called by a specific function",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {
                        "type": "string",
                        "description": "Name of the function to find callees for"
                    }
                },
                "required": ["function_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_class_definition",
            "description": "Get the complete source code of a class including all its methods",
            "parameters": {
                "type": "object",
                "properties": {
                    "class_name": {
                        "type": "string",
                        "description": "Name of the class (e.g., 'User', 'OrderProcessor')"
                    }
                },
                "required": ["class_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_module_overview",
            "description": "Get overview of a module including all functions and classes",
            "parameters": {
                "type": "object",
                "properties": {
                    "module_path": {
                        "type": "string",
                        "description": "Path to module (e.g., 'services/orders.py')"
                    },
                    "include_source": {
                        "type": "boolean",
                        "description": "Whether to include full source code (default: false, just signatures)"
                    }
                },
                "required": ["module_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_functions",
            "description": "Search for functions by name pattern across the codebase",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (e.g., 'validate', 'calculate_*')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)"
                    }
                },
                "required": ["pattern"]
            }
        }
    }
]


class CodeContextToolHandler:
    """Handles tool calls for fetching code context from the code graph"""

    def __init__(self, code_graph: Optional[CodeGraph] = None):
        """
        Initialize tool handler

        Args:
            code_graph: Code graph to fetch context from
        """
        self.code_graph = code_graph

    def handle_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle a tool call and return the result

        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments

        Returns:
            Result dict with the requested context
        """
        if not self.code_graph:
            return {
                "error": "Code graph not available",
                "message": "Code graph analysis is not enabled or failed"
            }

        logger.info(
            "tool_call_received",
            tool=tool_name,
            arguments=arguments
        )

        # Dispatch to appropriate handler
        handlers = {
            "get_function_definition": self._get_function_definition,
            "get_function_callers": self._get_function_callers,
            "get_function_callees": self._get_function_callees,
            "get_class_definition": self._get_class_definition,
            "get_module_overview": self._get_module_overview,
            "search_functions": self._search_functions
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = handler(arguments)
            logger.info(
                "tool_call_completed",
                tool=tool_name,
                result_size=len(str(result))
            )
            return result
        except Exception as e:
            logger.error(
                "tool_call_failed",
                tool=tool_name,
                error=str(e)
            )
            return {"error": str(e)}

    def _get_function_definition(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get function definition"""
        function_name = args["function_name"]
        module_path = args.get("module_path")

        # Search for function in graph
        matches = []
        for func_id, func in self.code_graph.functions.items():
            if func.name == function_name:
                if module_path:
                    # Filter by module path if provided
                    if module_path in str(func.file_path):
                        matches.append(func)
                else:
                    matches.append(func)

        if not matches:
            return {
                "found": False,
                "message": f"Function '{function_name}' not found in code graph"
            }

        # Return first match (or all if multiple)
        if len(matches) == 1:
            func = matches[0]
            return {
                "found": True,
                "function_name": func.name,
                "file": str(func.file_path),
                "line": func.line_number,
                "signature": func.signature,
                "docstring": func.docstring,
                "source_code": func.source_code,
                "complexity": func.cyclomatic_complexity,
                "param_types": func.param_types,
                "return_type": func.return_type
            }
        else:
            # Multiple matches
            return {
                "found": True,
                "multiple_matches": True,
                "count": len(matches),
                "matches": [
                    {
                        "function_name": f.name,
                        "file": str(f.file_path),
                        "line": f.line_number,
                        "signature": f.signature,
                        "source_code": f.source_code
                    }
                    for f in matches[:5]  # Limit to 5
                ]
            }

    def _get_function_callers(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get functions that call this function"""
        function_name = args["function_name"]

        # Find the function first
        target_func = None
        for func in self.code_graph.functions.values():
            if func.name == function_name:
                target_func = func
                break

        if not target_func:
            return {"found": False, "message": f"Function '{function_name}' not found"}

        # Get callers
        callers = []
        for caller_id in target_func.called_by:
            if caller_id in self.code_graph.elements:
                caller = self.code_graph.elements[caller_id]
                callers.append({
                    "name": caller.name,
                    "file": str(caller.file_path),
                    "line": caller.line_number,
                    "signature": caller.signature,
                    "type": caller.type.value
                })

        return {
            "found": True,
            "function_name": function_name,
            "caller_count": len(callers),
            "callers": callers
        }

    def _get_function_callees(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get functions called by this function"""
        function_name = args["function_name"]

        # Find the function
        target_func = None
        for func in self.code_graph.functions.values():
            if func.name == function_name:
                target_func = func
                break

        if not target_func:
            return {"found": False, "message": f"Function '{function_name}' not found"}

        # Get callees (functions this function calls)
        callees = []
        for call_name in target_func.calls:
            # Try to resolve the call
            for func_id, func in self.code_graph.functions.items():
                if func.name == call_name:
                    callees.append({
                        "name": func.name,
                        "file": str(func.file_path),
                        "line": func.line_number,
                        "signature": func.signature,
                        "docstring": func.docstring
                    })
                    break  # Take first match

        return {
            "found": True,
            "function_name": function_name,
            "callee_count": len(callees),
            "callees": callees
        }

    def _get_class_definition(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get class definition"""
        class_name = args["class_name"]

        # Search for class
        matches = []
        for class_id, cls in self.code_graph.classes.items():
            if cls.name == class_name:
                matches.append(cls)

        if not matches:
            return {"found": False, "message": f"Class '{class_name}' not found"}

        cls = matches[0]
        return {
            "found": True,
            "class_name": cls.name,
            "file": str(cls.file_path),
            "line": cls.line_number,
            "docstring": cls.docstring,
            "source_code": cls.source_code,
            "lines_of_code": cls.lines_of_code
        }

    def _get_module_overview(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get module overview"""
        module_path = args["module_path"]
        include_source = args.get("include_source", False)

        # Find module
        target_module = None
        for module_id, module in self.code_graph.modules.items():
            if module_path in str(module.file_path):
                target_module = module
                break

        if not target_module:
            return {"found": False, "message": f"Module '{module_path}' not found"}

        # Get functions and classes in this module
        functions = []
        classes = []

        for func in self.code_graph.functions.values():
            if func.parent_module == target_module.id:
                func_info = {
                    "name": func.name,
                    "line": func.line_number,
                    "signature": func.signature,
                    "docstring": func.docstring
                }
                if include_source:
                    func_info["source_code"] = func.source_code
                functions.append(func_info)

        for cls in self.code_graph.classes.values():
            if cls.parent_module == target_module.id:
                cls_info = {
                    "name": cls.name,
                    "line": cls.line_number,
                    "docstring": cls.docstring
                }
                if include_source:
                    cls_info["source_code"] = cls.source_code
                classes.append(cls_info)

        return {
            "found": True,
            "module_path": str(target_module.file_path),
            "docstring": target_module.docstring,
            "lines_of_code": target_module.lines_of_code,
            "imports": target_module.imports,
            "function_count": len(functions),
            "class_count": len(classes),
            "functions": functions,
            "classes": classes
        }

    def _search_functions(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for functions by name pattern"""
        pattern = args["pattern"].lower()
        limit = args.get("limit", 10)

        matches = []
        for func in self.code_graph.functions.values():
            if pattern in func.name.lower():
                matches.append({
                    "name": func.name,
                    "file": str(func.file_path),
                    "line": func.line_number,
                    "signature": func.signature,
                    "type": func.type.value
                })

                if len(matches) >= limit:
                    break

        return {
            "pattern": pattern,
            "match_count": len(matches),
            "matches": matches,
            "truncated": len(matches) >= limit
        }
