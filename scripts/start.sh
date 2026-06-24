#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -f .env ]]; then
  echo "Missing .env. Create it first: cp .env.example .env"
  exit 1
fi

mkdir -p user_data/logs user_data/data user_data/backtest_results
docker compose --env-file .env up -d
docker compose ps
echo "Paper bot started. Follow logs with: docker compose logs -f freqtrade"
