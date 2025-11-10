from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Iterable, Literal

from .errors import RulepackError

PrimitiveValue = str | int | float | bool
ConditionValue = PrimitiveValue | list[PrimitiveValue]

SelectorSource = Literal["file_metrics", "file_imports", "function_calls", "import_edges", "boundary_stats"]
ConditionOperator = Literal["equals", "not_equals", "in", "not_in", "like", "not_like", "match", "gt", "gte", "lt", "lte"]
PredicateKind = Literal["forbid", "threshold"]
ThresholdAggregator = Literal["count", "sum"]
ThresholdOperator = Literal["gt", "gte", "lt", "lte", "eq", "ne"]
Severity = Literal["info", "warn", "error"]
Enforcement = Literal["observe", "warn", "block"]


SELECTOR_FIELD_MAP: dict[SelectorSource, frozenset[str]] = {
    "file_metrics": frozenset(
        {
            "path",
            "boundary",
            "sha256",
            "size_bytes",
            "sloc",
            "class_count",
            "function_count",
            "import_count",
            "parse_ms",
        }
    ),
    "file_imports": frozenset({"path", "import_name"}),
    "function_calls": frozenset({"path", "callee_name"}),
    "import_edges": frozenset({"source_boundary", "target_name", "usage_count"}),
    "boundary_stats": frozenset({"boundary", "module_count", "total_sloc", "total_functions", "total_classes"}),
}


@dataclass(slots=True)
class RuleCondition:
    field: str
    op: ConditionOperator
    value: ConditionValue

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleCondition:
        raw_value = data["value"]
        value = list(raw_value) if isinstance(raw_value, list) else raw_value
        return cls(field=str(data["field"]), op=data["op"], value=value)


@dataclass(slots=True)
class RuleSelector:
    source: SelectorSource
    conditions: list[RuleCondition] = field(default_factory=list)

    _valid_fields: ClassVar[dict[SelectorSource, frozenset[str]]] = SELECTOR_FIELD_MAP

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleSelector:
        source = data["source"]
        conditions_data = data.get("conditions") or []
        conditions = [RuleCondition.from_dict(cond) for cond in conditions_data]
        selector = cls(source=source, conditions=conditions)
        selector._validate_fields()
        return selector

    def _validate_fields(self) -> None:
        allowed = self._valid_fields[self.source]
        invalid = [condition.field for condition in self.conditions if condition.field not in allowed]
        if invalid:
            raise RulepackError(f"Selector '{self.source}' does not support fields: {', '.join(sorted(set(invalid)))}")

    def iter_conditions(self) -> Iterable[RuleCondition]:
        return iter(self.conditions)


@dataclass(slots=True)
class RulePredicateThreshold:
    aggregator: ThresholdAggregator
    operator: ThresholdOperator
    value: float
    field: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RulePredicateThreshold:
        return cls(
            aggregator=data["aggregator"],
            operator=data["operator"],
            value=float(data["value"]),
            field=data.get("field"),
        )


@dataclass(slots=True)
class RulePredicate:
    kind: PredicateKind
    message: str | None = None
    threshold: RulePredicateThreshold | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RulePredicate:
        predicate = cls(
            kind=data["kind"],
            message=data.get("message"),
            threshold=RulePredicateThreshold.from_dict(data["threshold"]) if data.get("threshold") else None,
        )
        predicate._validate()
        return predicate

    def _validate(self) -> None:
        if self.kind == "threshold" and not self.threshold:
            raise RulepackError("Threshold predicate requires 'threshold' configuration")


@dataclass(slots=True)
class RuleDefinition:
    id: str
    description: str
    severity: Severity
    enforcement: Enforcement
    selector: RuleSelector
    predicate: RulePredicate
    category: str | None = None
    scopes: list[str] = field(default_factory=list)
    autofix: dict[str, str] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleDefinition:
        return cls(
            id=data["id"],
            description=data["description"],
            severity=data["severity"],
            enforcement=data["enforcement"],
            selector=RuleSelector.from_dict(data["selector"]),
            predicate=RulePredicate.from_dict(data["predicate"]),
            category=data.get("category"),
            scopes=list(data.get("scopes", [])),
            autofix=data.get("autofix"),
        )


@dataclass(slots=True)
class RulepackMetadata:
    id: str
    name: str
    version: str
    summary: str
    owners: list[str]
    tags: list[str] = field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RulepackMetadata:
        return cls(
            id=data["id"],
            name=data["name"],
            version=data["version"],
            summary=data["summary"],
            owners=list(data["owners"]),
            tags=list(data.get("tags", [])),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass(slots=True)
class Rulepack:
    metadata: RulepackMetadata
    rules: list[RuleDefinition]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rulepack:
        metadata = RulepackMetadata.from_dict(data["metadata"])
        rules = [RuleDefinition.from_dict(rule_data) for rule_data in data["rules"]]
        _validate_rule_ids(rules)
        return cls(metadata=metadata, rules=rules)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": {
                "id": self.metadata.id,
                "name": self.metadata.name,
                "version": self.metadata.version,
                "summary": self.metadata.summary,
                "owners": list(self.metadata.owners),
                "tags": list(self.metadata.tags),
                **({"created_at": self.metadata.created_at} if self.metadata.created_at else {}),
                **({"updated_at": self.metadata.updated_at} if self.metadata.updated_at else {}),
            },
            "rules": [self._rule_to_dict(rule) for rule in self.rules],
        }

    @staticmethod
    def _rule_to_dict(rule: RuleDefinition) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": rule.id,
            "description": rule.description,
            "severity": rule.severity,
            "enforcement": rule.enforcement,
            "selector": {
                "source": rule.selector.source,
                "conditions": [
                    {"field": cond.field, "op": cond.op, "value": cond.value} for cond in rule.selector.conditions
                ],
            },
            "predicate": {
                "kind": rule.predicate.kind,
            },
        }
        if rule.category:
            data["category"] = rule.category
        if rule.scopes:
            data["scopes"] = list(rule.scopes)
        if rule.autofix:
            data["autofix"] = dict(rule.autofix)
        if rule.predicate.message:
            data["predicate"]["message"] = rule.predicate.message
        if rule.predicate.threshold:
            threshold = rule.predicate.threshold
            threshold_payload: dict[str, Any] = {
                "aggregator": threshold.aggregator,
                "operator": threshold.operator,
                "value": threshold.value,
            }
            if threshold.field:
                threshold_payload["field"] = threshold.field
            data["predicate"]["threshold"] = threshold_payload
        return data


def _validate_rule_ids(rules: Sequence[RuleDefinition]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for rule in rules:
        if rule.id in seen:
            duplicates.append(rule.id)
        seen.add(rule.id)
    if duplicates:
        raise RulepackError(f"Duplicate rule ids found: {', '.join(sorted(set(duplicates)))}")
