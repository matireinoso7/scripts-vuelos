#!/usr/bin/env python3
"""List JSONL write payloads not yet recorded in applied manifest."""
from __future__ import annotations

import json
import sys
from pathlib import Path

WRITES = Path("/tmp/flight_writes.jsonl")
APPLIED = Path("/tmp/applied_sheet_rows.txt")


def main() -> None:
    applied: set[str] = set()
    if APPLIED.exists():
        applied = {x.strip() for x in APPLIED.read_text().splitlines() if x.strip()}
    if not WRITES.exists():
        return
    for line in WRITES.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        payload = json.loads(line)
        row = payload["cells"].split(":")[0]
        if row in applied:
            continue
        print(line)


if __name__ == "__main__":
    main()
