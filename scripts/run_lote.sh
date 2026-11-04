#!/usr/bin/env bash
# Scrape sheet rows [START, END] via 4-step pipeline.
set -euo pipefail
START="${1:?start row}"
END="${2:?end row}"
CSV="${3:-/workspace/sheet_live.csv}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/run_flights.py" --all --start-row "$START" --end-row "$END" --csv "$CSV"
