# Risk settings for the seven-day paper experiment

This is deliberately an aggressive **paper-only** profile, not a safe production profile. It looks for short, high-volume momentum moves on liquid spot pairs. That creates more trade opportunities and more false signals, which is precisely why the controls below are part of the experiment.

## Capital and position sizing

- `dry_run: true` makes every trade simulated. Do not change this during the experiment.
- `dry_run_wallet: 200` starts the test at 200 USDT.
- `max_open_trades: 4` limits simultaneous exposure. It is deliberately below the top-20 dynamic pair universe.
- `tradable_balance_ratio: 0.90` leaves 10% unallocated for fees, rounding, and safety.
- `stake_amount: unlimited` lets Freqtrade dynamically split available capital among the four slots instead of committing the whole wallet to one signal.

With a 200 USDT simulated wallet, a fully allocated slot is normally about 45-50 USDT. That is high enough to make a one-week test meaningful without putting the entire wallet into one coin.

## Per-trade loss and profit handling

- Hard stoploss: `-5.5%`. This is wide enough for a volatile 5-minute crypto move, but it is still a hard exit rather than an unlimited hold.
- Trailing stop: starts protecting a trade only after `+2.2%`; it trails at `1.2%`. This avoids instantly choking a breakout while giving back less when it reverses.
- ROI schedule: targets 2.5% in the first 30 minutes, then reduces to 1.8%, 1.0%, and finally exits on the strategy signal after three hours. Scalps that cannot move should release their capital.
- Fast exit: RSI weakness, a MACD bearish cross below the fast EMA, or a weak return below the Bollinger midpoint triggers an exit signal.

## Session-level circuit breakers

Freqtrade protections are evaluated from completed trades and use 5-minute candles.

| Protection | Setting | Purpose |
| --- | --- | --- |
| CooldownPeriod | 5 candles (25 minutes) | Stops immediate revenge re-entry on the same pair after a close. |
| StoplossGuard | 2 stoplosses in 48 candles | Pauses all new entries for 4 hours after two stoploss-type losses. |
| MaxDrawdown | 12% over 288 candles | Treats 24 hours as the daily loss window; pauses entries for 6 hours after enough closed trades show a 12% drawdown. |

The daily drawdown threshold is intentionally a circuit breaker, not a target. If it trips, inspect the market and logs; do not simply turn it off mid-test.

## What to inspect each day

1. Current equity versus the 200 USDT starting wallet.
2. Number of open trades and whether more than one sits in correlated coins.
3. StoplossGuard or MaxDrawdown messages in `scripts/status.sh` output.
4. Fees and slippage assumptions in backtests versus the paper fills.
5. Long losing streaks. A strategy can have a positive aggregate result while being too painful or fragile to deploy.

Do not enable live trading after a profitable seven-day sample alone. At minimum, test multiple market regimes, model fees/slippage conservatively, and review every protection trigger.
