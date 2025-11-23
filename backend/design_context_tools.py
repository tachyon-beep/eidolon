"""
Interactive Design Context Tools - Phase 4C

Provides tools for higher-level decomposers (Module, Subsystem, System) to:
1. Explore existing architecture and patterns
2. Propose draft designs and get feedback
3. Clarify requirements interactively
4. Iterate on architecture until locked in

This enables back-and-forth on design decisions BEFORE implementation,
similar to how code_context_tools enables context fetching DURING implementation.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass
import re

from code_graph import CodeGraph, CodeElement, CodeElementType
from logging_config import get_logger

logger = get_logger(__name__)


# Tool specifications for LLM
DESIGN_CONTEXT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_existing_modules",
            "description": "Get list of existing modules in a subsystem or project. Returns module names, purposes, and key components.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subsystem": {
                        "type": "string",
                        "description": "Subsystem name to search in (optional, searches all if not provided)"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Filter modules by name pattern (optional)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_module_pattern",
            "description": "Analyze the architectural pattern used by a specific module. Returns pattern type (MVC, layered, etc.), structure, and key characteristics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "module_name": {
                        "type": "string",
                        "description": "Name of the module to analyze"
                    }
                },
                "required": ["module_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_similar_modules",
            "description": "Find modules with similar responsibilities or patterns. Useful for understanding existing approaches before designing new modules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "responsibility": {
                        "type": "string",
                        "description": "Description of what the module should do (e.g., 'authentication', 'data validation')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)"
                    }
                },
                "required": ["responsibility"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_subsystem_architecture",
            "description": "Get architectural overview of a subsystem, including its modules, relationships, and design patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subsystem_name": {
                        "type": "string",
                        "description": "Name of the subsystem to analyze"
                    }
                },
                "required": ["subsystem_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "propose_design_option",
            "description": "Propose a design option with structure and rationale. The system will provide feedback. Use this to explore different architectural approaches.",
            "parameters": {
                "type": "object",
                "properties": {
                    "option_name": {
                        "type": "string",
                        "description": "Name for this design option (e.g., 'Option A: Layered Architecture')"
                    },
                    "structure": {
                        "type": "object",
                        "description": "Proposed structure as JSON (modules, classes, functions)"
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this design approach is good"
                    },
                    "tradeoffs": {
                        "type": "string",
                        "description": "Known limitations or tradeoffs"
                    }
                },
                "required": ["option_name", "structure", "rationale"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_requirement_clarification",
            "description": "Request clarification on ambiguous requirements. Use when the specification is unclear or multiple interpretations are possible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The specific question about requirements"
                    },
                    "context": {
                        "type": "string",
                        "description": "Why this clarification is needed"
                    },
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Possible interpretations or options (if applicable)"
                    }
                },
                "required": ["question", "context"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dependency_constraints",
            "description": "Get constraints and dependencies that will affect module design (e.g., must integrate with existing auth system, must use specific database).",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "description": "Scope to check constraints for (module, subsystem, or system)"
                    }
                },
                "required": ["scope"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_design_decision",
            "description": "Validate a specific design decision against project standards, patterns, and constraints. Returns whether it's valid and any concerns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "decision": {
                        "type": "string",
                        "description": "The design decision to validate"
                    },
                    "context": {
                        "type": "string",
                        "description": "Context for this decision"
                    }
                },
                "required": ["decision"]
            }
        }
    }
]


class DesignContextToolHandler:
    """
    Handles design-level tool calls for architecture exploration and iteration.

    Unlike CodeContextToolHandler (low-level code details), this provides:
    - High-level architectural patterns
    - Design exploration and validation
    - Requirements clarification
    - Design iteration and feedback
    """

    def __init__(
        self,
        code_graph: Optional[CodeGraph] = None,
        project_context: Optional[Dict[str, Any]] = None,
        design_constraints: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize design context tool handler

        Args:
            code_graph: Code graph for analyzing existing architecture
            project_context: Additional project context (standards, patterns, etc.)
            design_constraints: Known constraints (tech stack, integrations, etc.)
        """
        self.code_graph = code_graph
        self.project_context = project_context or {}
        self.design_constraints = design_constraints or {}

        # Track proposed designs for iteration
        self.proposed_designs: List[Dict[str, Any]] = []

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch tool call to appropriate handler

        Args:
            tool_name: Name of tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        logger.info("design_tool_call_received", tool=tool_name, arguments=arguments)

        handlers = {
            "get_existing_modules": self._get_existing_modules,
            "analyze_module_pattern": self._analyze_module_pattern,
            "search_similar_modules": self._search_similar_modules,
            "get_subsystem_architecture": self._get_subsystem_architecture,
            "propose_design_option": self._propose_design_option,
            "request_requirement_clarification": self._request_requirement_clarification,
            "get_dependency_constraints": self._get_dependency_constraints,
            "validate_design_decision": self._validate_design_decision
        }

        handler = handlers.get(tool_name)
        if not handler:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = handler(arguments)
            logger.info("design_tool_call_completed", tool=tool_name, result_size=len(str(result)))
            return result
        except Exception as e:
            logger.error("design_tool_call_failed", tool=tool_name, error=str(e))
            return {"error": str(e)}

    def _get_existing_modules(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of existing modules"""
        if not self.code_graph:
            return {"found": False, "reason": "No code graph available"}

        subsystem = args.get("subsystem")
        pattern = args.get("pattern")

        modules = []
        for module_id, module in self.code_graph.modules.items():
            # Filter by subsystem if provided
            if subsystem and subsystem.lower() not in str(module.file_path).lower():
                continue

            # Filter by pattern if provided
            if pattern and pattern.lower() not in module.name.lower():
                continue

            # Get module info
            functions = [e for e in self.code_graph.elements.values()
                        if e.type == CodeElementType.FUNCTION and e.file_path == module.file_path]
            classes = [e for e in self.code_graph.elements.values()
                      if e.type == CodeElementType.CLASS and e.file_path == module.file_path]

            modules.append({
                "name": module.name,
                "file": str(module.file_path),
                "functions": len(functions),
                "classes": len(classes),
                "docstring": module.docstring or "No description",
                "imports": module.imports[:5]  # First 5 imports
            })

        return {
            "found": True,
            "count": len(modules),
            "modules": modules
        }

    def _analyze_module_pattern(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze architectural pattern of a module"""
        module_name = args["module_name"]

        if not self.code_graph:
            return {"found": False, "reason": "No code graph available"}

        # Find module
        module = None
        for m in self.code_graph.modules.values():
            if module_name.lower() in m.name.lower():
                module = m
                break

        if not module:
            return {"found": False, "reason": f"Module '{module_name}' not found"}

        # Analyze structure
        elements = [e for e in self.code_graph.elements.values()
                   if e.file_path == module.file_path]

        classes = [e for e in elements if e.type == CodeElementType.CLASS]
        functions = [e for e in elements if e.type == CodeElementType.FUNCTION]

        # Detect pattern (heuristic)
        pattern = "Procedural"
        if len(classes) > len(functions):
            pattern = "Object-Oriented"
        if any("Controller" in c.name or "View" in c.name or "Model" in c.name for c in classes):
            pattern = "MVC"
        if any("Service" in c.name or "Repository" in c.name for c in classes):
            pattern = "Layered Architecture"

        return {
            "found": True,
            "module_name": module.name,
            "pattern": pattern,
            "structure": {
                "classes": len(classes),
                "functions": len(functions),
                "class_names": [c.name for c in classes[:10]],
                "function_names": [f.name for f in functions[:10]]
            },
            "imports": module.imports[:10],
            "docstring": module.docstring
        }

    def _search_similar_modules(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search for modules with similar responsibilities"""
        responsibility = args["responsibility"].lower()
        limit = args.get("limit", 5)

        if not self.code_graph:
            return {"found": False, "reason": "No code graph available"}

        # Search keywords in responsibility
        keywords = responsibility.split()

        matches = []
        for module in self.code_graph.modules.values():
            score = 0

            # Check module name
            for keyword in keywords:
                if keyword in module.name.lower():
                    score += 3

            # Check docstring
            if module.docstring:
                for keyword in keywords:
                    if keyword in module.docstring.lower():
                        score += 2

            # Check function/class names
            elements = [e for e in self.code_graph.elements.values()
                       if e.file_path == module.file_path]
            for element in elements:
                for keyword in keywords:
                    if keyword in element.name.lower():
                        score += 1

            if score > 0:
                matches.append({
                    "module_name": module.name,
                    "file": str(module.file_path),
                    "relevance_score": score,
                    "docstring": module.docstring or "No description"
                })

        # Sort by score and limit
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)
        matches = matches[:limit]

        return {
            "found": len(matches) > 0,
            "count": len(matches),
            "matches": matches
        }

    def _get_subsystem_architecture(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get architecture overview of a subsystem"""
        subsystem_name = args["subsystem_name"]

        if not self.code_graph:
            return {"found": False, "reason": "No code graph available"}

        # Find modules in subsystem (heuristic: directory name)
        subsystem_modules = []
        for module in self.code_graph.modules.values():
            if subsystem_name.lower() in str(module.file_path).lower():
                subsystem_modules.append(module)

        if not subsystem_modules:
            return {"found": False, "reason": f"No modules found for subsystem '{subsystem_name}'"}

        # Analyze relationships
        total_classes = sum(1 for e in self.code_graph.elements.values()
                           if e.type == CodeElementType.CLASS
                           and any(e.file_path == m.file_path for m in subsystem_modules))

        total_functions = sum(1 for e in self.code_graph.elements.values()
                             if e.type == CodeElementType.FUNCTION
                             and any(e.file_path == m.file_path for m in subsystem_modules))

        return {
            "found": True,
            "subsystem_name": subsystem_name,
            "module_count": len(subsystem_modules),
            "modules": [{"name": m.name, "file": str(m.file_path)} for m in subsystem_modules],
            "total_classes": total_classes,
            "total_functions": total_functions,
            "key_patterns": "Analysis not yet implemented"  # TODO: Add pattern detection
        }

    def _propose_design_option(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Propose a design option and get feedback"""
        option_name = args["option_name"]
        structure = args["structure"]
        rationale = args["rationale"]
        tradeoffs = args.get("tradeoffs", "None specified")

        # Store proposal
        proposal = {
            "option_name": option_name,
            "structure": structure,
            "rationale": rationale,
            "tradeoffs": tradeoffs
        }
        self.proposed_designs.append(proposal)

        # Provide automated feedback (heuristic)
        feedback = []

        # Check structure completeness
        if isinstance(structure, dict):
            if "modules" not in structure and "classes" not in structure and "functions" not in structure:
                feedback.append("⚠️ Structure seems incomplete - consider specifying modules/classes/functions")
            else:
                feedback.append("✅ Structure is well-defined")

        # Check against constraints
        if self.design_constraints:
            feedback.append(f"ℹ️ Constraints to consider: {list(self.design_constraints.keys())}")

        # Simple validation
        if len(rationale) < 20:
            feedback.append("⚠️ Rationale could be more detailed")

        return {
            "accepted": True,
            "proposal_id": len(self.proposed_designs),
            "feedback": feedback,
            "suggestion": "Consider exploring alternative approaches before finalizing"
        }

    def _request_requirement_clarification(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Request clarification on requirements"""
        question = args["question"]
        context = args["context"]
        options = args.get("options", [])

        # In production, this could trigger user interaction
        # For now, provide heuristic responses

        response = {
            "question": question,
            "context": context,
            "clarification": "Automated response: Use best practices and common patterns unless specified otherwise",
            "recommendation": None
        }

        # Check project context for answers
        if self.project_context:
            if "standards" in self.project_context:
                response["clarification"] = f"Based on project standards: {self.project_context['standards']}"

        # If options provided, pick reasonable default
        if options:
            response["recommendation"] = options[0]
            response["clarification"] += f" Recommended: {options[0]}"

        return response

    def _get_dependency_constraints(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get dependency constraints"""
        scope = args["scope"]

        constraints = {
            "scope": scope,
            "constraints": []
        }

        # Add stored constraints
        if self.design_constraints:
            constraints["constraints"] = list(self.design_constraints.values())

        # Analyze code graph for implicit constraints
        if self.code_graph:
            # Find common imports (indicate tech stack)
            all_imports = set()
            for module in self.code_graph.modules.values():
                all_imports.update(module.imports[:5])

            constraints["existing_dependencies"] = list(all_imports)[:10]
            constraints["constraints"].append(f"Existing tech stack uses: {', '.join(list(all_imports)[:5])}")

        return constraints

    def _validate_design_decision(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a design decision"""
        decision = args["decision"]
        context = args.get("context", "")

        # Heuristic validation
        concerns = []
        recommendations = []

        # Check for anti-patterns
        if "singleton" in decision.lower():
            concerns.append("Singleton pattern can make testing difficult")
            recommendations.append("Consider dependency injection instead")

        if "global" in decision.lower():
            concerns.append("Global state can lead to coupling and testing issues")
            recommendations.append("Consider passing dependencies explicitly")

        # Check alignment with existing patterns
        if self.code_graph:
            # Could check if decision aligns with existing patterns
            recommendations.append("Ensure consistency with existing module patterns")

        return {
            "valid": len(concerns) == 0,
            "decision": decision,
            "concerns": concerns if concerns else ["No concerns identified"],
            "recommendations": recommendations if recommendations else ["Looks good!"],
            "confidence": 0.7  # Heuristic confidence
        }
