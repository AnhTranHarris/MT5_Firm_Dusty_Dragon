from dusty_dragon.analytics.capital_growth import CapitalGrowthSummary
from dusty_dragon.analytics.firm_health import (
    FirmHealthGrowthMonitor,
    FirmHealthInputs,
    FirmHealthStatus,
    ResearchPriority,
)
from dusty_dragon.analytics.performance import FirmPerformanceSummary


def growth(
    *,
    profitable: bool = True,
    drawdown: float = 2.0,
    preserved: bool = True,
) -> CapitalGrowthSummary:
    return CapitalGrowthSummary(
        starting_capital=10_000,
        ending_capital=10_500 if profitable else 9_900,
        net_growth=500 if profitable else -100,
        net_growth_pct=5.0 if profitable else -1.0,
        max_drawdown_pct=drawdown,
        profitable=profitable,
        capital_preserved=preserved,
        growth_to_drawdown=2.5 if profitable and drawdown else None,
    )


def performance(*, expectancy: float = 0.25) -> FirmPerformanceSummary:
    return FirmPerformanceSummary(
        trade_count=100,
        wins=60,
        losses=40,
        flats=0,
        win_rate=0.60,
        total_r=25.0,
        expectancy_r=expectancy,
        profit_factor_r=1.8,
        max_drawdown_r=4.0,
        forecast_samples=80,
        forecast_direction_accuracy=0.62,
        mean_forecast_error_pct=0.05,
    )


def test_healthy_firm_keeps_full_trading_risk_and_research_running():
    report = FirmHealthGrowthMonitor().evaluate(
        FirmHealthInputs(growth=growth(), performance=performance())
    )

    assert report.status == FirmHealthStatus.HEALTHY
    assert report.trading_risk_multiplier == 1.0
    assert report.research_priority == ResearchPriority.NORMAL
    assert report.research_enabled is True


def test_non_growing_capital_moves_firm_to_caution_not_research_shutdown():
    report = FirmHealthGrowthMonitor().evaluate(
        FirmHealthInputs(growth=growth(profitable=False), performance=performance())
    )

    assert report.status == FirmHealthStatus.CAUTION
    assert report.trading_risk_multiplier == 0.5
    assert report.research_priority == ResearchPriority.ELEVATED
    assert report.research_enabled is True


def test_halt_stops_new_trading_risk_but_intensifies_research():
    report = FirmHealthGrowthMonitor().evaluate(
        FirmHealthInputs(
            growth=growth(drawdown=12.0, preserved=False),
            performance=performance(expectancy=-0.2),
        )
    )

    assert report.status == FirmHealthStatus.HALT
    assert report.trading_risk_multiplier == 0.0
    assert report.research_priority == ResearchPriority.URGENT
    assert report.research_enabled is True


def test_mt5_disconnect_halts_trading_without_disabling_research():
    report = FirmHealthGrowthMonitor().evaluate(
        FirmHealthInputs(
            growth=growth(),
            performance=performance(),
            mt5_connected=False,
        )
    )

    assert report.status == FirmHealthStatus.HALT
    assert report.research_enabled is True
    assert "MT5 connectivity unavailable" in report.reasons


def test_model_or_archive_degradation_raises_caution_only():
    report = FirmHealthGrowthMonitor().evaluate(
        FirmHealthInputs(
            growth=growth(),
            performance=performance(),
            kronos_calibration_degrading=True,
            archive_healthy=False,
        )
    )

    assert report.status == FirmHealthStatus.CAUTION
    assert report.research_priority == ResearchPriority.ELEVATED
    assert report.research_enabled is True
