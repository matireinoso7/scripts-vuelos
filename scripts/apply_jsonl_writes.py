#!/usr/bin/env python3
"""Print MCP write_range payloads from JSONL (for manual/agent apply)."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/flight_writes.jsonl")
    if not path.exists():
        print("no file", file=sys.stderr)
        sys.exit(1)
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        json.loads(line)  # validate
        print(line)
        n += 1
    print(f"# {n} payloads", file=sys.stderr)


if __name__ == "__main__":
    main()
