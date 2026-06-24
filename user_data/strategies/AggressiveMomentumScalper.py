"""Aggressive, long-only spot momentum strategy for short paper-trading experiments.

This strategy deliberately seeks liquid 5-minute breakouts, then uses the 1-hour
trend as a brake. It is a research starting point, not a promise of profit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative
from pandas import DataFrame


class AggressiveMomentumScalper(IStrategy):
    """Trade high-volume momentum only when the higher timeframe agrees."""

    INTERFACE_VERSION = 3

    # The 5-minute chart finds entries; the decorator below supplies 1-hour trend data.
    timeframe = "5m"
    can_short = False
    process_only_new_candles = True
    startup_candle_count = 240

    # A hard circuit breaker. The trailing configuration locks gains only after +2.2%.
    stoploss = -0.055
    trailing_stop = True
    trailing_stop_positive = 0.012
    trailing_stop_positive_offset = 0.022
    trailing_only_offset_is_reached = True

    # Fallback ROI schedule. custom_roi below makes the same intent explicit in code.
    minimal_roi = {
        "0": 0.025,
        "30": 0.018,
        "90": 0.010,
        "180": 0.0,
    }
    use_custom_roi = True

    # Limit orders reduce taker fees/slippage in a scalping strategy. Emergency exits are
    # configured as market orders in config.json so a genuine stop is not left hanging.
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "emergency_exit": "market",
        "force_exit": "market",
        "force_entry": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    @informative("1h")
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Higher-timeframe indicators prevent buying a 5m bounce in a weak macro trend."""
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Calculate fast momentum, volatility, and liquidity measurements."""
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=21)

        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        bands = ta.BBANDS(
            dataframe,
            timeperiod=20,
            nbdevup=2.0,
            nbdevdn=2.0,
            matype=0,
        )
        dataframe["bb_upper"] = bands["upperband"]
        dataframe["bb_middle"] = bands["middleband"]
        dataframe["bb_lower"] = bands["lowerband"]
        dataframe["bb_width"] = (dataframe["bb_upper"] - dataframe["bb_lower"]) / dataframe[
            "bb_middle"
        ]

        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["volume_mean_20"] = dataframe["volume"].rolling(20).mean()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Enter only liquid, expanding 5m momentum aligned with the 1h trend."""
        trend_confirmed = (
            (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["ema_fast_1h"] > dataframe["ema_slow_1h"])
            & (dataframe["close"] > dataframe["ema_fast_1h"])
            & (dataframe["rsi_1h"] > 50)
        )
        momentum_confirmed = (
            (dataframe["rsi"] > 55)
            & (dataframe["rsi"] < 78)
            & (dataframe["macd"] > dataframe["macdsignal"])
            & (dataframe["macdhist"] > dataframe["macdhist"].shift(1))
            & (dataframe["close"] > dataframe["bb_middle"])
            & (dataframe["bb_width"] > 0.015)
        )
        liquid_and_tradeable = (
            (dataframe["volume"] > dataframe["volume_mean_20"] * 1.25)
            # Avoid dead markets and violent one-candle chaos. 0.35%-5% ATR is a
            # practical aggressive range for 5m liquid spot pairs.
            & (dataframe["atr_pct"] > 0.0035)
            & (dataframe["atr_pct"] < 0.05)
            & (dataframe["volume"] > 0)
        )
        # A close above the upper band is allowed only with exceptional volume.
        continuation_is_supported = (dataframe["close"] <= dataframe["bb_upper"]) | (
            dataframe["volume"] > dataframe["volume_mean_20"] * 1.8
        )

        dataframe.loc[
            trend_confirmed
            & momentum_confirmed
            & liquid_and_tradeable
            & continuation_is_supported,
            ["enter_long", "enter_tag"],
        ] = (1, "momentum_breakout")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit fading momentum quickly instead of waiting passively for the stoploss."""
        macd_cross_down = (dataframe["macd"] < dataframe["macdsignal"]) & (
            dataframe["macd"].shift(1) >= dataframe["macdsignal"].shift(1)
        )
        momentum_failed = (
            (dataframe["rsi"] < 46)
            | (macd_cross_down & (dataframe["close"] < dataframe["ema_fast"]))
            | (
                (dataframe["close"] < dataframe["bb_middle"])
                & (dataframe["volume"] < dataframe["volume_mean_20"])
            )
        )
        dataframe.loc[momentum_failed, "exit_long"] = 1
        return dataframe

    def custom_roi(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        trade_duration: int,
        entry_tag: Optional[str],
        side: str,
        **kwargs: object,
    ) -> Optional[float]:
        """Demand a quick win early, then release capital if momentum takes too long."""
        if trade_duration < 30:
            return 0.025
        if trade_duration < 90:
            return 0.018
        if trade_duration < 180:
            return 0.010
        return 0.0
