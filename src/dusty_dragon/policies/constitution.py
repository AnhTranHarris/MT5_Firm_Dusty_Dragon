from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from pydantic import BaseModel, Field, model_validator


class DeskRiskPolicy(BaseModel):
    max_risk_per_trade_pct: float = Field(gt=0, le=1)
    normal_daily_halt_pct: float = Field(gt=0, le=1)
    absolute_daily_halt_pct: float = Field(gt=0, le=1)
    max_active_exposure_pct: float = Field(gt=0, le=1)
    weekly_caution_pct: float = Field(gt=0, le=1)
    weekly_defensive_pct: float = Field(gt=0, le=1)
    weekly_halt_pct: float = Field(gt=0, le=1)
    weekly_catastrophic_quarantine_pct: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> DeskRiskPolicy:
        ordered = (
            self.weekly_caution_pct,
            self.weekly_defensive_pct,
            self.weekly_halt_pct,
            self.weekly_catastrophic_quarantine_pct,
        )
        if tuple(sorted(ordered)) != ordered:
            raise ValueError("weekly risk thresholds must increase monotonically")
        if self.normal_daily_halt_pct > self.absolute_daily_halt_pct:
            raise ValueError("normal daily halt cannot exceed absolute daily halt")
        return self


class GraduationPolicy(BaseModel):
    stretch_growth_target_pct: float = Field(gt=0)
    trailing_growth_window_days: int = Field(gt=0)
    trailing_growth_stretch_pct: float = Field(gt=0)
    minimum_trade_management_quality_pct: float = Field(gt=0, le=1)
    rolling_trade_sample: int = Field(gt=0)
    capital_milestone_usd: float = Field(gt=0)
    realized_gain_giveback_block_pct: float = Field(gt=0, le=1)
    peak_equity_gain_giveback_block_pct: float = Field(gt=0, le=1)


class DemoPolicy(BaseModel):
    starting_capital_usd: float = Field(gt=0)
    qualification_trading_days: int = Field(gt=0)
    bootstrap_forward_days: int = Field(gt=0)
    selected_risk_multiplier: float = Field(ge=1)
    sunday_capital_compression_factor: float = Field(gt=0, lt=1)


class ExpansionPolicy(BaseModel):
    live_minimum_closing_equity_usd: float = Field(gt=0)
    maintenance_trading_days: int = Field(gt=0)
    review_weekday: str
    desks_per_layer: int = Field(default=6, gt=0)


class PortfolioPolicy(BaseModel):
    preferred_monthly_realized_growth_pct: float = Field(gt=0)
    capital_transfer_between_desks: bool = False
    portfolio_can_override_desk_risk: bool = False
    portfolio_can_veto_incremental_risk: bool = True


class ChallengePolicy(BaseModel):
    baseline_trading_days: int = Field(gt=0)
    campaign_trading_days: int = Field(gt=0)
    different_layer_cooldown_trading_days: int = Field(gt=0)
    challenger_has_execution_authority: bool = False


class LayerPolicy(BaseModel):
    layer2_candidate_styles: tuple[str, ...]
    layer2_slots: int = Field(default=6, gt=0)
    hardware_deferred_styles: tuple[str, ...] = ()
    layer3_sibling_variation_target_pct: float = Field(gt=0, le=1)
    layer3_broker_dependent: bool = True


class DustyConstitution(BaseModel):
    policy_id: str
    policy_version: str
    desk_risk: DeskRiskPolicy
    graduation: GraduationPolicy
    demo: DemoPolicy
    expansion: ExpansionPolicy
    portfolio: PortfolioPolicy
    challenge: ChallengePolicy
    layers: LayerPolicy


@lru_cache(maxsize=1)
def load_constitution() -> DustyConstitution:
    path = files("dusty_dragon.policies").joinpath("dusty_dragon_v1.json")
    return DustyConstitution.model_validate(json.loads(path.read_text(encoding="utf-8")))
