from collections.abc import Sequence

import pandas as pd

from dusty_dragon.brokers.contracts import MarketBar

KRONOS_FEATURE_COLUMNS = ("open", "high", "low", "close", "volume")


def bars_to_kronos_frame(bars: Sequence[MarketBar]) -> pd.DataFrame:
    """Convert normalized broker bars to the frame expected by Kronos.

    Reference implementation:
    https://github.com/shiyu-coder/Kronos

    Kronos examples feed a timestamp series alongside Pandas OHLCV/K-line data.
    FX spot feeds generally do not provide centralized exchange volume, so Dusty
    Dragon deliberately maps MT5 ``tick_volume`` to the Kronos ``volume`` field.
    That provenance must remain explicit in reports and future model evaluation.

    The bridge accepts only one symbol/timeframe per frame to prevent accidental
    cross-series contamination during forecasting or backtesting.
    """
    if not bars:
        raise ValueError("cannot build a Kronos frame from zero market bars")

    symbols = {bar.symbol for bar in bars}
    timeframes = {bar.timeframe for bar in bars}
    if len(symbols) != 1:
        raise ValueError("Kronos frame requires bars from exactly one symbol")
    if len(timeframes) != 1:
        raise ValueError("Kronos frame requires bars from exactly one timeframe")

    ordered = sorted(bars, key=lambda bar: bar.opened_at)
    timestamps = [bar.opened_at for bar in ordered]
    if len(set(timestamps)) != len(timestamps):
        raise ValueError("Kronos frame cannot contain duplicate timestamps")

    frame = pd.DataFrame(
        {
            "timestamps": timestamps,
            "open": [bar.open for bar in ordered],
            "high": [bar.high for bar in ordered],
            "low": [bar.low for bar in ordered],
            "close": [bar.close for bar in ordered],
            "volume": [bar.tick_volume for bar in ordered],
        }
    )
    frame.attrs["symbol"] = next(iter(symbols))
    frame.attrs["timeframe"] = next(iter(timeframes))
    frame.attrs["volume_source"] = "mt5_tick_volume"
    return frame


def split_kronos_inputs(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Return feature and timestamp objects ready for ``KronosPredictor.predict``."""
    missing = {"timestamps", *KRONOS_FEATURE_COLUMNS}.difference(frame.columns)
    if missing:
        raise ValueError(f"Kronos frame is missing required columns: {sorted(missing)}")

    features = frame.loc[:, list(KRONOS_FEATURE_COLUMNS)].copy()
    timestamps = pd.to_datetime(frame["timestamps"], utc=True)
    return features, timestamps
