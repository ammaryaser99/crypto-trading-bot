#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
TIMERANGE="${1:-20240101-}"

mkdir -p user_data/data
docker compose run --rm freqtrade download-data \
  --config /freqtrade/user_data/config.json \
  --config /freqtrade/user_data/config.static-pairs.json \
  --timeframes 5m 1h \
  --timerange "$TIMERANGE"
