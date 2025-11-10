from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Mapping

from .models import MetadataContext


def _derive_trace_id(tenant: str, run_id: str) -> str:
    h = hashlib.sha256()
    h.update(tenant.encode("utf-8"))
    h.update(run_id.encode("utf-8"))
    return h.hexdigest()[:24]


def _random_span_id() -> str:
    return secrets.token_hex(8)


def build_context(tenant: str, repo: str, run_id: str, task_id: str, parent_span_id: str | None = None) -> MetadataContext:
    trace_id = _derive_trace_id(tenant, run_id)
    span_id = _random_span_id()
    return MetadataContext(trace_id=trace_id, span_id=span_id, parent_span_id=parent_span_id, task_id=task_id)


def inject_env(context: MetadataContext, metadata: Mapping[str, str]) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "EID_TRACE_ID": context.trace_id,
            "EID_SPAN_ID": context.span_id,
            "EID_PARENT_SPAN_ID": context.parent_span_id or "",
            "EID_TASK_ID": context.task_id,
            "EID_TENANT": metadata.get("tenant", ""),
            "EID_REPO": metadata.get("repo", ""),
            "EID_RUN_ID": metadata.get("run_id", ""),
        }
    )
    if context.residency_fallback:
        env["EID_RESIDENCY_FALLBACK"] = context.residency_fallback
    return env
