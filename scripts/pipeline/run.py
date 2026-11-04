#!/usr/bin/env python3
"""
Legacy CLI — delegates scrape to run_flights.py (4-step pipeline).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    ap = argparse.ArgumentParser(description="Flight pipeline (legacy entry)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("urls", help="List URLs for one Link")
    a.add_argument("link")

    s = sub.add_parser("scrape", help="Run steps 2–4 (search→filter→save) for row range")
    s.add_argument("--start-row", type=int, required=True)
    s.add_argument("--end-row", type=int, required=True)
    s.add_argument("--csv", default=str(ROOT / "sheet_live.csv"))
    s.add_argument("--pause-sec", type=float, default=1.0)
    s.add_argument("--headful", action="store_true")
    s.add_argument("--mark-skipped-json", action="store_true", help="Ignored; rejections in step3 JSONL")

    args = ap.parse_args()
    if args.cmd == "urls":
        sys.path.insert(0, str(ROOT / "scripts"))
        from pipeline.step_a_urls import search_urls_for_link

        for u in search_urls_for_link(args.link):
            print(u)
        return

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_flights.py"),
        "--all",
        "--start-row",
        str(args.start_row),
        "--end-row",
        str(args.end_row),
        "--csv",
        args.csv,
        "--pause-sec",
        str(args.pause_sec),
    ]
    if args.headful:
        cmd.append("--headful")
    raise SystemExit(subprocess.call(cmd, cwd=str(ROOT)))


if __name__ == "__main__":
    main()
