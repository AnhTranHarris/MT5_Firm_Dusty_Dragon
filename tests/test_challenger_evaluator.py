from dusty_dragon.backtest.campaign_evaluator import CampaignEvaluation
from dusty_dragon.learning.challenger_evaluator import ChallengerCampaignComparator


def campaign(
    *,
    mean: float,
    profitable_rate: float,
    worst: float,
    regime_mean: float,
) -> CampaignEvaluation:
    return CampaignEvaluation(
        experiment_count=20,
        profitable_after_cost_count=int(20 * profitable_rate),
        profitable_after_cost_rate=profitable_rate,
        mean_cost_adjusted_return_pct=mean,
        worst_cost_adjusted_return_pct=worst,
        regime_mean_returns={"trend_low_vol": regime_mean},
        symbol_mean_returns={"EURUSD": mean},
    )


def test_stronger_cost_adjusted_challenger_passes():
    champion = campaign(mean=0.05, profitable_rate=0.65, worst=-0.10, regime_mean=0.05)
    challenger = campaign(mean=0.08, profitable_rate=0.70, worst=-0.12, regime_mean=0.08)

    result = ChallengerCampaignComparator().compare(champion, challenger)

    assert result.passed is True
    assert result.improvement_pct_points == 0.03
    assert result.reasons == []


def test_challenger_with_better_average_but_bad_tail_fails():
    champion = campaign(mean=0.05, profitable_rate=0.65, worst=-0.10, regime_mean=0.05)
    challenger = campaign(mean=0.10, profitable_rate=0.70, worst=-0.40, regime_mean=0.10)

    result = ChallengerCampaignComparator().compare(champion, challenger)

    assert result.passed is False
    assert "challenger worst-run return breaches downside threshold" in result.reasons


def test_challenger_regime_regression_fails_even_if_average_improves():
    champion = campaign(mean=0.05, profitable_rate=0.65, worst=-0.10, regime_mean=0.15)
    challenger = campaign(mean=0.08, profitable_rate=0.70, worst=-0.10, regime_mean=0.00)

    result = ChallengerCampaignComparator().compare(champion, challenger)

    assert result.passed is False
    assert any("materially regresses in regimes" in reason for reason in result.reasons)


def test_insufficient_campaign_evidence_fails_closed():
    champion = campaign(mean=0.05, profitable_rate=0.65, worst=-0.10, regime_mean=0.05)
    challenger = campaign(mean=0.08, profitable_rate=0.70, worst=-0.10, regime_mean=0.08)
    challenger = challenger.model_copy(update={"experiment_count": 5})

    result = ChallengerCampaignComparator(minimum_experiments=10).compare(
        champion, challenger
    )

    assert result.passed is False
    assert "challenger campaign has insufficient experiments" in result.reasons
