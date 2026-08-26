from __future__ import annotations

from typing import Any, Protocol

from dusty_dragon.brokers.mt5_native_write import (
    MetaTrader5OrderSendTransport,
    MetaTrader5WriteModule,
    MT5WriteCapability,
)
from dusty_dragon.brokers.mt5_write import DryRunMT5WriteAdapter
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment


class MetaTrader5RuntimeModule(MetaTrader5WriteModule, Protocol):
    ACCOUNT_TRADE_MODE_DEMO: int

    def account_info(self) -> Any: ...


def build_native_demo_write_adapter(
    mt5: MetaTrader5RuntimeModule,
    *,
    expected_account: AccountSnapshot,
    enable_write: bool = False,
    magic: int = 0,
) -> DryRunMT5WriteAdapter:
    """Construct native write access only when Dusty and MT5 independently agree on demo state."""

    if expected_account.environment is not AccountEnvironment.DEMO:
        raise PermissionError("Dusty account snapshot is not DEMO")

    native_account = mt5.account_info()
    if native_account is None:
        raise RuntimeError(f"MT5 account_info returned no result: {mt5.last_error()!r}")
    if int(native_account.trade_mode) != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise PermissionError("connected MT5 account is not a demo account")
    if str(native_account.login) != expected_account.account_id:
        raise PermissionError("connected MT5 login does not match Dusty broker account")
    if not bool(native_account.trade_allowed):
        raise PermissionError("connected MT5 account does not allow trading")
    if not bool(native_account.trade_expert):
        raise PermissionError("connected MT5 account does not allow expert trading")

    native_transport = MetaTrader5OrderSendTransport(
        mt5,
        capability=MT5WriteCapability(enabled=enable_write),
        magic=magic,
    )
    return DryRunMT5WriteAdapter(native_transport)
