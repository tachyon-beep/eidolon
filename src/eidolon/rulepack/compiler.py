from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import RulepackError
from .models import (
    ConditionValue,
    RuleCondition,
    RuleDefinition,
    RulePredicate,
    Rulepack,
    RulepackMetadata,
    SelectorSource,
)


@dataclass(frozen=True)
class TableDefinition:
    name: str
    alias: str
    columns: tuple[str, ...]


TABLE_DEFINITIONS: dict[SelectorSource, TableDefinition] = {
    "file_metrics": TableDefinition(
        name="file_metrics",
        alias="fm",
        columns=("path", "boundary", "sha256", "size_bytes", "sloc", "class_count", "function_count", "import_count", "parse_ms"),
    ),
    "file_imports": TableDefinition(
        name="file_imports",
        alias="fi",
        columns=("path", "import_name"),
    ),
    "function_calls": TableDefinition(
        name="function_calls",
        alias="fc",
        columns=("path", "callee_name"),
    ),
    "import_edges": TableDefinition(
        name="import_edges",
        alias="ie",
        columns=("source_boundary", "target_name", "usage_count"),
    ),
    "boundary_stats": TableDefinition(
        name="boundary_stats",
        alias="bs",
        columns=("boundary", "module_count", "total_sloc", "total_functions", "total_classes"),
    ),
}


@dataclass(slots=True)
class CompiledRule:
    id: str
    description: str
    severity: str
    enforcement: str
    selector_source: SelectorSource
    predicate: RulePredicate
    scopes: list[str]
    category: str | None
    autofix: dict[str, str] | None
    sql: str
    parameters: dict[str, ConditionValue]

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": self.id,
            "description": self.description,
            "severity": self.severity,
            "enforcement": self.enforcement,
            "selector_source": self.selector_source,
            "sql": self.sql,
            "parameters": self.parameters,
            "predicate": predicate_to_dict(self.predicate),
            "scopes": self.scopes,
        }
        if self.category:
            payload["category"] = self.category
        if self.autofix:
            payload["autofix"] = self.autofix
        return payload


@dataclass(slots=True)
class CompiledRulepack:
    metadata: RulepackMetadata
    rules: list[CompiledRule]

    def to_dict(self) -> dict[str, Any]:
        metadata = {
            "id": self.metadata.id,
            "name": self.metadata.name,
            "version": self.metadata.version,
            "summary": self.metadata.summary,
            "owners": self.metadata.owners,
            "tags": self.metadata.tags,
        }
        if self.metadata.created_at:
            metadata["created_at"] = self.metadata.created_at
        if self.metadata.updated_at:
            metadata["updated_at"] = self.metadata.updated_at
        return {"metadata": metadata, "rules": [rule.to_dict() for rule in self.rules]}


class RulepackCompiler:
    """Compiles rulepack selectors into SQL fragments."""

    def compile(self, rulepack: Rulepack) -> CompiledRulepack:
        compiled_rules = [self._compile_rule(rule) for rule in rulepack.rules]
        return CompiledRulepack(metadata=rulepack.metadata, rules=compiled_rules)

    def _compile_rule(self, rule: RuleDefinition) -> CompiledRule:
        table = TABLE_DEFINITIONS[rule.selector.source]
        columns = ", ".join(f"{table.alias}.{col} AS {col}" for col in table.columns)
        sql_lines = [
            f"SELECT {columns}",
            f"FROM {table.name} AS {table.alias}",
            f"WHERE {table.alias}.run_id = %(run_id)s",
        ]
        parameters: dict[str, ConditionValue] = {}
        param_factory = _ParameterFactory()

        for condition in rule.selector.conditions:
            clause, clause_params = self._render_condition(condition, table.alias, param_factory)
            sql_lines.append(f"  AND {clause}")
            parameters.update(clause_params)

        sql = "\n".join(sql_lines)
        return CompiledRule(
            id=rule.id,
            description=rule.description,
            severity=rule.severity,
            enforcement=rule.enforcement,
            selector_source=rule.selector.source,
            predicate=rule.predicate,
            scopes=list(rule.scopes),
            category=rule.category,
            autofix=rule.autofix,
            sql=sql,
            parameters=parameters,
        )

    def _render_condition(
        self,
        condition: RuleCondition,
        alias: str,
        param_factory: "_ParameterFactory",
    ) -> tuple[str, dict[str, ConditionValue]]:
        op = condition.op
        field_ref = f"{alias}.{condition.field}"
        if op in {"equals", "not_equals"}:
            value = _ensure_scalar(condition, op)
            param = param_factory.new(condition.field)
            comparator = "=" if op == "equals" else "!="
            return f"{field_ref} {comparator} %({param})s", {param: value}
        if op in {"gt", "gte", "lt", "lte"}:
            value = _ensure_scalar(condition, op)
            param = param_factory.new(condition.field)
            comparator = _COMPARATORS[op]
            return f"{field_ref} {comparator} %({param})s", {param: value}
        if op == "in":
            values = _ensure_list(condition, op)
            param = param_factory.new(condition.field)
            return f"{field_ref} = ANY(%({param})s)", {param: values}
        if op == "not_in":
            values = _ensure_list(condition, op)
            param = param_factory.new(condition.field)
            return f"NOT ({field_ref} = ANY(%({param})s))", {param: values}
        if op == "like":
            value = _ensure_scalar(condition, op)
            param = param_factory.new(condition.field)
            return f"{field_ref} LIKE %({param})s", {param: value}
        if op == "not_like":
            value = _ensure_scalar(condition, op)
            param = param_factory.new(condition.field)
            return f"NOT ({field_ref} LIKE %({param})s)", {param: value}
        if op == "match":
            values = _ensure_glob_list(condition)
            param_values: dict[str, str] = {}
            fragments: list[str] = []
            for pattern in values:
                param = param_factory.new(condition.field)
                param_values[param] = pattern
                fragments.append(f"{field_ref} LIKE %({param})s ESCAPE '\\\\'")
            return "(" + " OR ".join(fragments) + ")", param_values
        raise RulepackError(f"Unsupported operator '{op}' in rule '{condition.field}'")


class _ParameterFactory:
    def __init__(self) -> None:
        self._counter = 0

    def new(self, hint: str) -> str:
        token = f"{hint}_{self._counter}"
        self._counter += 1
        return token.replace(".", "_")


_COMPARATORS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


def _ensure_scalar(condition: RuleCondition, op: str) -> Any:
    if isinstance(condition.value, list):
        raise RulepackError(f"Operator '{op}' requires a scalar value for field '{condition.field}'")
    return condition.value


def _ensure_list(condition: RuleCondition, op: str) -> list[Any]:
    if isinstance(condition.value, list):
        if not condition.value:
            raise RulepackError(f"Operator '{op}' requires at least one value for field '{condition.field}'")
        return condition.value
    raise RulepackError(f"Operator '{op}' requires a list value for field '{condition.field}'")


def _ensure_glob_list(condition: RuleCondition) -> list[str]:
    raw_values = condition.value if isinstance(condition.value, list) else [condition.value]
    if not raw_values:
        raise RulepackError(f"Glob match requires at least one pattern for field '{condition.field}'")
    patterns: list[str] = []
    for value in raw_values:
        if not isinstance(value, str):
            raise RulepackError(f"Glob match requires string patterns for field '{condition.field}'")
        patterns.append(_glob_to_like(value))
    return patterns


def _glob_to_like(pattern: str) -> str:
    """Convert a shell-style glob to a SQL LIKE pattern."""
    buffer: list[str] = []
    for char in pattern:
        if char == "*":
            buffer.append("%")
        elif char == "?":
            buffer.append("_")
        elif char == "\\":
            buffer.append("\\\\")
        elif char in {"%", "_"}:
            buffer.append(f"\\{char}")
        else:
            buffer.append(char)
    return "".join(buffer)


def predicate_to_dict(predicate: RulePredicate) -> dict[str, Any]:
        data: dict[str, Any] = {"kind": predicate.kind}
        if predicate.message:
            data["message"] = predicate.message
        if predicate.threshold:
            threshold = predicate.threshold
            payload: dict[str, Any] = {
                "aggregator": threshold.aggregator,
                "operator": threshold.operator,
                "value": threshold.value,
            }
            if threshold.field:
                payload["field"] = threshold.field
            data["threshold"] = payload
        return data
