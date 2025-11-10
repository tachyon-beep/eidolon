from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import ResidencyPolicy


@dataclass(slots=True)
class TenantPolicy:
    tenant: str
    required_regions: list[str]
    preferred_regions: list[str]
    fallback: str = "block"


def merge_residency_policy(
    tenant_policy: TenantPolicy,
    plan_overrides: dict[str, Sequence[str] | str] | None = None,
) -> ResidencyPolicy:
    overrides = plan_overrides or {}
    required = list(overrides.get("required_regions", tenant_policy.required_regions))
    preferred = list(overrides.get("preferred_regions", tenant_policy.preferred_regions))
    fallback = (overrides.get("fallback") or tenant_policy.fallback)
    policy = ResidencyPolicy(required_regions=required, preferred_regions=preferred, fallback=fallback)  # type: ignore[arg-type]
    policy.validate()
    return policy
