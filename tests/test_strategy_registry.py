import pytest

from dusty_dragon.learning.strategy_lineage import PromotionEvidence, StrategyStatus
from dusty_dragon.storage.strategy_registry import StrategyRegistry


def test_founder_is_first_generation_champion(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")

    founder = registry.register_founder("generalist-v0", {"kronos_weight": 0.5})

    assert founder.generation == 0
    assert founder.status == StrategyStatus.CHAMPION
    assert registry.champion().id == founder.id


def test_challenger_records_parent_and_generation(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    founder = registry.register_founder("generalist-v0", {})

    child = registry.create_challenger(
        founder.id,
        "generalist-v1-candidate",
        {"kronos_weight": 0.6},
    )

    assert child.parent_id == founder.id
    assert child.generation == 1
    assert child.status == StrategyStatus.CHALLENGER
    assert registry.children(founder.id)[0].id == child.id


def test_incomplete_evidence_cannot_replace_champion(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    founder = registry.register_founder("generalist-v0", {})
    child = registry.create_challenger(founder.id, "generalist-v1-candidate", {})

    with pytest.raises(ValueError, match="incomplete"):
        registry.promote(
            child.id,
            PromotionEvidence(backtest_passed=True, walk_forward_passed=True),
        )

    assert registry.champion().id == founder.id


def test_complete_validation_promotes_challenger_and_retires_old_champion(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    founder = registry.register_founder("generalist-v0", {})
    child = registry.create_challenger(founder.id, "generalist-v1-candidate", {})

    promoted = registry.promote(
        child.id,
        PromotionEvidence(
            backtest_passed=True,
            walk_forward_passed=True,
            paper_passed=True,
            compared_to_champion=True,
            capital_growth_passed=True,
            notes="validated against frozen champion with positive capital growth",
        ),
    )

    assert promoted.status == StrategyStatus.CHAMPION
    assert registry.champion().id == child.id
    assert registry.get(founder.id).status == StrategyStatus.RETIRED


def test_rejected_challenger_cannot_be_promoted(tmp_path):
    registry = StrategyRegistry(tmp_path / "strategies.sqlite3")
    founder = registry.register_founder("generalist-v0", {})
    child = registry.create_challenger(founder.id, "bad-v1", {})
    registry.reject(child.id)

    with pytest.raises(ValueError, match="only a challenger"):
        registry.promote(
            child.id,
            PromotionEvidence(
                backtest_passed=True,
                walk_forward_passed=True,
                paper_passed=True,
                compared_to_champion=True,
                capital_growth_passed=True,
            ),
        )
