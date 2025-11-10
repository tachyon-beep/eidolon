from __future__ import annotations

import pytest

from eidolon.orchestrator.policy_engine import TenantPolicy, merge_residency_policy


def test_merge_residency_policy_defaults() -> None:
    tenant_policy = TenantPolicy(tenant="demo", required_regions=["ap-southeast-2"], preferred_regions=["ap-southeast-2"])
    policy = merge_residency_policy(tenant_policy)
    assert policy.required_regions == ["ap-southeast-2"]
    assert policy.fallback == "block"


def test_merge_residency_policy_overrides() -> None:
    tenant_policy = TenantPolicy(tenant="demo", required_regions=["us-east-1"], preferred_regions=["us-east-1"], fallback="queue")
    overrides = {"required_regions": ["eu-central-1"], "fallback": "degrade"}
    policy = merge_residency_policy(tenant_policy, overrides)
    assert policy.required_regions == ["eu-central-1"]
    assert policy.fallback == "degrade"


def test_merge_residency_policy_requires_regions() -> None:
    tenant_policy = TenantPolicy(tenant="demo", required_regions=["us-east-1"], preferred_regions=[])
    with pytest.raises(ValueError):
        merge_residency_policy(tenant_policy, {"required_regions": []})
