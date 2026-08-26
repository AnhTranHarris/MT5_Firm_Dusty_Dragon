from dusty_dragon.brokers.health import (
    BrokerHealthMonitor,
    BrokerHealthPolicy,
    BrokerHealthState,
)
from dusty_dragon.brokers.reconciliation import ReconciliationStatus


def policy() -> BrokerHealthPolicy:
    return BrokerHealthPolicy(
        drift_watch_count=1,
        drift_restrict_count=2,
        drift_halt_count=3,
        invalid_halts_immediately=True,
        match_resets_drift_count=True,
    )


def test_drift_escalates_watch_restricted_halted() -> None:
    monitor = BrokerHealthMonitor(policy())

    first = monitor.observe(ReconciliationStatus.DRIFT)
    second = monitor.observe(ReconciliationStatus.DRIFT)
    third = monitor.observe(ReconciliationStatus.DRIFT)

    assert first.state is BrokerHealthState.WATCH
    assert second.state is BrokerHealthState.RESTRICTED
    assert third.state is BrokerHealthState.HALTED
    assert not third.safe_for_new_orders


def test_invalid_halts_immediately() -> None:
    monitor = BrokerHealthMonitor(policy())

    snapshot = monitor.observe(ReconciliationStatus.INVALID)

    assert snapshot.state is BrokerHealthState.HALTED
    assert snapshot.consecutive_drift_count == 1


def test_match_resets_drift_sequence() -> None:
    monitor = BrokerHealthMonitor(policy())
    monitor.observe(ReconciliationStatus.DRIFT)
    monitor.observe(ReconciliationStatus.DRIFT)

    recovered = monitor.observe(ReconciliationStatus.MATCH)

    assert recovered.state is BrokerHealthState.HEALTHY
    assert recovered.consecutive_drift_count == 0
    assert recovered.safe_for_new_orders
