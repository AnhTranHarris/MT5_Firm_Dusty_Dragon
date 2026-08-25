from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from dusty_dragon.research.task_graph import ResearchTask, ResearchTaskGraph

TaskHandler = Callable[[ResearchTask, dict[UUID, Any]], Any]


class ResearchTaskResult(BaseModel):
    task_id: UUID
    task_type: str
    strategy_version: str
    output: Any
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ResearchResultStore:
    """Durable outputs for the research DAG, separate from task lifecycle state."""

    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_results (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    strategy_version TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    completed_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def put(self, result: ResearchTaskResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_results(
                    task_id, task_type, strategy_version, output_json, completed_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    task_type = excluded.task_type,
                    strategy_version = excluded.strategy_version,
                    output_json = excluded.output_json,
                    completed_at = excluded.completed_at
                """,
                (
                    str(result.task_id),
                    result.task_type,
                    result.strategy_version,
                    json.dumps(result.output, sort_keys=True, default=str),
                    result.completed_at.isoformat(),
                ),
            )

    def get(self, task_id: UUID) -> ResearchTaskResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT task_id, task_type, strategy_version, output_json, completed_at "
                "FROM research_results WHERE task_id = ?",
                (str(task_id),),
            ).fetchone()
        if row is None:
            return None
        return ResearchTaskResult(
            task_id=row[0],
            task_type=row[1],
            strategy_version=row[2],
            output=json.loads(row[3]),
            completed_at=row[4],
        )


@dataclass
class ResearchTaskExecutor:
    """Claim and execute one runnable research task at a time.

    Automaton roadmap: durable workers claim bounded tasks and persist lifecycle
    transitions. Vibe-Trading roadmap: quantitative stages remain explicit and
    independently auditable. Kronos roadmap: forecast work may be registered as
    a handler, but the executor grants no order or promotion authority.
    """

    graph: ResearchTaskGraph
    results: ResearchResultStore
    handlers: dict[str, TaskHandler]

    def run_once(self) -> ResearchTaskResult | None:
        task = self.graph.claim_next()
        if task is None:
            return None
        try:
            handler = self.handlers[task.task_type]
            dependency_outputs = self._dependency_outputs(task)
            output = handler(task, dependency_outputs)
            result = ResearchTaskResult(
                task_id=task.id,
                task_type=task.task_type,
                strategy_version=task.strategy_version,
                output=output,
            )
            self.results.put(result)
            self.graph.succeed(task.id)
            return result
        except Exception as exc:  # noqa: BLE001 - worker boundary must not strand RUNNING tasks
            self.graph.fail(task.id, f"{type(exc).__name__}: {exc}")
            return None

    def run_until_idle(self, *, max_tasks: int = 100) -> list[ResearchTaskResult]:
        """Run successful tasks until idle or until one task needs a retry.

        A failed task is intentionally retried by a future heartbeat rather than
        immediately in a tight loop. This preserves observable retry state and
        avoids a single broken experiment monopolizing the weekend worker.
        """
        if max_tasks <= 0:
            raise ValueError("max_tasks must be positive")
        completed: list[ResearchTaskResult] = []
        for _ in range(max_tasks):
            result = self.run_once()
            if result is None:
                break
            completed.append(result)
        return completed

    def _dependency_outputs(self, task: ResearchTask) -> dict[UUID, Any]:
        outputs: dict[UUID, Any] = {}
        for dependency_id in task.depends_on:
            result = self.results.get(dependency_id)
            if result is None:
                raise RuntimeError(f"missing result for succeeded dependency {dependency_id}")
            outputs[dependency_id] = result.output
        return outputs
