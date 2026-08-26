from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import UUID

from dusty_dragon.learning.strategy_lineage import (
    PromotionEvidence,
    StrategyRecord,
    StrategyStatus,
)


class StrategyRegistry:
    """Durable champion/challenger lineage for Dusty Dragon strategies.

    Automaton reference: retain explicit parent-child lineage and lifecycle state.
    Dusty Dragon deliberately changes the autonomy model: a challenger never
    mutates the champion in place and promotion requires completed validation.

    Vibe-Trading reference: governance state is persisted and auditable.
    Kronos model settings may live inside strategy config, but Kronos has no
    promotion authority.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS strategies (
                    id TEXT PRIMARY KEY,
                    version TEXT NOT NULL UNIQUE,
                    parent_id TEXT,
                    generation INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    config_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS promotions (
                    strategy_id TEXT PRIMARY KEY,
                    evidence_json TEXT NOT NULL,
                    promoted_at TEXT NOT NULL
                )
                """
            )

    def register_founder(self, version: str, config: dict) -> StrategyRecord:
        if self.all():
            raise ValueError("founder strategy may only be registered in an empty registry")
        record = StrategyRecord(
            version=version,
            generation=0,
            status=StrategyStatus.CHAMPION,
            config=config,
        )
        self._insert(record)
        return record

    def create_challenger(self, parent_id: UUID, version: str, config: dict) -> StrategyRecord:
        parent = self.get(parent_id)
        if parent is None:
            raise ValueError(f"parent strategy not found: {parent_id}")
        record = StrategyRecord(
            version=version,
            parent_id=parent.id,
            generation=parent.generation + 1,
            status=StrategyStatus.CHALLENGER,
            config=config,
        )
        self._insert(record)
        return record

    def promote(self, strategy_id: UUID, evidence: PromotionEvidence) -> StrategyRecord:
        challenger = self.get(strategy_id)
        if challenger is None:
            raise ValueError(f"strategy not found: {strategy_id}")
        if challenger.status != StrategyStatus.CHALLENGER:
            raise ValueError("only a challenger may be promoted")
        if not evidence.complete:
            raise ValueError("promotion evidence is incomplete")

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE strategies SET status = ? WHERE status = ?",
                (StrategyStatus.RETIRED.value, StrategyStatus.CHAMPION.value),
            )
            connection.execute(
                "UPDATE strategies SET status = ? WHERE id = ?",
                (StrategyStatus.CHAMPION.value, str(strategy_id)),
            )
            connection.execute(
                """
                INSERT INTO promotions(strategy_id, evidence_json, promoted_at)
                VALUES (?, ?, datetime('now'))
                """,
                (
                    str(strategy_id),
                    json.dumps(evidence.model_dump(mode="json"), sort_keys=True),
                ),
            )
            connection.commit()
        promoted = self.get(strategy_id)
        if promoted is None:
            raise RuntimeError("promoted strategy disappeared from registry")
        return promoted

    def reject(self, strategy_id: UUID) -> StrategyRecord:
        record = self.get(strategy_id)
        if record is None:
            raise ValueError(f"strategy not found: {strategy_id}")
        if record.status != StrategyStatus.CHALLENGER:
            raise ValueError("only a challenger may be rejected")
        with self._connect() as connection:
            connection.execute(
                "UPDATE strategies SET status = ? WHERE id = ?",
                (StrategyStatus.REJECTED.value, str(strategy_id)),
            )
        rejected = self.get(strategy_id)
        if rejected is None:
            raise RuntimeError("rejected strategy disappeared from registry")
        return rejected

    def champion(self) -> StrategyRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM strategies WHERE status = ?",
                (StrategyStatus.CHAMPION.value,),
            ).fetchone()
        return self._decode(row) if row else None

    def get(self, strategy_id: UUID) -> StrategyRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM strategies WHERE id = ?",
                (str(strategy_id),),
            ).fetchone()
        return self._decode(row) if row else None

    def children(self, parent_id: UUID) -> list[StrategyRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM strategies WHERE parent_id = ? ORDER BY created_at, version",
                (str(parent_id),),
            ).fetchall()
        return [self._decode(row) for row in rows]

    def all(self) -> list[StrategyRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM strategies ORDER BY generation, created_at, version"
            ).fetchall()
        return [self._decode(row) for row in rows]

    def _insert(self, record: StrategyRecord) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO strategies(
                        id, version, parent_id, generation, created_at, status, config_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(record.id),
                        record.version,
                        str(record.parent_id) if record.parent_id else None,
                        record.generation,
                        record.created_at.isoformat(),
                        record.status.value,
                        json.dumps(record.config, sort_keys=True, separators=(",", ":")),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"strategy version already exists: {record.version}") from exc

    @staticmethod
    def _decode(row: tuple) -> StrategyRecord:
        return StrategyRecord(
            id=row[0],
            version=row[1],
            parent_id=row[2],
            generation=row[3],
            created_at=row[4],
            status=row[5],
            config=json.loads(row[6]),
        )
