from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from dusty_dragon.brokers.mt5_read import BrokerReadState
from dusty_dragon.domain.accounts import AccountSnapshot, PositionSide, PositionSnapshot
from dusty_dragon.domain.market import AccountEnvironment


@dataclass(slots=True)
class ExpectedStateRepository:
    """Persist and restore Dusty's sovereign expectation of broker state."""

    connection: sqlite3.Connection

    def replace(self, state: BrokerReadState, *, policy_id: str) -> None:
        if not policy_id.strip():
            raise ValueError("policy_id is required")

        account = state.account
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO expected_account_states(
                    account_id, desk_id, broker_id, environment, as_of_utc,
                    balance, equity, margin, free_margin, policy_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    desk_id = excluded.desk_id,
                    broker_id = excluded.broker_id,
                    environment = excluded.environment,
                    as_of_utc = excluded.as_of_utc,
                    balance = excluded.balance,
                    equity = excluded.equity,
                    margin = excluded.margin,
                    free_margin = excluded.free_margin,
                    policy_id = excluded.policy_id
                """,
                (
                    account.account_id,
                    account.desk_id,
                    account.broker_id,
                    account.environment.value,
                    account.observed_at_utc.isoformat(),
                    account.balance,
                    account.equity,
                    account.margin,
                    account.free_margin,
                    policy_id,
                ),
            )
            self.connection.execute(
                "DELETE FROM expected_positions WHERE account_id = ?",
                (account.account_id,),
            )
            self.connection.executemany(
                """
                INSERT INTO expected_positions(
                    account_id, position_id, instrument_id, side, volume,
                    open_price, current_price, unrealized_pnl, observed_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        position.account_id,
                        position.position_id,
                        position.instrument_id,
                        position.side.value,
                        position.volume,
                        position.open_price,
                        position.current_price,
                        position.unrealized_pnl,
                        position.observed_at_utc.isoformat(),
                    )
                    for position in state.positions
                ],
            )

    def load(self, account_id: str) -> BrokerReadState:
        if not account_id.strip():
            raise ValueError("account_id is required")

        account_row = self.connection.execute(
            "SELECT * FROM expected_account_states WHERE account_id = ?",
            (account_id,),
        ).fetchone()
        if account_row is None:
            raise LookupError(f"expected broker state not found for account: {account_id}")

        account = AccountSnapshot(
            account_id=account_row["account_id"],
            desk_id=account_row["desk_id"],
            broker_id=account_row["broker_id"],
            environment=AccountEnvironment(account_row["environment"]),
            observed_at_utc=datetime.fromisoformat(account_row["as_of_utc"]),
            balance=account_row["balance"],
            equity=account_row["equity"],
            margin=account_row["margin"],
            free_margin=account_row["free_margin"],
        )
        position_rows = self.connection.execute(
            """
            SELECT * FROM expected_positions
            WHERE account_id = ?
            ORDER BY position_id
            """,
            (account_id,),
        ).fetchall()
        positions = tuple(
            PositionSnapshot(
                position_id=row["position_id"],
                account_id=row["account_id"],
                instrument_id=row["instrument_id"],
                side=PositionSide(row["side"]),
                volume=row["volume"],
                open_price=row["open_price"],
                current_price=row["current_price"],
                unrealized_pnl=row["unrealized_pnl"],
                observed_at_utc=datetime.fromisoformat(row["observed_at_utc"]),
            )
            for row in position_rows
        )
        return BrokerReadState(account=account, positions=positions)
