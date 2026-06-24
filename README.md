# Aggressive Momentum Freqtrade Paper Bot

An aggressive, long-only Freqtrade spot bot for a **seven-day paper-trading experiment**. It scans liquid USDT markets for 5-minute momentum breakouts and confirms the broader 1-hour trend before entering. RSI, EMA trend, MACD, Bollinger Bands, volume, and ATR all participate in the decision.

> **Experimental and high risk. Paper trading only.** This repository starts with `dry_run: true`, a 200 USDT simulated wallet, and no real API keys. It is not financial advice and does not promise profit. Do not enable live trading until you have reviewed backtests, paper results, fees/slippage, and every risk setting.

## What is included

- Official `freqtradeorg/freqtrade:stable` Docker deployment.
- `AggressiveMomentumScalper`: 5m trend/momentum entries with 1h trend confirmation and fast failure exits.
- Dynamic liquid-USDT universe using `VolumePairList`, plus a static ten-pair fallback for reproducible data downloads/backtests.
- Controlled aggressive risk: four maximum positions, 5.5% hard stop, gain-protecting trailing stop, cooldown, stoploss guard, and 24-hour 12% max-drawdown circuit breaker.
- Optional Telegram notifications and a loopback-only API/Web UI, configured through `.env` rather than source control.
- Download, backtest, start, stop, and status scripts.

Read [the risk guide](docs/RISK_SETTINGS.md) before starting. VPS-specific details are in [the deployment guide](docs/SETUP_VPS.md).

## Repository layout

```text
.
├── docker-compose.yml
├── .env.example
├── user_data/
│   ├── config.json                 # Dynamic live-paper pair universe
│   ├── config.static-pairs.json    # Stable backtest/download universe
│   └── strategies/AggressiveMomentumScalper.py
├── scripts/
│   ├── start.sh
│   ├── stop.sh
│   ├── status.sh
│   ├── download_data.sh
│   └── backtest.sh
└── docs/
```

## Quick start: Ubuntu or other Linux host

Install Docker Engine and the Compose plugin, then:

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY.git crypto-freqtrade
cd crypto-freqtrade
cp .env.example .env
chmod +x scripts/*.sh
nano .env
./scripts/start.sh
./scripts/status.sh
```

The bot is already configured for spot dry-run. Its startup log must include a dry-run confirmation. If it does not, stop immediately and inspect `user_data/config.json` before doing anything else.

## Configure `.env`

`.env` is ignored by Git. Start with `cp .env.example .env`.

- `EXCHANGE_NAME=binance` is the default; Freqtrade/CCXT exchange names can be substituted if they support your intended spot market and pair format.
- `EXCHANGE_KEY`, `EXCHANGE_SECRET`, and `EXCHANGE_PASSWORD` are blank by default. Keep exchange withdrawals disabled on any key you create.
- Set `TELEGRAM_ENABLED=true` only after setting `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID`.
- Change `API_PASSWORD` and `API_JWT_SECRET_KEY` before use. The dashboard is intentionally not exposed to the internet.

## Operations

```bash
# Start in the background (and restart after VPS reboots)
./scripts/start.sh

# See container state and the last 80 log lines
./scripts/status.sh

# Follow logs continuously
docker compose logs -f freqtrade

# Stop gracefully
./scripts/stop.sh
```

The API/Web UI listens at `127.0.0.1:8080` on the VPS. Use an SSH tunnel instead of opening the port publicly:

```bash
ssh -L 8080:127.0.0.1:8080 YOUR_USER@YOUR_VPS_IP
```

Then visit `http://127.0.0.1:8080` locally. More VPS hardening guidance is in [docs/SETUP_VPS.md](docs/SETUP_VPS.md).

## Download data and backtest

The scripts use the static fallback universe for reproducibility: BTC, ETH, SOL, BNB, XRP, DOGE, ADA, AVAX, LINK, and TON quoted in USDT.

```bash
# Download 5m and 1h candles from 1 January 2024 through today.
./scripts/download_data.sh 20240101-

# Backtest the same period and export trades to user_data/backtest_results/.
./scripts/backtest.sh 20240101-
```

Use a smaller period when iterating, for example `20260101-20260601`. Before trusting a result, compare:

| Metric | Why it matters |
| --- | --- |
| Total profit and profit factor | Shows aggregate outcome, but can hide fragile gains. |
| Maximum drawdown | Shows the worst capital dip; compare it with the 12% daily circuit breaker. |
| Win rate | A low win rate can be acceptable only if average wins materially exceed average losses. |
| Average trade duration | This strategy expects relatively short holds; long holds may indicate weak exit logic. |
| Maximum consecutive losses | Reveals whether the wallet and your tolerance can survive a losing streak. |

Backtests are not live performance. They can understate spread, latency, partial fills, fees, and exchange outages. Do not optimize solely on a single week or a single bull-market period.

## Pairs

Normal paper operation uses a dynamic `VolumePairList`: the 20 largest liquid USDT markets, then age, precision, price, spread, stability, and volatility filters remove bad candidates. Leveraged token patterns and stablecoin-to-USDT markets are excluded.

For a fixed production-like paper universe, replace the `pairlists` block in `user_data/config.json` with the `StaticPairList` block from `user_data/config.static-pairs.json`, or launch a one-off command with both config files as shown in `scripts/backtest.sh`.

## Seven-day monitoring checklist

1. Day 0: run a data download and at least one backtest. Confirm dry-run in logs.
2. Days 1-2: check logs and dashboard twice daily; confirm expected pairs and no exchange/API errors.
3. Every day: record equity, closed trades, win rate, fees, average trade duration, drawdown, and longest losing streak.
4. When a protection triggers: leave it enabled, capture the surrounding market conditions, and investigate rather than immediately restarting the bot.
5. Day 7: compare actual paper fills with backtest assumptions and decide whether the strategy deserves more paper testing. Do not use a single seven-day result as permission for live money.

## Safety boundaries

- `dry_run` defaults to `true`; live trading is not enabled or documented as a quick switch.
- No API key, Telegram token, database, log, or backtest output is tracked by Git.
- The UI/API binds to loopback only and requires credentials supplied from `.env`.
- This is spot-only and long-only. It does not use leverage, futures, martingale, or averaging down.

## Push this repository to GitHub

After reviewing the initial commit, create an empty GitHub repository without adding a README/license, then run:

```bash
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPOSITORY.git
git branch -M main
git push -u origin main
```

Use a private GitHub repository if you plan to keep your VPS configuration adjacent to the project, even though `.env` is ignored.
