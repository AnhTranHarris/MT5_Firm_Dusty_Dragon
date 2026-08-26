from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any


@dataclass(frozen=True, slots=True)
class PolicyBundle:
    policy_id: str
    constitution_version: str
    raw: dict[str, Any]

    @property
    def demo(self) -> dict[str, Any]:
        return self.raw["demo"]

    @property
    def live_expansion(self) -> dict[str, Any]:
        return self.raw["live_expansion"]

    @property
    def portfolio(self) -> dict[str, Any]:
        return self.raw["portfolio"]


def load_policy(path: str | Path) -> PolicyBundle:
    policy_path = Path(path)
    with policy_path.open("rb") as handle:
        raw = tomllib.load(handle)

    policy_id = str(raw.get("policy_id", "")).strip()
    constitution_version = str(raw.get("constitution_version", "")).strip()
    if not policy_id or not constitution_version:
        raise ValueError("policy_id and constitution_version are required")

    return PolicyBundle(
        policy_id=policy_id,
        constitution_version=constitution_version,
        raw=raw,
    )
