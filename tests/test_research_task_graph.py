from dusty_dragon.research.task_graph import (
    ResearchTask,
    ResearchTaskGraph,
    ResearchTaskStatus,
)


def test_task_dependency_blocks_child_until_parent_succeeds(tmp_path):
    graph = ResearchTaskGraph(tmp_path / "tasks.db")
    parent = graph.add(ResearchTask(task_type="factor_scan", strategy_version="generalist-v0"))
    child = graph.add(
        ResearchTask(
            task_type="campaign_backtest",
            strategy_version="generalist-v0",
            depends_on=[parent.id],
        )
    )

    claimed = graph.claim_next()
    assert claimed is not None and claimed.id == parent.id
    assert graph.claim_next() is None

    graph.succeed(parent.id)
    claimed_child = graph.claim_next()
    assert claimed_child is not None and claimed_child.id == child.id


def test_failed_task_retries_until_attempt_limit(tmp_path):
    graph = ResearchTaskGraph(tmp_path / "tasks.db")
    task = graph.add(
        ResearchTask(task_type="kronos_horizon", strategy_version="generalist-v1", max_attempts=2)
    )

    first = graph.claim_next()
    assert first is not None and first.attempts == 1
    retried = graph.fail(task.id, "temporary failure")
    assert retried.status == ResearchTaskStatus.PENDING
    assert retried.last_error == "temporary failure"

    second = graph.claim_next()
    assert second is not None and second.attempts == 2
    failed = graph.fail(task.id, "still broken")
    assert failed.status == ResearchTaskStatus.FAILED


def test_failed_dependency_marks_descendant_blocked(tmp_path):
    graph = ResearchTaskGraph(tmp_path / "tasks.db")
    parent = graph.add(
        ResearchTask(task_type="forecast_test", strategy_version="v1", max_attempts=1)
    )
    child = graph.add(
        ResearchTask(task_type="promotion_compare", strategy_version="v1", depends_on=[parent.id])
    )

    graph.claim_next()
    graph.fail(parent.id, "permanent failure")
    assert graph.claim_next() is None
    blocked = graph.get(child.id)
    assert blocked is not None
    assert blocked.status == ResearchTaskStatus.BLOCKED


def test_task_graph_persists_across_instances(tmp_path):
    path = tmp_path / "tasks.db"
    first = ResearchTaskGraph(path)
    task = first.add(ResearchTask(task_type="robustness", strategy_version="v2"))

    reopened = ResearchTaskGraph(path)
    restored = reopened.get(task.id)
    assert restored is not None
    assert restored.task_type == "robustness"
    assert restored.status == ResearchTaskStatus.PENDING
