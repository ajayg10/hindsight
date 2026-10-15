#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
if ! command -v docker >/dev/null 2>&1; then
  python3 scripts/phase0.py --blocked 'Docker executable absent on this host; container spikes did not run.'
  exit 2
fi
if ! docker info >/dev/null 2>&1; then
  python3 scripts/phase0.py --blocked 'Docker daemon inaccessible; container spikes did not run.'
  exit 2
fi
docker compose up -d --wait falkordb
docker compose --profile verify run --rm spikes
