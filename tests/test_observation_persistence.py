from datetime import UTC, datetime

import pytest

from dusty_dragon.brokers.mt5_instruments import MT5InstrumentRegistration
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment, AssetClass, Instrument, InstrumentSpec
from dusty_dragon.persistence.observations import ObservationRepository
from dusty_dragon.persistence.sqlite import connect, initialize


def seeded_connection():
    connection = connect(":memory:")
    initialize(connection)
    with connection:
        connection.execute("INSERT INTO brokers(broker_id, name) VALUES (?, ?)", ("B1", "Broker 1"))
        connection.execute(
            """
            INSERT INTO desks(desk_id, layer, specialization, created_at_utc)
            VALUES (?, ?, ?, ?)
            """,
            ("GENERALIST-01", 0, "GENERALIST", "2026-08-26T09:00:00+00:00"),
        )
        connection.execute(
            """
            INSERT INTO broker_accounts(
                account_id, desk_id, broker_id, account_number, environment, opened_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "A1",
                "GENERALIST-01",
                "B1",
                "10001",
                "DEMO",
                "2026-08-26T09:00:00+00:00",
            ),
        )
    return connection


def test_repository_persists_instrument_and_specification() -> None:
    connection = seeded_connection()
    repository = ObservationRepository(connection)
    registration = MT5InstrumentRegistration(
        instrument=Instrument(
            instrument_id="FX.EURUSD@B1",
            broker_id="B1",
            broker_symbol="EURUSD.a",
            asset_class=AssetClass.FX,
            base_currency="EUR",
            quote_currency="USD",
        ),
        spec=InstrumentSpec(
            instrument_id="FX.EURUSD@B1",
            digits=5,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100_000.0,
            min_volume=0.01,
            max_volume=100.0,
            volume_step=0.01,
            effective_from_utc=datetime(2026, 8, 26, 9, 30, tzinfo=UTC),
        ),
    )

    repository.register_instrument(registration)

    instrument = connection.execute("SELECT * FROM instruments").fetchone()
    spec = connection.execute("SELECT * FROM instrument_specs").fetchone()
    assert instrument["broker_symbol"] == "EURUSD.a"
    assert spec["min_volume"] == pytest.approx(0.01)


def test_equity_snapshot_is_idempotent_for_same_account_timestamp() -> None:
    connection = seeded_connection()
    repository = ObservationRepository(connection)
    snapshot = AccountSnapshot(
        account_id="A1",
        desk_id="GENERALIST-01",
        broker_id="B1",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 9, 30, tzinfo=UTC),
        balance=20_000.0,
        equity=20_025.0,
        margin=100.0,
        free_margin=19_925.0,
    )

    repository.persist_equity_snapshot(snapshot, policy_id="financial_v1")
    repository.persist_equity_snapshot(snapshot, policy_id="financial_v1")

    count = connection.execute("SELECT COUNT(*) AS count FROM equity_snapshots").fetchone()["count"]
    assert count == 1


def test_equity_snapshot_rejects_unknown_account_lineage() -> None:
    connection = seeded_connection()
    repository = ObservationRepository(connection)
    snapshot = AccountSnapshot(
        account_id="UNKNOWN",
        desk_id="GENERALIST-01",
        broker_id="B1",
        environment=AccountEnvironment.DEMO,
        observed_at_utc=datetime(2026, 8, 26, 9, 30, tzinfo=UTC),
        balance=20_000.0,
        equity=20_000.0,
        margin=0.0,
        free_margin=20_000.0,
    )

    with pytest.raises(Exception):
        repository.persist_equity_snapshot(snapshot, policy_id="financial_v1")
