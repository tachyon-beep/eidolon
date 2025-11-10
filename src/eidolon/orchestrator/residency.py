from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .models import ResidencyPolicy


@dataclass(slots=True)
class TenantResidencyConfig:
    tenant: str
    required_regions: list[str]
    preferred_regions: list[str]
    fallback: str = "block"


def merge_residency(
    tenant_config: TenantResidencyConfig,
    plan_overrides: dict[str, str | Sequence[str]] | None = None,
) -> ResidencyPolicy:
    required = list(plan_overrides.get("required_regions", tenant_config.required_regions)) if plan_overrides else list(tenant_config.required_regions)
    preferred = list(plan_overrides.get("preferred_regions", tenant_config.preferred_regions)) if plan_overrides else list(tenant_config.preferred_regions)
    fallback = str(plan_overrides.get("fallback", tenant_config.fallback)) if plan_overrides else tenant_config.fallback
    policy = ResidencyPolicy(required_regions=required, preferred_regions=preferred, fallback=fallback)  # type: ignore[arg-type]
    policy.validate()
    return policy
