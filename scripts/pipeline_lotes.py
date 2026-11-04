#!/usr/bin/env python3
"""Run one or more scrape batches via run_flights.py (on demand)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
PROGRESS = ROOT / "scripts" / "scrape_progress.json"
CSV = ROOT / "sheet_live.csv"
RUN = ROOT / "scripts" / "run_flights.py"
WRITES = Path("/tmp/flight_writes.jsonl")
APPLY_SCRIPT = ROOT / "scripts" / "apply_mcp_writes.py"

from pipeline.step1_read import default_row_range  # noqa: E402


def load_progress() -> dict:
    return json.loads(PROGRESS.read_text(encoding="utf-8"))


def save_progress(data: dict) -> None:
    PROGRESS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def run_range(start: int, end: int, extra: list[str]) -> int:
    cmd = [
        sys.executable,
        str(RUN),
        "--all",
        "--no-purge",
        "--start-row",
        str(start),
        "--end-row",
        str(end),
        "--csv",
        str(CSV),
        *extra,
    ]
    return subprocess.call(cmd, cwd=str(ROOT))


def queue_mcp_apply(p: dict, batch_start: int, batch_end: int) -> None:
    total = count_jsonl_lines(WRITES)
    from_line = int(p.get("mcp_applied_lines", 0))
    if total <= from_line:
        return
    pending = list(p.get("mcp_pending_batches") or [])
    pending.append(
        {
            "batch_start": batch_start,
            "batch_end": batch_end,
            "from_line": from_line,
            "to_line": total,
        }
    )
    p["mcp_pending_batches"] = pending
    p["mcp_needs_apply"] = True


def main() -> None:
    ap = argparse.ArgumentParser(description="Batch wrapper for run_flights.py")
    ap.add_argument("--one-batch", action="store_true", help="Single batch from next_row")
    ap.add_argument("--max-batches", type=int, default=0, help="Max batches (0 = all remaining)")
    ap.add_argument("--batch-size", type=int, default=0, help="Override scrape_progress batch_size")
    ap.add_argument("--start-row", type=int, default=0, help="Override next_row for this run")
    ap.add_argument("--headful", action="store_true")
    ap.add_argument(
        "--apply-mcp",
        action="store_true",
        help="Queue MCP apply metadata after each batch (agent runs apply_mcp_writes + Google-sheets)",
    )
    args = ap.parse_args()

    p = load_progress()
    if CSV.exists():
        p["end_row"] = default_row_range(CSV)[1]
        p["data_rows"] = default_row_range(CSV)[1] - 1
    if args.batch_size > 0:
        p["batch_size"] = args.batch_size
        save_progress(p)
    if args.start_row > 0:
        p["next_row"] = args.start_row
        save_progress(p)

    start = int(p.get("next_row", 2))
    end_row = int(p.get("end_row", 238))
    batch = int(p.get("batch_size", 10))
    extra_base = ["--headful"] if args.headful else []
    first_batch = True

    batches_done = 0
    while start <= end_row:
        end = min(start + batch - 1, end_row)
        extra = list(extra_base)
        extra.append("--update-csv")
        if first_batch:
            extra.extend(["--fresh", "--fresh-writes"])
            first_batch = False
        print(f"Batch {start}-{end}...", flush=True)
        code = run_range(start, end, extra)
        p = load_progress()
        p["next_row"] = end + 1
        p["note"] = f"Último lote {start}-{end} (run_flights --all), exit={code}"
        if args.apply_mcp:
            queue_mcp_apply(p, start, end)
        p["flight_writes_lines"] = count_jsonl_lines(WRITES)
        save_progress(p)
        start = end + 1
        batches_done += 1
        if args.one_batch:
            break
        if args.max_batches and batches_done >= args.max_batches:
            break
        if start <= end_row:
            time.sleep(int(p.get("batch_pause_sec", 45)))
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
