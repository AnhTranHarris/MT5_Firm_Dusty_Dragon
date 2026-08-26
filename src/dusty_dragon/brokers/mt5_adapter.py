from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, ClassVar

from dusty_dragon.brokers.contracts import (
    BrokerAccountState,
    BrokerAdapter,
    ExecutionResult,
    MarketBar,
    Position,
    Quote,
    SymbolSpec,
)
from dusty_dragon.brokers.volume import normalize_volume_down
from dusty_dragon.domain.trades import Side, TradeProposal


class MT5UnavailableError(RuntimeError):
    pass


class MT5BrokerAdapter(BrokerAdapter):
    """MetaTrader 5 transport adapter.

    This module is intentionally the only place allowed to translate between
    Dusty Dragon domain models and MetaTrader5-native objects. That preserves a
    future path to another transport such as a broker API or TradingView-linked
    execution channel without changing strategy/research code.

    Design references:
    - Vibe-Trading: fail-closed live/order gateway separation and normalized
      financial-data interfaces.
    - Kronos: Python-native OHLCV/time-series ingestion boundary.
    - Automaton: explicit capability boundary and auditable tool execution.
    """

    _TIMEFRAME_NAMES: ClassVar[dict[str, str]] = {
        "M1": "TIMEFRAME_M1",
        "M5": "TIMEFRAME_M5",
        "M15": "TIMEFRAME_M15",
        "M30": "TIMEFRAME_M30",
        "H1": "TIMEFRAME_H1",
        "H4": "TIMEFRAME_H4",
        "D1": "TIMEFRAME_D1",
    }

    def __init__(
        self,
        *,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        terminal_path: str | None = None,
        mt5_module: Any | None = None,
    ) -> None:
        self._login = login
        self._password = password
        self._server = server
        self._terminal_path = terminal_path
        self._mt5 = mt5_module
        self._connected = False

    def _module(self) -> Any:
        if self._mt5 is not None:
            return self._mt5
        try:
            import MetaTrader5 as mt5  # type: ignore[import-not-found]
        except ImportError as exc:
            raise MT5UnavailableError(
                "MetaTrader5 package is unavailable; install the project with the mt5 extra"
            ) from exc
        self._mt5 = mt5
        return mt5

    def connect(self) -> None:
        mt5 = self._module()
        kwargs: dict[str, Any] = {}
        if self._terminal_path:
            kwargs["path"] = self._terminal_path
        if self._login is not None:
            kwargs["login"] = self._login
        if self._password:
            kwargs["password"] = self._password
        if self._server:
            kwargs["server"] = self._server

        if not mt5.initialize(**kwargs):
            raise MT5UnavailableError(f"MT5 initialize failed: {mt5.last_error()}")
        self._connected = True

    def close(self) -> None:
        if self._connected:
            self._module().shutdown()
            self._connected = False

    def _require_connected(self) -> Any:
        if not self._connected:
            raise MT5UnavailableError("MT5 adapter is not connected")
        return self._module()

    def symbols(self) -> Sequence[str]:
        mt5 = self._require_connected()
        rows = mt5.symbols_get()
        if rows is None:
            raise MT5UnavailableError(f"MT5 symbols_get failed: {mt5.last_error()}")
        return tuple(sorted(row.name for row in rows))

    def symbol_spec(self, symbol: str) -> SymbolSpec:
        mt5 = self._require_connected()
        row = mt5.symbol_info(symbol)
        if row is None:
            raise MT5UnavailableError(f"unknown MT5 symbol: {symbol}")
        return SymbolSpec(
            symbol=symbol,
            volume_min=float(row.volume_min),
            volume_max=float(row.volume_max),
            volume_step=float(row.volume_step),
            point=float(row.point),
            digits=int(row.digits),
            trade_mode=getattr(row, "trade_mode", None),
            contract_size=self._positive_or_none(getattr(row, "trade_contract_size", None)),
            tick_size=self._positive_or_none(getattr(row, "trade_tick_size", None)),
            tick_value=self._nonnegative_or_none(getattr(row, "trade_tick_value", None)),
            profit_currency=getattr(row, "currency_profit", None),
        )

    def quote(self, symbol: str) -> Quote:
        mt5 = self._require_connected()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5UnavailableError(f"no current MT5 quote for {symbol}")
        timestamp = datetime.fromtimestamp(float(tick.time), tz=UTC)
        return Quote(symbol=symbol, captured_at=timestamp, bid=float(tick.bid), ask=float(tick.ask))

    def bars(self, symbol: str, timeframe: str, count: int) -> Sequence[MarketBar]:
        if count <= 0:
            raise ValueError("bar count must be positive")

        mt5 = self._require_connected()
        normalized_timeframe = timeframe.upper()
        constant_name = self._TIMEFRAME_NAMES.get(normalized_timeframe)
        if constant_name is None:
            raise ValueError(f"unsupported MT5 timeframe: {timeframe}")
        mt5_timeframe = getattr(mt5, constant_name, None)
        if mt5_timeframe is None:
            raise MT5UnavailableError(f"MT5 module does not expose {constant_name}")

        rows = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
        if rows is None or len(rows) == 0:
            raise MT5UnavailableError(f"no MT5 bars returned for {symbol} {timeframe}")

        result: list[MarketBar] = []
        for row in rows:
            result.append(
                MarketBar(
                    symbol=symbol,
                    timeframe=normalized_timeframe,
                    opened_at=datetime.fromtimestamp(float(row["time"]), tz=UTC),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    tick_volume=float(row["tick_volume"]),
                    spread_points=float(row["spread"]),
                    real_volume=float(row["real_volume"]),
                )
            )
        return tuple(result)

    def account_state(self) -> BrokerAccountState:
        mt5 = self._require_connected()
        row = mt5.account_info()
        if row is None:
            raise MT5UnavailableError(f"MT5 account_info failed: {mt5.last_error()}")

        margin_level = float(row.margin_level)
        return BrokerAccountState(
            captured_at=datetime.now(UTC),
            login=int(row.login) if getattr(row, "login", None) is not None else None,
            currency=str(row.currency),
            balance=float(row.balance),
            equity=float(row.equity),
            margin=float(row.margin),
            free_margin=float(row.margin_free),
            margin_level=margin_level if margin_level > 0 else None,
        )

    def positions(self) -> Sequence[Position]:
        mt5 = self._require_connected()
        rows = mt5.positions_get()
        if rows is None:
            raise MT5UnavailableError(f"MT5 positions_get failed: {mt5.last_error()}")

        buy_type = getattr(mt5, "POSITION_TYPE_BUY", 0)
        result: list[Position] = []
        for row in rows:
            result.append(
                Position(
                    ticket=int(row.ticket),
                    symbol=str(row.symbol),
                    side=Side.BUY if row.type == buy_type else Side.SELL,
                    volume=float(row.volume),
                    price_open=float(row.price_open),
                    stop_loss=float(row.sl) if float(row.sl) > 0 else None,
                    take_profit=float(row.tp) if float(row.tp) > 0 else None,
                    profit=float(row.profit),
                )
            )
        return tuple(result)

    def execute_paper(self, proposal: TradeProposal, volume: float) -> ExecutionResult:
        """Validate MT5 symbol mechanics without sending an order."""
        spec = self.symbol_spec(proposal.symbol)
        normalized_volume = normalize_volume_down(volume, spec)
        quote = self.quote(proposal.symbol)
        price = quote.ask if proposal.side == Side.BUY else quote.bid
        spread_points = quote.spread / spec.point
        return ExecutionResult(
            accepted=True,
            message="paper validation accepted; no MT5 order sent",
            requested_volume=volume,
            executed_volume=normalized_volume,
            executed_price=price,
            spread_points=spread_points,
            slippage_points=0.0,
            estimated_commission=0.0,
            estimated_swap=0.0,
        )

    @staticmethod
    def _positive_or_none(value: Any) -> float | None:
        if value is None:
            return None
        parsed = float(value)
        return parsed if parsed > 0 else None

    @staticmethod
    def _nonnegative_or_none(value: Any) -> float | None:
        if value is None:
            return None
        parsed = float(value)
        return parsed if parsed >= 0 else None
