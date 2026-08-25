from dusty_dragon.research.executor import ResearchResultStore, ResearchTaskExecutor
from dusty_dragon.research.task_graph import ResearchTask, ResearchTaskGraph, ResearchTaskStatus


def test_executor_runs_dependency_chain_and_persists_outputs(tmp_path):
    graph = ResearchTaskGraph(tmp_path / "tasks.sqlite3")
    results = ResearchResultStore(tmp_path / "results.sqlite3")
    first = graph.add(
        ResearchTask(task_type="first", strategy_version="c1", payload={"value": 2})
    )
    second = graph.add(
        ResearchTask(
            task_type="second",
            strategy_version="c1",
            payload={"increment": 3},
            depends_on=[first.id],
        )
    )

    def first_handler(task, dependencies):
        assert dependencies == {}
        return {"value": task.payload["value"]}

    def second_handler(task, dependencies):
        prior = dependencies[first.id]["value"]
        return {"value": prior + task.payload["increment"]}

    executor = ResearchTaskExecutor(
        graph=graph,
        results=results,
        handlers={"first": first_handler, "second": second_handler},
    )

    completed = executor.run_until_idle()

    assert [item.task_id for item in completed] == [first.id, second.id]
    assert graph.get(first.id).status == ResearchTaskStatus.SUCCEEDED
    assert graph.get(second.id).status == ResearchTaskStatus.SUCCEEDED
    assert results.get(second.id).output == {"value": 5}


def test_executor_failure_is_retried_on_future_heartbeat(tmp_path):
    graph = ResearchTaskGraph(tmp_path / "tasks.sqlite3")
    results = ResearchResultStore(tmp_path / "results.sqlite3")
    task = graph.add(
        ResearchTask(task_type="flaky", strategy_version="c1", max_attempts=2)
    )
    calls = {"count": 0}

    def flaky_handler(_task, _dependencies):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary failure")
        return {"ok": True}

    executor = ResearchTaskExecutor(graph, results, {"flaky": flaky_handler})

    assert executor.run_until_idle() == []
    after_first = graph.get(task.id)
    assert after_first.status == ResearchTaskStatus.PENDING
    assert after_first.attempts == 1
    assert "temporary failure" in after_first.last_error

    completed = executor.run_until_idle()
    assert len(completed) == 1
    assert graph.get(task.id).status == ResearchTaskStatus.SUCCEEDED
    assert graph.get(task.id).attempts == 2


def test_missing_handler_fails_closed(tmp_path):
    graph = ResearchTaskGraph(tmp_path / "tasks.sqlite3")
    results = ResearchResultStore(tmp_path / "results.sqlite3")
    task = graph.add(
        ResearchTask(
            task_type="unknown",
            strategy_version="c1",
            max_attempts=1,
        )
    )

    executor = ResearchTaskExecutor(graph, results, {})

    assert executor.run_once() is None
    failed = graph.get(task.id)
    assert failed.status == ResearchTaskStatus.FAILED
    assert "KeyError" in failed.last_error
    assert results.get(task.id) is None


def test_failed_parent_blocks_child(tmp_path):
    graph = ResearchTaskGraph(tmp_path / "tasks.sqlite3")
    results = ResearchResultStore(tmp_path / "results.sqlite3")
    parent = graph.add(
        ResearchTask(task_type="parent", strategy_version="c1", max_attempts=1)
    )
    child = graph.add(
        ResearchTask(
            task_type="child",
            strategy_version="c1",
            depends_on=[parent.id],
        )
    )

    def parent_handler(_task, _dependencies):
        raise ValueError("invalid experiment")

    executor = ResearchTaskExecutor(graph, results, {"parent": parent_handler})

    assert executor.run_once() is None
    assert graph.get(parent.id).status == ResearchTaskStatus.FAILED
    assert graph.claim_next() is None
    assert graph.get(child.id).status == ResearchTaskStatus.BLOCKED


def test_result_store_survives_restart(tmp_path):
    path = tmp_path / "results.sqlite3"
    graph = ResearchTaskGraph(tmp_path / "tasks.sqlite3")
    task = graph.add(ResearchTask(task_type="one", strategy_version="c1"))
    results = ResearchResultStore(path)
    executor = ResearchTaskExecutor(
        graph,
        results,
        {"one": lambda _task, _dependencies: {"answer": 42}},
    )

    result = executor.run_once()
    assert result is not None

    reopened = ResearchResultStore(path)
    assert reopened.get(task.id).output == {"answer": 42}
