from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd
from pydantic import BaseModel, Field

from dusty_dragon.brokers.contracts import MarketBar
from dusty_dragon.intelligence.kronos_bridge import bars_to_kronos_frame, split_kronos_inputs


class KronosPredictorLike(Protocol):
    def predict(
        self,
        *,
        df: pd.DataFrame,
        x_timestamp: pd.Series,
        y_timestamp: pd.Series,
        pred_len: int,
        **kwargs: Any,
    ) -> pd.DataFrame: ...


class KronosForecast(BaseModel):
    """Broker-neutral forecast summary derived from a Kronos prediction path."""

    symbol: str
    timeframe: str
    horizon_bars: int = Field(gt=0)
    starting_close: float = Field(gt=0)
    predicted_close: float = Field(gt=0)
    predicted_return_pct: float
    predicted_high: float = Field(gt=0)
    predicted_low: float = Field(gt=0)
    forecast_rows: int = Field(gt=0)
    volume_source: str


@dataclass(frozen=True)
class KronosForecastService:
    """Thin adapter around the upstream Kronos predictor.

    Roadmap reference: https://github.com/shiyu-coder/Kronos

    The service intentionally produces forecast evidence only. It does not create
    trades, size positions, or bypass Vibe-inspired governance. Automaton-style
    learning will later compare these forecast summaries with realized outcomes.
    """

    predictor: KronosPredictorLike
    temperature: float = 1.0
    top_p: float = 0.9
    sample_count: int = 1

    def forecast(self, bars: list[MarketBar], horizon_bars: int) -> KronosForecast:
        if horizon_bars <= 0:
            raise ValueError("horizon_bars must be positive")

        frame = bars_to_kronos_frame(bars)
        features, x_timestamp = split_kronos_inputs(frame)
        future_timestamps = self._future_timestamps(x_timestamp, horizon_bars)

        prediction = self.predictor.predict(
            df=features,
            x_timestamp=x_timestamp,
            y_timestamp=future_timestamps,
            pred_len=horizon_bars,
            T=self.temperature,
            top_p=self.top_p,
            sample_count=self.sample_count,
            verbose=False,
        )
        self._validate_prediction(prediction, horizon_bars)

        starting_close = float(features.iloc[-1]["close"])
        predicted_close = float(prediction.iloc[-1]["close"])
        predicted_return_pct = ((predicted_close / starting_close) - 1.0) * 100.0

        return KronosForecast(
            symbol=str(frame.attrs["symbol"]),
            timeframe=str(frame.attrs["timeframe"]),
            horizon_bars=horizon_bars,
            starting_close=starting_close,
            predicted_close=predicted_close,
            predicted_return_pct=predicted_return_pct,
            predicted_high=float(prediction["high"].max()),
            predicted_low=float(prediction["low"].min()),
            forecast_rows=len(prediction),
            volume_source=str(frame.attrs["volume_source"]),
        )

    @staticmethod
    def _future_timestamps(x_timestamp: pd.Series, horizon_bars: int) -> pd.Series:
        if len(x_timestamp) < 2:
            raise ValueError("Kronos forecasting requires at least two historical timestamps")

        deltas = x_timestamp.diff().dropna()
        if deltas.empty or (deltas <= pd.Timedelta(0)).any():
            raise ValueError("historical timestamps must increase monotonically")

        interval = deltas.mode().iloc[0]
        last = x_timestamp.iloc[-1]
        return pd.Series([last + interval * step for step in range(1, horizon_bars + 1)])

    @staticmethod
    def _validate_prediction(prediction: pd.DataFrame, horizon_bars: int) -> None:
        required = {"open", "high", "low", "close"}
        missing = required.difference(prediction.columns)
        if missing:
            raise ValueError(f"Kronos prediction missing columns: {sorted(missing)}")
        if len(prediction) != horizon_bars:
            raise ValueError(
                f"Kronos prediction returned {len(prediction)} rows; expected {horizon_bars}"
            )
        if prediction.loc[:, list(required)].isna().any().any():
            raise ValueError("Kronos prediction contains NaN price values")
        if (prediction.loc[:, list(required)] <= 0).any().any():
            raise ValueError("Kronos prediction contains non-positive price values")
        if (prediction["low"] > prediction["high"]).any():
            raise ValueError("Kronos prediction contains low above high")
