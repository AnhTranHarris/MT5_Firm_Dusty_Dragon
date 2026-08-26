from uuid import uuid4

import pytest

from dusty_dragon.research.stage_handlers import ResearchStageHandlers
from dusty_dragon.research.task_graph import ResearchTask


def make_handlers():
    return ResearchStageHandlers(
        campaign_runner=lambda payload: {"campaign": payload["runs_per_symbol"]},
        cost_regime_runner=lambda _payload, prior: {"costed": prior["campaign"]},
        champion_comparison_runner=lambda _payload, prior: {"compared": prior["costed"]},
        sunday_validation_runner=lambda _payload, prior: {"validated": prior["compared"]},
    ).handlers()


def test_handlers_execute_full_research_chain_contracts():
    handlers = make_handlers()
    campaign_task = ResearchTask(
        task_type="backtest_campaign",
        strategy_version="c1",
        payload={
            "runs_per_symbol": 12,
            "prior_week_min": 1,
            "prior_week_max": 8,
            "include_unused_symbol_counterfactuals": True,
        },
    )
    campaign = handlers["backtest_campaign"](campaign_task, {})
    dependency = uuid4()

    cost_task = ResearchTask(task_type="cost_regime_evaluation", strategy_version="c1")
    costed = handlers["cost_regime_evaluation"](cost_task, {dependency: campaign})

    comparison_task = ResearchTask(task_type="champion_comparison", strategy_version="c1")
    compared = handlers["champion_comparison"](comparison_task, {dependency: costed})

    sunday_task = ResearchTask(
        task_type="sunday_validation",
        strategy_version="c1",
        payload={"promotion_authority": False},
    )
    validated = handlers["sunday_validation"](sunday_task, {dependency: compared})

    assert validated == {"validated": 12}


def test_campaign_rejects_thin_or_malformed_evidence_protocol():
    handler = make_handlers()["backtest_campaign"]

    with pytest.raises(ValueError, match="10-20"):
        handler(
            ResearchTask(
                task_type="backtest_campaign",
                strategy_version="c1",
                payload={
                    "runs_per_symbol": 5,
                    "prior_week_min": 1,
                    "prior_week_max": 8,
                    "include_unused_symbol_counterfactuals": True,
                },
            ),
            {},
        )

    with pytest.raises(ValueError, match="unused-symbol"):
        handler(
            ResearchTask(
                task_type="backtest_campaign",
                strategy_version="c1",
                payload={
                    "runs_per_symbol": 12,
                    "prior_week_min": 1,
                    "prior_week_max": 8,
                    "include_unused_symbol_counterfactuals": False,
                },
            ),
            {},
        )


def test_sunday_validation_rejects_promotion_authority():
    handler = make_handlers()["sunday_validation"]
    task = ResearchTask(
        task_type="sunday_validation",
        strategy_version="c1",
        payload={"promotion_authority": True},
    )

    with pytest.raises(PermissionError, match="promotion authority"):
        handler(task, {uuid4(): {"compared": 12}})


def test_downstream_stage_requires_exactly_one_dependency():
    handler = make_handlers()["champion_comparison"]
    task = ResearchTask(task_type="champion_comparison", strategy_version="c1")

    with pytest.raises(ValueError, match="exactly one"):
        handler(task, {})
