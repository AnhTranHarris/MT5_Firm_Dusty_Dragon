from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dusty_dragon.brokers.mt5_runtime import MetaTrader5RuntimeModule
from dusty_dragon.domain.accounts import AccountSnapshot
from dusty_dragon.domain.market import AccountEnvironment


class MetaTrader5SessionModule(MetaTrader5RuntimeModule, Protocol):
    def initialize(self, *, login: int, timeout: int) -> bool: ...

    def shutdown(self) -> None: ...


@dataclass(slots=True)
class MT5DemoSession:
    """Own one verified Python-to-MT5 connection bound to a single demo login."""

    mt5: MetaTrader5SessionModule
    expected_account: AccountSnapshot
    timeout_ms: int = 60_000
    _opened: bool = False
    _fault_reason: str | None = None

    def open(self) -> None:
        if self._fault_reason is not None:
            raise RuntimeError(f"MT5 session fault is latched: {self._fault_reason}")
        if self._opened:
            self.validate_current()
            return
        if self.expected_account.environment is not AccountEnvironment.DEMO:
            raise PermissionError("Dusty account snapshot is not DEMO")
        if self.timeout_ms <= 0:
            raise ValueError("timeout_ms must be positive")

        try:
            expected_login = int(self.expected_account.account_id)
        except ValueError as exc:
            raise ValueError("MT5 account_id must be a numeric login") from exc

        if not self.mt5.initialize(login=expected_login, timeout=self.timeout_ms):
            raise RuntimeError(f"MT5 initialize failed: {self.mt5.last_error()!r}")

        self._opened = True
        try:
            self.validate_current()
        except Exception:
            self.close()
            raise

    def validate_current(self) -> None:
        if self._fault_reason is not None:
            raise RuntimeError(f"MT5 session fault is latched: {self._fault_reason}")
        if not self._opened:
            raise RuntimeError("MT5 session is not open")

        try:
            self._validate_native_account()
        except (PermissionError, RuntimeError) as exc:
            self._latch_fault(str(exc))
            raise

    def _validate_native_account(self) -> None:
        account = self.mt5.account_info()
        if account is None:
            raise RuntimeError(f"MT5 account_info returned no result: {self.mt5.last_error()!r}")
        if str(account.login) != self.expected_account.account_id:
            raise PermissionError("connected MT5 login drifted from bound Dusty account")
        if int(account.trade_mode) != self.mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise PermissionError("connected MT5 account is no longer demo")
        if not bool(account.trade_allowed):
            raise PermissionError("connected MT5 account no longer allows trading")
        if not bool(account.trade_expert):
            raise PermissionError("connected MT5 account no longer allows expert trading")

    def _latch_fault(self, reason: str) -> None:
        self._fault_reason = reason
        self.close()

    def close(self) -> None:
        if not self._opened:
            return
        self.mt5.shutdown()
        self._opened = False

    @property
    def opened(self) -> bool:
        return self._opened

    @property
    def faulted(self) -> bool:
        return self._fault_reason is not None

    @property
    def fault_reason(self) -> str | None:
        return self._fault_reason

    def __enter__(self) -> MT5DemoSession:
        self.open()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
