# Risk settings for the seven-day paper experiment

This is deliberately an aggressive **paper-only** profile, not a safe production profile. It looks for short, high-volume momentum moves on liquid spot pairs. That creates more trade opportunities and more false signals, which is precisely why the controls below are part of the experiment.

## Capital and position sizing

- `dry_run: true` makes every trade simulated. Do not change this during the experiment.
- `dry_run_wallet: 200` starts the test at 200 USDT.
- `max_open_trades: 5` limits simultaneous exposure while allowing the one-week paper test to stay active.
- `tradable_balance_ratio: 0.95` leaves 5% unallocated for fees, rounding, and safety.
- `stake_amount: unlimited` lets Freqtrade dynamically split available capital among the five slots instead of committing the whole wallet to one signal.

With a 200 USDT simulated wallet, a fully allocated slot is normally about 35-40 USDT. That is high enough to make a one-week test visible without putting the entire wallet into one coin.

## Per-trade loss and profit handling

- Hard stoploss: `-6.5%`. This is wider and higher risk than the first profile, but it is still a hard exit rather than an unlimited hold.
- Trailing stop: starts protecting a trade only after `+1.8%`; it trails at `0.9%`. This takes profits sooner during a fast paper test.
- ROI schedule: targets 1.8% early, then reduces to 1.2%, 0.6%, and finally releases capital after two hours. Pullback entries use slightly smaller ROI targets.
- Fast exit: RSI weakness, a MACD bearish cross below the fast EMA, or a weak return below the Bollinger midpoint triggers an exit signal.

## Session-level circuit breakers

Freqtrade protections are evaluated from completed trades and use 5-minute candles.

| Protection | Setting | Purpose |
| --- | --- | --- |
| CooldownPeriod | 2 candles (10 minutes) | Short pause after a close so the bot can remain active without instant churn. |
| StoplossGuard | 3 stoplosses in 36 candles | Pauses all new entries for 2 hours after repeated stoploss-type losses. |
| MaxDrawdown | 15% over 288 candles | Treats 24 hours as the daily loss window; pauses entries for 4 hours after enough closed trades show a 15% drawdown. |

The daily drawdown threshold is intentionally a circuit breaker, not a target. If it trips, inspect the market and logs; do not simply turn it off mid-test.

## What to inspect each day

1. Current equity versus the 200 USDT starting wallet.
2. Number of open trades and whether more than one sits in correlated coins.
3. StoplossGuard or MaxDrawdown messages in `scripts/status.sh` output.
4. Fees and slippage assumptions in backtests versus the paper fills.
5. Long losing streaks. A strategy can have a positive aggregate result while being too painful or fragile to deploy.

Do not enable live trading after a profitable seven-day sample alone. At minimum, test multiple market regimes, model fees/slippage conservatively, and review every protection trigger.
