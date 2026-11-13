"""Provider-neutral model routing policy for MOMO.

This module selects a configured provider profile. It does not store credentials,
instantiate SDK clients, or transmit user data.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class DataClass(str, Enum):
    PUBLIC = "public"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class ProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderProfile:
    provider_id: str
    locality: str  # "local" or "remote"
    capabilities: frozenset[str]
    allowed_data: frozenset[DataClass]
    cost_per_1k_tokens: float
    priority: int = 100
    enabled: bool = True


@dataclass(frozen=True)
class ModelRequest:
    capability: str
    data_class: DataClass
    max_cost_per_1k_tokens: float
    prefer_local: bool = True
    require_local: bool = False


class ModelRouter:
    """Select the least-exposure eligible provider under explicit constraints."""

    def select(
        self,
        request: ModelRequest,
        providers: Iterable[ProviderProfile],
    ) -> ProviderProfile:
        if request.max_cost_per_1k_tokens < 0:
            raise ValueError("Cost ceiling cannot be negative")
        if request.require_local and not request.prefer_local:
            raise ValueError("A local-only request cannot disable local preference")

        eligible: list[ProviderProfile] = []
        for provider in providers:
            if not provider.enabled:
                continue
            if provider.locality not in {"local", "remote"}:
                continue
            if request.require_local and provider.locality != "local":
                continue
            # Sensitive and restricted data never leave the device in this baseline.
            if request.data_class in {DataClass.SENSITIVE, DataClass.RESTRICTED}:
                if provider.locality != "local":
                    continue
            if request.data_class not in provider.allowed_data:
                continue
            if request.capability not in provider.capabilities:
                continue
            if provider.cost_per_1k_tokens > request.max_cost_per_1k_tokens:
                continue
            eligible.append(provider)

        if not eligible:
            raise ProviderUnavailable("No provider satisfies privacy, capability, and cost policy")

        def rank(provider: ProviderProfile) -> tuple[int, int, float, str]:
            local_penalty = 0 if (provider.locality == "local" or not request.prefer_local) else 1
            return (local_penalty, -provider.priority, provider.cost_per_1k_tokens, provider.provider_id)

        return sorted(eligible, key=rank)[0]
