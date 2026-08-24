from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from dusty_dragon.reporting.trade_report import TradeReport


class TradeLedger:
    """Append-only SQLite ledger for trade-decision provenance.

    The hash chain is intentionally simple and local: each row commits to the
    previous row hash plus the canonical JSON payload. This is not blockchain;
    it is a tamper-evident audit trail inspired by Vibe-Trading governance and
    Automaton's persistent audit history.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trade_reports (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_trade_reports_trade_id ON trade_reports(trade_id)"
            )

    @staticmethod
    def _hash(previous_hash: str, payload_json: str) -> str:
        material = f"{previous_hash}\n{payload_json}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def append(self, report: TradeReport) -> str:
        payload_json = report.model_dump_json(exclude_none=False)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT record_hash FROM trade_reports ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = row["record_hash"] if row is not None else "GENESIS"
            record_hash = self._hash(previous_hash, payload_json)
            connection.execute(
                """
                INSERT INTO trade_reports (
                    trade_id, created_at, payload_json, previous_hash, record_hash
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(report.trade_id),
                    report.created_at.isoformat(),
                    payload_json,
                    previous_hash,
                    record_hash,
                ),
            )
        return record_hash

    def reports_for_trade(self, trade_id: str) -> list[TradeReport]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM trade_reports WHERE trade_id = ? ORDER BY sequence",
                (trade_id,),
            ).fetchall()
        return [TradeReport.model_validate_json(row["payload_json"]) for row in rows]

    def verify_chain(self) -> bool:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json, previous_hash, record_hash
                FROM trade_reports
                ORDER BY sequence
                """
            ).fetchall()

        expected_previous = "GENESIS"
        for row in rows:
            if row["previous_hash"] != expected_previous:
                return False
            expected_hash = self._hash(expected_previous, row["payload_json"])
            if row["record_hash"] != expected_hash:
                return False
            expected_previous = row["record_hash"]
        return True
