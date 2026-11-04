#!/usr/bin/env python3
"""Scrape sheet rows [start, end] via run_flights.py --all."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-row", type=int, required=True, help="1-based sheet row (>=2)")
    ap.add_argument("--end-row", type=int, required=True)
    ap.add_argument("--csv", default="-", help="Sheet export CSV with header")
    args = ap.parse_args()

    csv_path = args.csv
    cleanup: Path | None = None
    if args.csv == "-":
        cleanup = Path(tempfile.mkstemp(suffix=".csv")[1])
        cleanup.write_text(sys.stdin.read(), encoding="utf-8")
        csv_path = str(cleanup)

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_flights.py"),
        "--all",
        "--start-row",
        str(args.start_row),
        "--end-row",
        str(args.end_row),
        "--csv",
        csv_path if csv_path != "-" else str(ROOT / "sheet_live.csv"),
    ]
    try:
        rc = subprocess.call(cmd, cwd=str(ROOT))
    finally:
        if cleanup:
            cleanup.unlink(missing_ok=True)
    sys.exit(rc)


if __name__ == "__main__":
    main()
