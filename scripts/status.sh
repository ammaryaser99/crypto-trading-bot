#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
docker compose ps
echo
echo "Recent bot logs:"
docker compose logs --tail 80 freqtrade
