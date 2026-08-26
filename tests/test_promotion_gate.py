from dusty_dragon.learning.challenger_evaluator import ChallengerComparison
from dusty_dragon.learning.promotion_gate import CampaignPromotionGate


def test_passing_campaign_only_satisfies_backtest_and_comparison_gates():
    comparison = ChallengerComparison(
        passed=True,
        champion_mean_return_pct=0.05,
        challenger_mean_return_pct=0.08,
        improvement_pct_points=0.03,
        champion_profitable_rate=0.65,
        challenger_profitable_rate=0.70,
        challenger_worst_return_pct=-0.10,
    )

    evidence = CampaignPromotionGate().evidence(comparison)

    assert evidence.backtest_passed is True
    assert evidence.compared_to_champion is True
    assert evidence.walk_forward_passed is False
    assert evidence.paper_passed is False
    assert evidence.capital_growth_passed is False
    assert evidence.complete is False


def test_full_promotion_evidence_requires_capital_growth_and_forward_gates():
    comparison = ChallengerComparison(passed=True, improvement_pct_points=0.03)

    evidence = CampaignPromotionGate().evidence(
        comparison,
        walk_forward_passed=True,
        paper_passed=True,
        capital_growth_passed=True,
    )

    assert evidence.complete is True


def test_tidy_but_unprofitable_challenger_cannot_be_complete():
    comparison = ChallengerComparison(passed=True, improvement_pct_points=0.03)

    evidence = CampaignPromotionGate().evidence(
        comparison,
        walk_forward_passed=True,
        paper_passed=True,
        capital_growth_passed=False,
    )

    assert evidence.backtest_passed is True
    assert evidence.complete is False


def test_failed_campaign_cannot_claim_historical_validation():
    comparison = ChallengerComparison(
        passed=False,
        reasons=["challenger worst-run return breaches downside threshold"],
    )

    evidence = CampaignPromotionGate().evidence(
        comparison,
        walk_forward_passed=True,
        paper_passed=True,
        capital_growth_passed=True,
    )

    assert evidence.backtest_passed is False
    assert evidence.compared_to_champion is False
    assert evidence.complete is False
    assert "campaign comparison failed" in evidence.notes
