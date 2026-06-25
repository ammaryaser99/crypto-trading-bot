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
    """Trade active 5m momentum and pullbacks when the higher timeframe is acceptable."""

    INTERFACE_VERSION = 3

    # The 5-minute chart finds entries; the decorator below supplies 1-hour trend data.
    timeframe = "5m"
    can_short = False
    process_only_new_candles = True
    startup_candle_count = 240

    # A hard circuit breaker. This is intentionally aggressive for paper testing.
    stoploss = -0.065
    trailing_stop = True
    trailing_stop_positive = 0.009
    trailing_stop_positive_offset = 0.018
    trailing_only_offset_is_reached = True

    # Fallback ROI schedule. custom_roi below makes the same intent explicit in code.
    minimal_roi = {
        "0": 0.018,
        "20": 0.012,
        "60": 0.006,
        "120": 0.0,
    }
    use_custom_roi = True
    use_exit_signal = True

    @property
    def protections(self) -> list[dict]:
        """Session circuit breakers required by Freqtrade 2026.5 and newer.

        Keep these in the strategy (rather than config.json) so strategy
        behavior, risk limits, and backtests remain coupled.
        """
        return [
            # Prevent immediate revenge re-entry into a just-closed pair.
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            # Three stoploss-type exits in three hours lock all entries for two hours.
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 36,
                "trade_limit": 3,
                "stop_duration_candles": 24,
                "only_per_pair": False,
            },
            # A 15% drawdown across the prior 24 hours pauses new entries for four hours.
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 288,
                "trade_limit": 10,
                "stop_duration_candles": 48,
                "max_allowed_drawdown": 0.15,
            },
        ]

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
        """Enter active liquid momentum and trend pullbacks.

        This version is intentionally more active for a short paper experiment:
        it accepts a softer 1h trend and allows pullback entries, while still
        requiring non-dead volume and ATR so it does not buy totally flat chop.
        """
        trend_confirmed = (
            (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["close"] > dataframe["ema_slow"])
            & (
                (dataframe["ema_fast_1h"] > dataframe["ema_slow_1h"])
                | (
                    (dataframe["close"] > dataframe["ema_fast_1h"])
                    & (dataframe["rsi_1h"] > 45)
                )
            )
        )
        breakout_confirmed = (
            (dataframe["rsi"] > 50)
            & (dataframe["rsi"] < 82)
            & (dataframe["macd"] > dataframe["macdsignal"])
            & (dataframe["macdhist"] > 0)
            & (dataframe["close"] > dataframe["bb_middle"])
            & (dataframe["bb_width"] > 0.008)
        )
        pullback_confirmed = (
            (dataframe["rsi"] > 42)
            & (dataframe["rsi"] < 68)
            & (dataframe["close"] > dataframe["ema_slow"])
            & (dataframe["close"] <= dataframe["ema_fast"] * 1.01)
            & (dataframe["macdhist"] > dataframe["macdhist"].shift(1))
            & (dataframe["bb_width"] > 0.006)
        )
        liquid_and_tradeable = (
            (dataframe["volume"] > dataframe["volume_mean_20"] * 0.85)
            # Avoid dead markets and violent one-candle chaos. 0.15%-7% ATR is
            # deliberately active, but still avoids completely flat candles.
            & (dataframe["atr_pct"] > 0.0015)
            & (dataframe["atr_pct"] < 0.07)
            & (dataframe["volume"] > 0)
        )
        # A close above the upper band is allowed only with exceptional volume.
        continuation_is_supported = (dataframe["close"] <= dataframe["bb_upper"] * 1.006) | (
            dataframe["volume"] > dataframe["volume_mean_20"] * 1.30
        )

        dataframe.loc[
            trend_confirmed
            & breakout_confirmed
            & liquid_and_tradeable
            & continuation_is_supported,
            ["enter_long", "enter_tag"],
        ] = (1, "momentum_breakout_active")

        dataframe.loc[
            trend_confirmed
            & pullback_confirmed
            & liquid_and_tradeable,
            ["enter_long", "enter_tag"],
        ] = (1, "trend_pullback_active")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit fading momentum quickly instead of waiting passively for the stoploss."""
        macd_cross_down = (dataframe["macd"] < dataframe["macdsignal"]) & (
            dataframe["macd"].shift(1) >= dataframe["macdsignal"].shift(1)
        )
        momentum_failed = (
            (dataframe["rsi"] < 43)
            | (macd_cross_down & (dataframe["close"] < dataframe["ema_fast"]))
            | (
                (dataframe["close"] < dataframe["bb_middle"] * 0.997)
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
        if entry_tag == "trend_pullback_active":
            if trade_duration < 20:
                return 0.014
            if trade_duration < 60:
                return 0.009
            if trade_duration < 120:
                return 0.004
            return 0.0
        if trade_duration < 30:
            return 0.018
        if trade_duration < 60:
            return 0.012
        if trade_duration < 120:
            return 0.006
        return 0.0
