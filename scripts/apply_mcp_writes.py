#!/usr/bin/env python3
"""Load write_range payloads from flight_writes.jsonl (for MCP apply)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from flight_policy import MAX_PRICE_USD  # noqa: E402


def iter_payloads(path: Path, from_line: int = 0):
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        if i < from_line or not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("status"):
            continue
        precio = payload.get("values", [[None]])[0][0]
        if isinstance(precio, (int, float)) and precio > MAX_PRICE_USD:
            continue
        yield i, payload


def count_payload_lines(path: Path) -> int:
    return sum(1 for _ in path.read_text(encoding="utf-8").splitlines() if _.strip())


def main() -> None:
    ap = argparse.ArgumentParser(description="Export MCP write_range payloads from JSONL")
    ap.add_argument("--path", type=Path, default=Path("/tmp/flight_writes.jsonl"))
    ap.add_argument("--from-line", type=int, default=0, help="0-based line index to start")
    ap.add_argument("--dump", action="store_true", help="Print JSON array of payloads to stdout")
    ap.add_argument("--count", action="store_true", help="Print number of data lines in file")
    args = ap.parse_args()
    if not args.path.exists():
        print(0 if args.count else "[]")
        return
    if args.count:
        print(count_payload_lines(args.path))
        return
    payloads = [p for _, p in iter_payloads(args.path, args.from_line)]
    if args.dump:
        json.dump(payloads, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    print(f"{len(payloads)} payloads from line {args.from_line}", file=sys.stderr)
    for _, p in iter_payloads(args.path, args.from_line):
        print(json.dumps(p, ensure_ascii=False))


if __name__ == "__main__":
    main()
