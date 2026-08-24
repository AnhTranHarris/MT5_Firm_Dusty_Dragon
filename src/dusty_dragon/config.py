from __future__ import annotations

from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradingMode(StrEnum):
    PAPER = "paper"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    trading_mode: TradingMode = TradingMode.PAPER
    broker_name: str = "boforex"
    mt5_login: int | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    mt5_terminal_path: str | None = None

    account_currency: str = "USD"
    account_starting_balance: float = 10_000.0
    primary_timeframe: str = "M15"

    risk_per_trade_pct: float = Field(default=0.25, gt=0, le=5)
    max_open_risk_pct: float = Field(default=2.0, gt=0, le=20)
    daily_drawdown_halt_pct: float = Field(default=2.5, gt=0, le=20)
    weekly_drawdown_halt_pct: float = Field(default=5.0, gt=0, le=30)

    def require_mt5_credentials(self) -> None:
        missing = [
            name
            for name, value in {
                "MT5_LOGIN": self.mt5_login,
                "MT5_PASSWORD": self.mt5_password,
                "MT5_SERVER": self.mt5_server,
            }.items()
            if value in (None, "")
        ]
        if missing:
            raise RuntimeError(f"Missing local MT5 configuration: {', '.join(missing)}")
