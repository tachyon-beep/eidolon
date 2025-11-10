from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import psycopg
from psycopg.rows import dict_row

from .compiler import CompiledRule, CompiledRulepack, RulepackCompiler, predicate_to_dict
from .errors import RulepackError
from .loader import RulepackLoader
from .models import RulePredicate, RulePredicateThreshold, RulepackMetadata

try:  # Reuse the ingest DSN to avoid drift.
    from eidolon.codegraph.ingest import DEFAULT_DSN as CODEGRAPH_DSN
except ImportError:  # pragma: no cover - fallback for partial installs
    CODEGRAPH_DSN = "postgresql://eidolon:password@localhost:6543/eidolon"

RowFilter = Callable[[CompiledRule, list[dict[str, Any]]], list[dict[str, Any]]]

DEFAULT_DSN = CODEGRAPH_DSN


@dataclass(slots=True)
class RuleEvaluation:
    rule: CompiledRule
    passed: bool
    matches: list[dict[str, Any]]
    metric: float | None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "rule_id": self.rule.id,
            "severity": self.rule.severity,
            "enforcement": self.rule.enforcement,
            "passed": self.passed,
            "match_count": len(self.matches),
            "predicate": predicate_to_dict(self.rule.predicate),
            "matches": self.matches,
        }
        if self.rule.category:
            data["category"] = self.rule.category
        if self.rule.autofix:
            data["autofix"] = self.rule.autofix
        if self.metric is not None:
            data["metric"] = self.metric
        return data


@dataclass(slots=True)
class EvaluationReport:
    metadata: RulepackMetadata
    run_id: int
    results: list[RuleEvaluation]

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
        total = len(self.results)
        passed = sum(1 for result in self.results if result.passed)
        failed = total - passed
        return {
            "metadata": metadata,
            "run_id": self.run_id,
            "summary": {"total": total, "passed": passed, "failed": failed},
            "results": [result.to_dict() for result in self.results],
        }


class RulepackEvaluator:
    """Executes compiled rulepack selectors against the CodeGraph Postgres schema."""

    def __init__(self, *, dsn: str = DEFAULT_DSN) -> None:
        self.dsn = dsn

    def evaluate(
        self,
        compiled: CompiledRulepack,
        *,
        run_id: int,
        row_filter: RowFilter | None = None,
    ) -> EvaluationReport:
        with psycopg.connect(self.dsn, row_factory=dict_row) as conn:
            results: list[RuleEvaluation] = []
            for rule in compiled.rules:
                matches = self._execute_rule(conn, rule, run_id=run_id)
                if row_filter:
                    matches = row_filter(rule, matches)
                passed, metric = evaluate_predicate(rule.predicate, matches)
                results.append(RuleEvaluation(rule=rule, passed=passed, matches=matches, metric=metric))
        return EvaluationReport(metadata=compiled.metadata, run_id=run_id, results=results)

    def _execute_rule(self, conn: psycopg.Connection, rule: CompiledRule, *, run_id: int) -> list[dict[str, Any]]:
        params = {"run_id": run_id, **rule.parameters}
        with conn.cursor() as cur:
            cur.execute(rule.sql, params)
            rows = cur.fetchall()
        return rows


def evaluate_predicate(predicate: RulePredicate, rows: Sequence[dict[str, Any]]) -> tuple[bool, float | None]:
    """Return (passed, metric) for a predicate applied to the result rows."""
    if predicate.kind == "forbid":
        metric = float(len(rows))
        return metric == 0.0, metric
    threshold = predicate.threshold
    if not threshold:
        raise RulepackError("Threshold predicate requires threshold configuration")
    metric = _calculate_threshold_metric(threshold, rows)
    return _compare(metric, threshold.operator, threshold.value), metric


def _calculate_threshold_metric(threshold: RulePredicateThreshold, rows: Sequence[dict[str, Any]]) -> float:
    if threshold.aggregator == "count":
        return float(len(rows))
    if threshold.aggregator == "sum":
        if not threshold.field:
            raise RulepackError("Sum aggregator requires a field name")
        total = 0.0
        for row in rows:
            if threshold.field not in row:
                raise RulepackError(f"Missing field '{threshold.field}' in row for sum aggregation")
            total += float(row[threshold.field])
        return total
    raise RulepackError(f"Unsupported aggregator '{threshold.aggregator}'")


def _compare(metric: float, operator: str, target: float) -> bool:
    if operator == "gt":
        return metric > target
    if operator == "gte":
        return metric >= target
    if operator == "lt":
        return metric < target
    if operator == "lte":
        return metric <= target
    if operator == "eq":
        return metric == target
    if operator == "ne":
        return metric != target
    raise RulepackError(f"Unsupported threshold operator '{operator}'")


def evaluate_rulepack_file(
    path: Path,
    *,
    run_id: int,
    dsn: str = DEFAULT_DSN,
    row_filter: RowFilter | None = None,
) -> EvaluationReport:
    """Convenience helper to load, compile, and evaluate a pack from disk."""
    loader = RulepackLoader()
    compiler = RulepackCompiler()
    pack = loader.load(path)
    compiled = compiler.compile(pack)
    evaluator = RulepackEvaluator(dsn=dsn)
    return evaluator.evaluate(compiled, run_id=run_id, row_filter=row_filter)
