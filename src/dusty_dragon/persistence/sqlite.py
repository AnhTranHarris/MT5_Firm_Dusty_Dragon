from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA_VERSION = 3

_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brokers (
    broker_id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS desks (
    desk_id TEXT PRIMARY KEY,
    layer INTEGER NOT NULL CHECK (layer >= 0),
    specialization TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    retired_at_utc TEXT
);

CREATE TABLE IF NOT EXISTS broker_accounts (
    account_id TEXT PRIMARY KEY,
    desk_id TEXT NOT NULL REFERENCES desks(desk_id),
    broker_id TEXT NOT NULL REFERENCES brokers(broker_id),
    account_number TEXT NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('DEMO', 'LIVE')),
    opened_at_utc TEXT NOT NULL,
    closed_at_utc TEXT,
    UNIQUE (broker_id, account_number, environment)
);

CREATE TABLE IF NOT EXISTS instruments (
    instrument_id TEXT PRIMARY KEY,
    broker_id TEXT NOT NULL REFERENCES brokers(broker_id),
    broker_symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    base_currency TEXT,
    quote_currency TEXT,
    UNIQUE (broker_id, broker_symbol)
);

CREATE TABLE IF NOT EXISTS instrument_specs (
    spec_id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id),
    effective_from_utc TEXT NOT NULL,
    digits INTEGER NOT NULL CHECK (digits >= 0),
    tick_size REAL NOT NULL CHECK (tick_size > 0),
    tick_value REAL NOT NULL CHECK (tick_value >= 0),
    contract_size REAL NOT NULL CHECK (contract_size > 0),
    min_volume REAL NOT NULL CHECK (min_volume > 0),
    max_volume REAL NOT NULL CHECK (max_volume >= min_volume),
    volume_step REAL NOT NULL CHECK (volume_step > 0),
    UNIQUE (instrument_id, effective_from_utc)
);

CREATE TABLE IF NOT EXISTS equity_snapshots (
    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
    desk_id TEXT NOT NULL REFERENCES desks(desk_id),
    account_id TEXT NOT NULL REFERENCES broker_accounts(account_id),
    observed_at_utc TEXT NOT NULL,
    balance REAL NOT NULL,
    equity REAL NOT NULL,
    policy_id TEXT NOT NULL,
    UNIQUE (account_id, observed_at_utc)
);

CREATE TABLE IF NOT EXISTS expected_account_states (
    account_id TEXT PRIMARY KEY REFERENCES broker_accounts(account_id),
    desk_id TEXT NOT NULL REFERENCES desks(desk_id),
    broker_id TEXT NOT NULL REFERENCES brokers(broker_id),
    environment TEXT NOT NULL CHECK (environment IN ('DEMO', 'LIVE')),
    as_of_utc TEXT NOT NULL,
    balance REAL NOT NULL CHECK (balance >= 0),
    equity REAL NOT NULL CHECK (equity >= 0),
    margin REAL NOT NULL CHECK (margin >= 0),
    free_margin REAL NOT NULL CHECK (free_margin >= 0),
    policy_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS expected_positions (
    account_id TEXT NOT NULL REFERENCES broker_accounts(account_id),
    position_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id),
    side TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT')),
    volume REAL NOT NULL CHECK (volume > 0),
    open_price REAL NOT NULL CHECK (open_price > 0),
    current_price REAL NOT NULL CHECK (current_price > 0),
    unrealized_pnl REAL NOT NULL,
    observed_at_utc TEXT NOT NULL,
    PRIMARY KEY (account_id, position_id)
);

CREATE TABLE IF NOT EXISTS capital_flows (
    flow_id TEXT PRIMARY KEY,
    desk_id TEXT NOT NULL REFERENCES desks(desk_id),
    account_id TEXT NOT NULL REFERENCES broker_accounts(account_id),
    occurred_at_utc TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount != 0),
    flow_type TEXT NOT NULL CHECK (
        flow_type IN ('DEPOSIT', 'WITHDRAWAL', 'DEMO_COMPRESSION', 'BROKER_ADJUSTMENT')
    ),
    policy_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id),
    timeframe TEXT NOT NULL,
    uri TEXT NOT NULL UNIQUE,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    row_count INTEGER NOT NULL CHECK (row_count > 0),
    start_utc TEXT NOT NULL,
    end_utc TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('BUILDING', 'FROZEN', 'SUPERSEDED')),
    schema_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS authorization_leases (
    lease_id TEXT PRIMARY KEY,
    desk_id TEXT NOT NULL REFERENCES desks(desk_id),
    instrument_id TEXT NOT NULL REFERENCES instruments(instrument_id),
    side TEXT NOT NULL,
    approved_risk_fraction REAL NOT NULL CHECK (approved_risk_fraction > 0),
    financial_policy_id TEXT NOT NULL,
    operations_policy_id TEXT NOT NULL,
    authorized_at_utc TEXT NOT NULL,
    expires_at_utc TEXT NOT NULL,
    consumed_at_utc TEXT,
    audit_event_id TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    occurred_at_utc TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    policy_id TEXT,
    payload_json TEXT NOT NULL
);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a local Dusty ledger connection with integrity-oriented defaults."""

    connection = sqlite3.connect(Path(path))
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = FULL")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    """Create the institutional ledger schema idempotently."""

    with connection:
        connection.executescript(_SCHEMA)
        connection.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES (?, ?)",
            ("schema_version", str(_SCHEMA_VERSION)),
        )


def schema_version(connection: sqlite3.Connection) -> int:
    row = connection.execute(
        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
    ).fetchone()
    if row is None:
        raise RuntimeError("database schema has not been initialized")
    return int(row["value"])
