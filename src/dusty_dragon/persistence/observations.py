from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from dusty_dragon.brokers.mt5_instruments import MT5InstrumentRegistration
from dusty_dragon.domain.accounts import AccountSnapshot


@dataclass(slots=True)
class ObservationRepository:
    """Persist normalized broker observations; raw broker payloads never cross this boundary."""

    connection: sqlite3.Connection

    def register_instrument(self, registration: MT5InstrumentRegistration) -> None:
        instrument = registration.instrument
        spec = registration.spec
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO instruments(
                    instrument_id, broker_id, broker_symbol, asset_class,
                    base_currency, quote_currency
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(instrument_id) DO UPDATE SET
                    broker_id = excluded.broker_id,
                    broker_symbol = excluded.broker_symbol,
                    asset_class = excluded.asset_class,
                    base_currency = excluded.base_currency,
                    quote_currency = excluded.quote_currency
                """,
                (
                    instrument.instrument_id,
                    instrument.broker_id,
                    instrument.broker_symbol,
                    instrument.asset_class.value,
                    instrument.base_currency,
                    instrument.quote_currency,
                ),
            )
            self.connection.execute(
                """
                INSERT OR IGNORE INTO instrument_specs(
                    instrument_id, effective_from_utc, digits, tick_size, tick_value,
                    contract_size, min_volume, max_volume, volume_step
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spec.instrument_id,
                    spec.effective_from_utc.isoformat(),
                    spec.digits,
                    spec.tick_size,
                    spec.tick_value,
                    spec.contract_size,
                    spec.min_volume,
                    spec.max_volume,
                    spec.volume_step,
                ),
            )

    def persist_equity_snapshot(self, snapshot: AccountSnapshot, *, policy_id: str) -> None:
        if not policy_id.strip():
            raise ValueError("policy_id is required")
        with self.connection:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO equity_snapshots(
                    desk_id, account_id, observed_at_utc, balance, equity, policy_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.desk_id,
                    snapshot.account_id,
                    snapshot.observed_at_utc.isoformat(),
                    snapshot.balance,
                    snapshot.equity,
                    policy_id,
                ),
            )
