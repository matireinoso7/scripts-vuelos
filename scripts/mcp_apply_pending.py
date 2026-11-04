#!/usr/bin/env python3
"""Manage MCP apply queue in scrape_progress.json (agent applies via Google-sheets MCP)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
PROGRESS = ROOT / "scripts" / "scrape_progress.json"
WRITES = Path("/tmp/flight_writes.jsonl")

def load_progress() -> dict:
    return json.loads(PROGRESS.read_text(encoding="utf-8"))


def save_progress(data: dict) -> None:
    PROGRESS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", action="store_true", help="Print JSON array of payloads for next pending batch")
    ap.add_argument("--mark-done", action="store_true", help="Mark current pending batch as applied")
    ap.add_argument("--status", action="store_true", help="Print pending batch count")
    args = ap.parse_args()
    p = load_progress()
    pending = list(p.get("mcp_pending_batches") or [])

    if args.status:
        print(json.dumps({"pending_batches": len(pending), "mcp_applied_lines": p.get("mcp_applied_lines", 0)}))
        return

    if not pending:
        if args.dump:
            print("[]")
        return

    batch = pending[0]
    from_line = int(batch["from_line"])
    to_line = int(batch["to_line"])

    if args.dump:
        lines = WRITES.read_text(encoding="utf-8").splitlines() if WRITES.exists() else []
        payloads = []
        for i in range(from_line, min(to_line, len(lines))):
            line = lines[i].strip()
            if line:
                payloads.append(json.loads(line))
        json.dump(payloads, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    if args.mark_done:
        p["mcp_applied_lines"] = to_line
        pending.pop(0)
        p["mcp_pending_batches"] = pending
        if not pending:
            p["mcp_needs_apply"] = False
        p["note"] = (
            p.get("note", "")
            + f"; MCP applied lines {from_line}-{to_line} batch {batch.get('batch_start')}-{batch.get('batch_end')}"
        )
        save_progress(p)
        print(f"marked applied through line {to_line}", file=sys.stderr)


if __name__ == "__main__":
    main()
