from datetime import UTC, datetime

from dusty_dragon.brokers.mt5_read import BrokerReadState
from dusty_dragon.domain.accounts import AccountSnapshot, PositionSide, PositionSnapshot
from dusty_dragon.persistence.expected_state import ExpectedStateRepository
from dusty_dragon.persistence.sqlite import connect, initialize, schema_version


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
            ("GENERALIST-01", 1, "GENERALIST", "2026-08-26T09:00:00+00:00"),
        )
        connection.execute(
            """
            INSERT INTO broker_accounts(
                account_id, desk_id, broker_id, account_number, environment, opened_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("A1", "GENERALIST-01", "B1", "10001", "DEMO", "2026-08-26T09:00:00+00:00"),
        )
        connection.execute(
            """
            INSERT INTO instruments(
                instrument_id, broker_id, broker_symbol, asset_class, base_currency, quote_currency
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("FX.EURUSD@B1", "B1", "EURUSD.a", "FX", "EUR", "USD"),
        )
    return connection


def state(*, equity: float = 20_025.0) -> BrokerReadState:
    observed_at = datetime(2026, 8, 26, 9, 30, tzinfo=UTC)
    return BrokerReadState(
        account=AccountSnapshot(
            account_id="A1",
            desk_id="GENERALIST-01",
            broker_id="B1",
            environment="DEMO",
            observed_at_utc=observed_at,
            balance=20_000.0,
            equity=equity,
            margin=100.0,
            free_margin=19_925.0,
        ),
        positions=(
            PositionSnapshot(
                position_id="42",
                account_id="A1",
                instrument_id="FX.EURUSD@B1",
                side=PositionSide.LONG,
                volume=0.01,
                open_price=1.1000,
                current_price=1.1025,
                unrealized_pnl=25.0,
                observed_at_utc=observed_at,
            ),
        ),
    )


def test_schema_version_advances_for_expected_state_tables() -> None:
    connection = seeded_connection()

    assert schema_version(connection) == 2


def test_expected_state_round_trips() -> None:
    connection = seeded_connection()
    repository = ExpectedStateRepository(connection)

    repository.replace(state(), policy_id="financial_v1")
    restored = repository.load("A1")

    assert restored.account.equity == 20_025.0
    assert restored.positions[0].position_id == "42"
    assert restored.positions[0].side is PositionSide.LONG


def test_replace_is_atomic_and_replaces_old_positions() -> None:
    connection = seeded_connection()
    repository = ExpectedStateRepository(connection)
    repository.replace(state(), policy_id="financial_v1")
    replacement = BrokerReadState(account=state(equity=20_100.0).account, positions=())

    repository.replace(replacement, policy_id="financial_v1")
    restored = repository.load("A1")

    assert restored.account.equity == 20_100.0
    assert restored.positions == ()


def test_missing_expected_state_fails_closed() -> None:
    connection = seeded_connection()
    repository = ExpectedStateRepository(connection)

    try:
        repository.load("MISSING")
    except LookupError as exc:
        assert "expected broker state not found" in str(exc)
    else:
        raise AssertionError("missing expected state must fail closed")
