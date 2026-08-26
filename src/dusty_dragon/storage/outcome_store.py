from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from dusty_dragon.learning.outcomes import TradeOutcome


class TradeOutcomeStore:
    """Append-once outcome persistence for future learning and analytics.

    Each trade may receive exactly one terminal outcome record. The serialized
    payload is hashed so corruption can be detected independently of the trade
    decision ledger. Later firm analytics may read this table but must not edit
    historical outcomes in place.
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
                CREATE TABLE IF NOT EXISTS trade_outcomes (
                    trade_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    closed_at TEXT NOT NULL
                )
                """
            )

    def append(self, outcome: TradeOutcome) -> str:
        payload = outcome.model_dump(mode="json")
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO trade_outcomes(trade_id, payload_json, payload_hash, closed_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (str(outcome.trade_id), payload_json, payload_hash, outcome.closed_at.isoformat()),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"outcome already recorded for trade {outcome.trade_id}") from exc
        return payload_hash

    def get(self, trade_id: str) -> TradeOutcome | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json, payload_hash FROM trade_outcomes WHERE trade_id = ?",
                (trade_id,),
            ).fetchone()
        if row is None:
            return None
        return self._decode_verified(trade_id, row[0], row[1])

    def all(self) -> list[TradeOutcome]:
        """Return all immutable outcomes ordered by close time for firm analytics."""

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT trade_id, payload_json, payload_hash
                FROM trade_outcomes
                ORDER BY closed_at ASC, trade_id ASC
                """
            ).fetchall()
        return [self._decode_verified(trade_id, payload, digest) for trade_id, payload, digest in rows]

    @staticmethod
    def _decode_verified(trade_id: str, payload_json: str, expected_hash: str) -> TradeOutcome:
        actual_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"outcome payload integrity failure for trade {trade_id}")
        return TradeOutcome.model_validate_json(payload_json)
