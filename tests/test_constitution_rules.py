from dusty_dragon.domain.models import (
    CohortOutcome,
    DeskExpansionEvidence,
    DeskHealth,
    DeskQualification,
    EquityClose,
    GraduationLevel,
    OrderIntent,
    RiskAssessment,
)
from dusty_dragon.governance.rules import (
    authorize_order,
    cohort_credit,
    demo_compressed_capital,
    live_expansion_eligible,
)


def _closes(values: list[float]) -> tuple[EquityClose, ...]:
    return tuple(
        EquityClose(trading_day=f"D{index + 1}", closing_equity=value)
        for index, value in enumerate(values)
    )


def test_atomic_cohort_all_pass_counts_all_members() -> None:
    desks = [
        DeskQualification("D1", CohortOutcome.PASS, GraduationLevel.MULTIDAY),
        DeskQualification("D2", CohortOutcome.PASS, GraduationLevel.WEEKLY),
        DeskQualification("D3", CohortOutcome.PASS, GraduationLevel.MULTIDAY),
    ]
    assert cohort_credit(desks, minimum_level=GraduationLevel.MULTIDAY) == 3


def test_one_valid_failure_zeroes_entire_cohort_credit() -> None:
    desks = [
        DeskQualification("D1", CohortOutcome.PASS, GraduationLevel.MULTIDAY),
        DeskQualification("D2", CohortOutcome.FAIL, GraduationLevel.MULTIDAY),
        DeskQualification("D3", CohortOutcome.PASS, GraduationLevel.WEEKLY),
    ]
    assert cohort_credit(desks, minimum_level=GraduationLevel.MULTIDAY) == 0


def test_below_required_graduation_zeroes_cohort_credit() -> None:
    desks = [
        DeskQualification("D1", CohortOutcome.PASS, GraduationLevel.MULTIDAY),
        DeskQualification("D2", CohortOutcome.PASS, GraduationLevel.HOLD_2D),
    ]
    assert cohort_credit(desks, minimum_level=GraduationLevel.MULTIDAY) == 0


def test_live_expansion_requires_each_desk_to_hold_5000_for_seven_days() -> None:
    desks = [
        DeskExpansionEvidence("D1", _closes([5100, 5200, 5150, 5300, 5250, 5400, 5500])),
        DeskExpansionEvidence("D2", _closes([5000, 5010, 5020, 5030, 5040, 5050, 5060])),
    ]
    assert live_expansion_eligible(desks, minimum_equity=5000, maintenance_days=7)


def test_4999_99_on_seventh_day_blocks_expansion() -> None:
    desk = DeskExpansionEvidence(
        "D1",
        _closes([5100, 5200, 5150, 5300, 5250, 5400, 4999.99]),
    )
    assert not live_expansion_eligible([desk], minimum_equity=5000, maintenance_days=7)


def test_aggregate_equity_cannot_subsidize_weak_desk() -> None:
    desks = [
        DeskExpansionEvidence("D1", _closes([7000] * 7)),
        DeskExpansionEvidence("D2", _closes([3000] * 7)),
    ]
    assert not live_expansion_eligible(desks, minimum_equity=5000, maintenance_days=7)


def test_halted_desk_blocks_expansion_even_with_sufficient_equity() -> None:
    desk = DeskExpansionEvidence(
        "D1",
        _closes([6000] * 7),
        health=DeskHealth.HALTED,
    )
    assert not live_expansion_eligible([desk], minimum_equity=5000, maintenance_days=7)


def test_order_requires_both_desk_and_portfolio_risk_approval() -> None:
    intent = OrderIntent("D1", "FX.EURUSD@BROKER", "BUY", 0.01)
    desk_pass = RiskAssessment(True, "desk risk passed")
    portfolio_pass = RiskAssessment(True, "portfolio risk passed")
    portfolio_fail = RiskAssessment(False, "correlated exposure")

    approved = authorize_order(
        intent,
        desk_risk=desk_pass,
        portfolio_risk=portfolio_pass,
        policy_id="financial_v1",
    )
    rejected = authorize_order(
        intent,
        desk_risk=desk_pass,
        portfolio_risk=portfolio_fail,
        policy_id="financial_v1",
    )

    assert approved is not None
    assert approved.policy_id == "financial_v1"
    assert rejected is None


def test_demo_capital_compression_is_exact_external_flow_calculation() -> None:
    assert demo_compressed_capital(20_000, 0.75) == 15_000
