from __future__ import annotations

import pytest

from eidolon.rulepack.errors import RulepackError
from eidolon.rulepack.models import RulePredicate, RulePredicateThreshold
from eidolon.rulepack.runtime import evaluate_predicate


def test_forbid_predicate_pass_fail() -> None:
    predicate = RulePredicate(kind="forbid")
    passed, metric = evaluate_predicate(predicate, [])
    assert passed is True
    assert metric == 0

    passed, metric = evaluate_predicate(predicate, [{"path": "foo.py"}])
    assert passed is False
    assert metric == 1


def test_count_threshold_predicate() -> None:
    predicate = RulePredicate(
        kind="threshold",
        threshold=RulePredicateThreshold(
            aggregator="count",
            operator="lte",
            value=2,
        ),
    )
    passed, metric = evaluate_predicate(predicate, [{"path": "a.py"}, {"path": "b.py"}])
    assert passed is True
    assert metric == 2

    passed, metric = evaluate_predicate(predicate, [{"path": "a.py"}] * 3)
    assert passed is False
    assert metric == 3


def test_sum_threshold_predicate() -> None:
    predicate = RulePredicate(
        kind="threshold",
        threshold=RulePredicateThreshold(
            aggregator="sum",
            operator="gte",
            value=10,
            field="total_sloc",
        ),
    )
    rows = [{"total_sloc": 4}, {"total_sloc": 6.5}]
    passed, metric = evaluate_predicate(predicate, rows)
    assert passed is True
    assert metric == pytest.approx(10.5)


def test_sum_threshold_requires_field() -> None:
    predicate = RulePredicate(
        kind="threshold",
        threshold=RulePredicateThreshold(
            aggregator="sum",
            operator="gte",
            value=5,
            field="total_sloc",
        ),
    )
    with pytest.raises(RulepackError):
        evaluate_predicate(predicate, [{"other": 5}])
