from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


TASK_COLUMNS = (
    "id, task_type, strategy_version, payload_json, depends_json, priority, "
    "status, attempts, max_attempts, created_at, updated_at, last_error"
)


class ResearchTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class ResearchTask(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    task_type: str
    strategy_version: str
    payload: dict = Field(default_factory=dict)
    depends_on: list[UUID] = Field(default_factory=list)
    priority: int = Field(default=50, ge=0, le=100)
    status: ResearchTaskStatus = ResearchTaskStatus.PENDING
    attempts: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_error: str | None = None


@dataclass
class ResearchTaskGraph:
    """SQLite-backed research queue with dependencies, retries, and priority.

    Automaton roadmap: durable tasks survive process restarts and expose lifecycle
    state instead of living only in transient context. Degraded conditions may
    defer non-essential work without deleting it.

    Vibe-Trading roadmap: each research action remains a bounded, auditable unit
    whose urgency can follow financial/risk evidence.

    Kronos roadmap: forecast experiments become tasks; Kronos itself receives no
    scheduler, priority-policy, promotion, or execution authority.
    """

    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_tasks (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    strategy_version TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    depends_json TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 50,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_error TEXT
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(research_tasks)").fetchall()
            }
            if "priority" not in columns:
                connection.execute(
                    "ALTER TABLE research_tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 50"
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def add(self, task: ResearchTask) -> ResearchTask:
        if task.id in set(task.depends_on):
            raise ValueError("research task cannot depend on itself")
        with self._connect() as connection:
            for dependency in task.depends_on:
                row = connection.execute(
                    "SELECT 1 FROM research_tasks WHERE id = ?", (str(dependency),)
                ).fetchone()
                if row is None:
                    raise ValueError(f"dependency not found: {dependency}")
            connection.execute(
                """
                INSERT INTO research_tasks(
                    id, task_type, strategy_version, payload_json, depends_json,
                    priority, status, attempts, max_attempts, created_at, updated_at, last_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(task.id),
                    task.task_type,
                    task.strategy_version,
                    json.dumps(task.payload, sort_keys=True),
                    json.dumps([str(item) for item in task.depends_on]),
                    task.priority,
                    task.status.value,
                    task.attempts,
                    task.max_attempts,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                    task.last_error,
                ),
            )
        return task

    def claim_next(self) -> ResearchTask | None:
        """Atomically claim the highest-priority oldest runnable task."""
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                f"SELECT {TASK_COLUMNS} FROM research_tasks WHERE status = ? "
                "ORDER BY priority DESC, created_at, id",
                (ResearchTaskStatus.PENDING.value,),
            ).fetchall()
            for row in rows:
                task = self._decode(row)
                dependency_statuses = [
                    self._status(connection, item) for item in task.depends_on
                ]
                if any(
                    status in {ResearchTaskStatus.FAILED, ResearchTaskStatus.BLOCKED}
                    for status in dependency_statuses
                ):
                    self._set_status(connection, task.id, ResearchTaskStatus.BLOCKED)
                    continue
                if not all(
                    status == ResearchTaskStatus.SUCCEEDED
                    for status in dependency_statuses
                ):
                    continue
                now = datetime.now(UTC)
                cursor = connection.execute(
                    """
                    UPDATE research_tasks
                    SET status = ?, attempts = attempts + 1, updated_at = ?, last_error = NULL
                    WHERE id = ? AND status = ?
                    """,
                    (
                        ResearchTaskStatus.RUNNING.value,
                        now.isoformat(),
                        str(task.id),
                        ResearchTaskStatus.PENDING.value,
                    ),
                )
                if cursor.rowcount != 1:
                    continue
                connection.commit()
                return self.get(task.id)
            connection.commit()
        return None

    def set_priority(self, task_id: UUID, priority: int) -> ResearchTask:
        if not 0 <= priority <= 100:
            raise ValueError("priority must be between 0 and 100")
        task = self.get(task_id)
        if task is None:
            raise ValueError(f"task not found: {task_id}")
        if task.status != ResearchTaskStatus.PENDING:
            raise ValueError("only a pending task may be reprioritized")
        with self._connect() as connection:
            connection.execute(
                "UPDATE research_tasks SET priority = ?, updated_at = ? WHERE id = ?",
                (priority, datetime.now(UTC).isoformat(), str(task_id)),
            )
        updated = self.get(task_id)
        if updated is None:
            raise RuntimeError("research task disappeared")
        return updated

    def succeed(self, task_id: UUID) -> ResearchTask:
        return self._finish(task_id, ResearchTaskStatus.SUCCEEDED, None)

    def fail(self, task_id: UUID, error: str) -> ResearchTask:
        task = self.get(task_id)
        if task is None:
            raise ValueError(f"task not found: {task_id}")
        if task.status != ResearchTaskStatus.RUNNING:
            raise ValueError("only a running task may fail")
        next_status = (
            ResearchTaskStatus.FAILED
            if task.attempts >= task.max_attempts
            else ResearchTaskStatus.PENDING
        )
        return self._finish(task_id, next_status, error)

    def get(self, task_id: UUID) -> ResearchTask | None:
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT {TASK_COLUMNS} FROM research_tasks WHERE id = ?",
                (str(task_id),),
            ).fetchone()
        return self._decode(row) if row else None

    def all(self) -> list[ResearchTask]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT {TASK_COLUMNS} FROM research_tasks "
                "ORDER BY priority DESC, created_at, id"
            ).fetchall()
        return [self._decode(row) for row in rows]

    def _finish(
        self, task_id: UUID, status: ResearchTaskStatus, error: str | None
    ) -> ResearchTask:
        task = self.get(task_id)
        if task is None:
            raise ValueError(f"task not found: {task_id}")
        if task.status != ResearchTaskStatus.RUNNING:
            raise ValueError("only a running task may complete")
        with self._connect() as connection:
            connection.execute(
                "UPDATE research_tasks SET status = ?, updated_at = ?, last_error = ? WHERE id = ?",
                (status.value, datetime.now(UTC).isoformat(), error, str(task_id)),
            )
        updated = self.get(task_id)
        if updated is None:
            raise RuntimeError("research task disappeared")
        return updated

    @staticmethod
    def _status(connection: sqlite3.Connection, task_id: UUID) -> ResearchTaskStatus:
        row = connection.execute(
            "SELECT status FROM research_tasks WHERE id = ?", (str(task_id),)
        ).fetchone()
        if row is None:
            raise ValueError(f"dependency not found: {task_id}")
        return ResearchTaskStatus(row[0])

    @staticmethod
    def _set_status(
        connection: sqlite3.Connection, task_id: UUID, status: ResearchTaskStatus
    ) -> None:
        connection.execute(
            "UPDATE research_tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, datetime.now(UTC).isoformat(), str(task_id)),
        )

    @staticmethod
    def _decode(row: tuple) -> ResearchTask:
        return ResearchTask(
            id=row[0],
            task_type=row[1],
            strategy_version=row[2],
            payload=json.loads(row[3]),
            depends_on=json.loads(row[4]),
            priority=row[5],
            status=row[6],
            attempts=row[7],
            max_attempts=row[8],
            created_at=row[9],
            updated_at=row[10],
            last_error=row[11],
        )
