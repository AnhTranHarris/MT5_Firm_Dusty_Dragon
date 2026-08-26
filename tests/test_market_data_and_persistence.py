from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from dusty_dragon.data.datasets import DatasetManifest, DatasetStatus
from dusty_dragon.domain.market import (
    AssetClass,
    Instrument,
    InstrumentSpec,
    MarketBar,
    VolumeType,
)
from dusty_dragon.persistence.sqlite import connect, initialize, schema_version


def test_market_bar_requires_utc_and_valid_ohlc_geometry() -> None:
    opened = datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    closed = opened + timedelta(minutes=5)
    bar = MarketBar(
        instrument_id="FX.EURUSD@BROKER_A",
        timeframe="M5",
        ts_open_utc=opened,
        ts_close_utc=closed,
        open=1.17,
        high=1.18,
        low=1.16,
        close=1.175,
        volume=100,
        volume_type=VolumeType.TICK,
        source="MT5",
    )
    assert bar.is_complete

    with pytest.raises(ValueError, match="OHLC geometry"):
        MarketBar(
            instrument_id="FX.EURUSD@BROKER_A",
            timeframe="M5",
            ts_open_utc=opened,
            ts_close_utc=closed,
            open=1.17,
            high=1.16,
            low=1.15,
            close=1.175,
            volume=100,
            volume_type=VolumeType.TICK,
            source="MT5",
        )


def test_instrument_identity_is_broker_scoped() -> None:
    instrument = Instrument(
        instrument_id="FX.EURUSD@BROKER_A",
        broker_id="BROKER_A",
        broker_symbol="EURUSD.a",
        asset_class=AssetClass.FX,
        base_currency="EUR",
        quote_currency="USD",
    )
    assert instrument.instrument_id != instrument.broker_symbol


def test_instrument_spec_rejects_invalid_volume_bounds() -> None:
    with pytest.raises(ValueError, match="max_volume"):
        InstrumentSpec(
            instrument_id="FX.EURUSD@BROKER_A",
            digits=5,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100_000,
            min_volume=1.0,
            max_volume=0.01,
            volume_step=0.01,
            effective_from_utc=datetime(2026, 8, 26, tzinfo=UTC),
        )


def test_frozen_dataset_manifest_requires_canonical_uri_and_checksum() -> None:
    manifest = DatasetManifest(
        dataset_id="DS-EURUSD-M5-001",
        instrument_id="FX.EURUSD@BROKER_A",
        timeframe="M5",
        uri="dusty://market/BROKER_A/EURUSD/M5/DS-EURUSD-M5-001.parquet",
        sha256="a" * 64,
        row_count=10_000,
        start_utc=datetime(2026, 1, 1, tzinfo=UTC),
        end_utc=datetime(2026, 8, 1, tzinfo=UTC),
        status=DatasetStatus.FROZEN,
    )
    assert manifest.immutable

    with pytest.raises(ValueError, match="sha256"):
        DatasetManifest(
            dataset_id="bad",
            instrument_id="FX.EURUSD@BROKER_A",
            timeframe="M5",
            uri="dusty://market/bad.parquet",
            sha256="NOT-A-HASH",
            row_count=1,
            start_utc=datetime(2026, 1, 1, tzinfo=UTC),
            end_utc=datetime(2026, 1, 2, tzinfo=UTC),
        )


def test_sqlite_schema_enforces_desk_account_lineage_and_broker_symbols() -> None:
    connection = connect(":memory:")
    initialize(connection)
    assert schema_version(connection) == 4

    connection.execute(
        "INSERT INTO brokers(broker_id, name) VALUES (?, ?)",
        ("BROKER_A", "Broker A"),
    )
    connection.execute(
        "INSERT INTO desks(desk_id, layer, specialization, created_at_utc) "
        "VALUES (?, ?, ?, ?)",
        ("GENERALIST-01", 0, "GENERALIST", "2026-08-26T00:00:00Z"),
    )
    connection.execute(
        "INSERT INTO broker_accounts("
        "account_id, desk_id, broker_id, account_number, environment, opened_at_utc"
        ") VALUES (?, ?, ?, ?, ?, ?)",
        ("ACC-1", "GENERALIST-01", "BROKER_A", "123", "DEMO", "2026-08-26T00:00:00Z"),
    )
    connection.execute(
        "INSERT INTO instruments("
        "instrument_id, broker_id, broker_symbol, asset_class, base_currency, quote_currency"
        ") VALUES (?, ?, ?, ?, ?, ?)",
        ("FX.EURUSD@BROKER_A", "BROKER_A", "EURUSD.a", "FX", "EUR", "USD"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO broker_accounts("
            "account_id, desk_id, broker_id, account_number, environment, opened_at_utc"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            ("ACC-2", "MISSING", "BROKER_A", "456", "DEMO", "2026-08-26T00:00:00Z"),
        )

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO instruments("
            "instrument_id, broker_id, broker_symbol, asset_class"
            ") VALUES (?, ?, ?, ?)",
            ("FX.EURUSD-SECOND@BROKER_A", "BROKER_A", "EURUSD.a", "FX"),
        )
