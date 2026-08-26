from datetime import UTC, datetime

from dusty_dragon.brokers.health import (
    BrokerHealthMonitor,
    BrokerHealthPolicy,
    BrokerHealthState,
)
from dusty_dragon.brokers.mt5_read import BrokerReadState, MT5ReadAdapter, MT5ReadContext
from dusty_dragon.brokers.observation_service import BrokerObservationService
from dusty_dragon.brokers.reconciliation import ReconciliationStatus
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment
from dusty_dragon.persistence.expected_state import ExpectedStateRepository
from dusty_dragon.persistence.observations import ObservationRepository
from dusty_dragon.persistence.reconciliation_audit import ReconciliationAuditRepository
from dusty_dragon.persistence.sqlite import connect, initialize


class FakeMT5Transport:
    def __init__(self, equity: float) -> None:
        self._equity = equity

    def account_info(self) -> dict[str, object]:
        return {
            "balance": 20_000.0,
            "equity": self._equity,
            "margin": 100.0,
            "margin_free": self._equity - 100.0,
        }

    def positions_get(self) -> list[dict[str, object]]:
        return []


def health_monitor() -> BrokerHealthMonitor:
    return BrokerHealthMonitor(
        BrokerHealthPolicy(
            drift_watch_count=1,
            drift_restrict_count=2,
            drift_halt_count=3,
            invalid_halts_immediately=True,
            match_resets_drift_count=True,
        )
    )


def expected_state(equity: float, observed_at: datetime) -> BrokerReadState:
    return BrokerReadState(
        account=AccountSnapshot(
            account_id="A1",
            desk_id="GENERALIST-01",
            broker_id="B1",
            environment=AccountEnvironment.DEMO,
            observed_at_utc=observed_at,
            balance=20_000.0,
            equity=equity,
            margin=100.0,
            free_margin=equity - 100.0,
        ),
        positions=(),
    )


def service(
    equity: float,
    expected_equity: float,
    observed_at: datetime,
) -> tuple[BrokerObservationService, object]:
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
            ("A1", "GENERALIST-01", "B1", "10001", "DEMO", "2026-08-26T09:00:00+00:00"),
        )

    expected_repository = ExpectedStateRepository(connection)
    expected_repository.replace(
        expected_state(expected_equity, observed_at),
        policy_id="financial_v1",
    )
    adapter = MT5ReadAdapter(
        FakeMT5Transport(equity),
        MT5ReadContext(
            desk_id="GENERALIST-01",
            account_id="A1",
            broker_id="B1",
            environment=AccountEnvironment.DEMO,
            symbol_to_instrument={},
        ),
    )
    return (
        BrokerObservationService(
            adapter,
            ObservationRepository(connection),
            expected_repository,
            ReconciliationAuditRepository(connection),
            health_monitor(),
            observation_policy_id="financial_v1",
            operations_policy_id="operations_v1",
        ),
        connection,
    )


def test_matching_broker_truth_is_persisted_audited_and_healthy() -> None:
    observed_at = datetime(2026, 8, 26, 9, 30, tzinfo=UTC)
    observation_service, connection = service(20_025.0, 20_025.0, observed_at)

    result = observation_service.observe_and_reconcile("A1", observed_at_utc=observed_at)

    assert result.reconciliation.status is ReconciliationStatus.MATCH
    assert result.health.state is BrokerHealthState.HEALTHY
    row = connection.execute("SELECT equity, policy_id FROM equity_snapshots").fetchone()
    audit = connection.execute(
        "SELECT event_type FROM audit_events WHERE event_id = ?",
        (result.audit_event_id,),
    ).fetchone()
    assert row["equity"] == 20_025.0
    assert row["policy_id"] == "financial_v1"
    assert audit["event_type"] == "BROKER_RECONCILIATION"


def test_drift_is_persisted_audited_and_escalates_watch() -> None:
    observed_at = datetime(2026, 8, 26, 9, 30, tzinfo=UTC)
    observation_service, connection = service(19_900.0, 20_000.0, observed_at)

    result = observation_service.observe_and_reconcile("A1", observed_at_utc=observed_at)

    assert result.reconciliation.status is ReconciliationStatus.DRIFT
    assert not result.reconciliation.safe_for_new_orders
    assert result.health.state is BrokerHealthState.WATCH
    assert not result.health.safe_for_new_orders
    row = connection.execute("SELECT equity FROM equity_snapshots").fetchone()
    assert row["equity"] == 19_900.0


def test_missing_expected_state_fails_before_broker_observation() -> None:
    observed_at = datetime(2026, 8, 26, 9, 30, tzinfo=UTC)
    observation_service, connection = service(20_000.0, 20_000.0, observed_at)
    connection.execute("DELETE FROM expected_account_states WHERE account_id = ?", ("A1",))

    try:
        observation_service.observe_and_reconcile("A1", observed_at_utc=observed_at)
    except LookupError as exc:
        assert "expected broker state not found" in str(exc)
    else:
        raise AssertionError("reconciliation without sovereign expected state must fail closed")
