from __future__ import annotations

import json
from typing import Any

import psycopg

from .runtime import EvaluationReport, RuleEvaluation


RESULT_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS drift_results (
        id SERIAL PRIMARY KEY,
        run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
        rulepack_id TEXT NOT NULL,
        rule_id TEXT NOT NULL,
        status TEXT NOT NULL,
        severity TEXT NOT NULL,
        enforcement TEXT NOT NULL,
        match_count INTEGER NOT NULL,
        metric DOUBLE PRECISION,
        payload JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS gatecheck_results (
        id SERIAL PRIMARY KEY,
        run_id INTEGER NOT NULL REFERENCES scan_runs(id) ON DELETE CASCADE,
        rulepack_id TEXT NOT NULL,
        rule_id TEXT NOT NULL,
        status TEXT NOT NULL,
        severity TEXT NOT NULL,
        enforcement TEXT NOT NULL,
        match_count INTEGER NOT NULL,
        metric DOUBLE PRECISION,
        context JSONB,
        payload JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
)


def ensure_result_tables(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        for stmt in RESULT_SCHEMA_STATEMENTS:
            cur.execute(stmt)
    conn.commit()


def record_drift_report(dsn: str, report: EvaluationReport) -> None:
    with psycopg.connect(dsn) as conn:
        ensure_result_tables(conn)
        with conn.cursor() as cur:
            for evaluation in report.results:
                status = _status_from_evaluation(evaluation)
                cur.execute(
                    """
                    INSERT INTO drift_results (
                        run_id, rulepack_id, rule_id, status, severity, enforcement,
                        match_count, metric, payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        report.run_id,
                        report.metadata.id,
                        evaluation.rule.id,
                        status,
                        evaluation.rule.severity,
                        evaluation.rule.enforcement,
                        len(evaluation.matches),
                        evaluation.metric,
                        json.dumps(evaluation.to_dict()),
                    ),
                )
        conn.commit()


def record_gatecheck_report(
    dsn: str,
    report: EvaluationReport,
    *,
    context: dict[str, Any] | None = None,
) -> None:
    with psycopg.connect(dsn) as conn:
        ensure_result_tables(conn)
        with conn.cursor() as cur:
            for evaluation in report.results:
                status = _status_from_evaluation(evaluation)
                cur.execute(
                    """
                    INSERT INTO gatecheck_results (
                        run_id, rulepack_id, rule_id, status, severity, enforcement,
                        match_count, metric, context, payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        report.run_id,
                        report.metadata.id,
                        evaluation.rule.id,
                        status,
                        evaluation.rule.severity,
                        evaluation.rule.enforcement,
                        len(evaluation.matches),
                        evaluation.metric,
                        json.dumps(context or {}),
                        json.dumps(evaluation.to_dict()),
                    ),
                )
        conn.commit()


def _status_from_evaluation(evaluation: RuleEvaluation) -> str:
    if evaluation.passed:
        return "pass"
    enforcement = evaluation.rule.enforcement
    if enforcement == "block":
        return "fail"
    if enforcement == "warn":
        return "warn"
    return "pass"
