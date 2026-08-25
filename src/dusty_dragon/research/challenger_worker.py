from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from dusty_dragon.learning.strategy_lineage import StrategyRecord
from dusty_dragon.research.factors import FactorSnapshot
from dusty_dragon.research.weekend import WeekendResearchBrief
from dusty_dragon.storage.strategy_registry import StrategyRegistry


class ChallengerHypothesis(BaseModel):
    code: str
    explanation: str
    mutations: dict[str, Any] = Field(default_factory=dict)


class ChallengerResearchResult(BaseModel):
    eligible: bool
    hypotheses: list[ChallengerHypothesis] = Field(default_factory=list)
    challengers: list[StrategyRecord] = Field(default_factory=list)


@dataclass(frozen=True)
class ChallengerResearchWorker:
    """Generate bounded descendant strategies from explicit weekend evidence.

    Automaton roadmap: a scheduled worker converts durable observations into
    explicit tasks/descendants. Dusty Dragon changes the autonomy boundary:
    this worker may create challengers only; it cannot promote or modify the
    active champion in place.

    Vibe-Trading roadmap: mutations target documented research/risk failures.
    Kronos roadmap: forecast weighting and horizon are tunable hypotheses, not
    assumed sources of edge.
    """

    registry: StrategyRegistry
    maximum_challengers: int = 4

    def __post_init__(self) -> None:
        if self.maximum_challengers <= 0:
            raise ValueError("maximum_challengers must be positive")

    def run(
        self,
        *,
        champion: StrategyRecord,
        brief: WeekendResearchBrief,
        factor_snapshot: FactorSnapshot | None = None,
    ) -> ChallengerResearchResult:
        if not brief.eligible_for_challenger_research:
            return ChallengerResearchResult(eligible=False)

        hypotheses = self._hypotheses(brief, factor_snapshot)
        challengers: list[StrategyRecord] = []
        for index, hypothesis in enumerate(hypotheses[: self.maximum_challengers], start=1):
            config = deepcopy(champion.config)
            config.setdefault("research", {})
            config["research"] = {
                **config["research"],
                "hypothesis_code": hypothesis.code,
                "hypothesis_explanation": hypothesis.explanation,
            }
            self._deep_merge(config, hypothesis.mutations)
            version = f"{champion.version}-c{champion.generation + 1}.{index}"
            challengers.append(
                self.registry.create_challenger(
                    champion.id,
                    version,
                    config,
                )
            )
        return ChallengerResearchResult(
            eligible=True,
            hypotheses=hypotheses,
            challengers=challengers,
        )

    @staticmethod
    def _hypotheses(
        brief: WeekendResearchBrief,
        factor_snapshot: FactorSnapshot | None,
    ) -> list[ChallengerHypothesis]:
        hypotheses: list[ChallengerHypothesis] = []
        codes = {priority.code for priority in brief.priorities}

        if "KRONOS_DIRECTION_CALIBRATION" in codes:
            hypotheses.extend(
                [
                    ChallengerHypothesis(
                        code="LOWER_KRONOS_WEIGHT",
                        explanation="Reduce forecast dominance when recorded direction calibration is weak.",
                        mutations={"signals": {"kronos_weight": 0.25}},
                    ),
                    ChallengerHypothesis(
                        code="SHORTER_KRONOS_HORIZON",
                        explanation="Test a shorter forecast horizon against the same validation campaign.",
                        mutations={"kronos": {"horizon_bars": 2}},
                    ),
                ]
            )

        if "OVERFIT_RISK" in codes or "TEMPORAL_ROBUSTNESS" in codes:
            hypotheses.append(
                ChallengerHypothesis(
                    code="HIGHER_ABSTENTION_THRESHOLD",
                    explanation="Require stronger evidence agreement to reduce time-specific or overfit entries.",
                    mutations={"signals": {"minimum_confidence": 0.65}},
                )
            )

        if "DRAWDOWN_CONTROL" in codes:
            hypotheses.append(
                ChallengerHypothesis(
                    code="LOWER_TRADE_RISK",
                    explanation="Reduce per-trade risk while keeping signal logic unchanged.",
                    mutations={"risk": {"risk_pct": 0.20}},
                )
            )

        if factor_snapshot is not None and factor_snapshot.regime.endswith("high_vol"):
            hypotheses.append(
                ChallengerHypothesis(
                    code="HIGH_VOL_FILTER",
                    explanation="Require greater selectivity in the currently observed high-volatility regime.",
                    mutations={"signals": {"high_volatility_minimum_confidence": 0.70}},
                )
            )

        if not hypotheses:
            hypotheses.append(
                ChallengerHypothesis(
                    code="ROBUSTNESS_CONTROL",
                    explanation="Create a minimally changed control challenger for robustness comparison.",
                    mutations={"research": {"control_challenger": True}},
                )
            )
        return hypotheses

    @staticmethod
    def _deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> None:
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                ChallengerResearchWorker._deep_merge(target[key], value)
            else:
                target[key] = deepcopy(value)
