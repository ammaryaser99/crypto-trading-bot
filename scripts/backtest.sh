#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
TIMERANGE="${1:-20240101-}"
RESULT="/freqtrade/user_data/backtest_results/AggressiveMomentumScalper-$(date +%Y%m%d-%H%M%S).json"

mkdir -p user_data/backtest_results
docker compose run --rm freqtrade backtesting \
  --config /freqtrade/user_data/config.json \
  --config /freqtrade/user_data/config.static-pairs.json \
  --strategy AggressiveMomentumScalper \
  --timerange "$TIMERANGE" \
  --export trades \
  --export-filename "$RESULT"

echo "Backtest complete. Results were saved under user_data/backtest_results/."
