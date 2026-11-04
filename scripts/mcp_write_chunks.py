#!/usr/bin/env python3
"""Print write_range JSON payloads for Google Sheets MCP (stdout, one per chunk)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/workspace/mcp_backfill.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    values = data["values"]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    for i in range(0, len(values), size):
        chunk = values[i : i + size]
        r1 = i + 1
        r2 = i + len(chunk)
        payload = {
            "spreadsheetId": data["spreadsheetId"],
            "sheet": data["sheet"],
            "cells": f"A{r1}:K{r2}",
            "parseInput": False,
            "values": chunk,
        }
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
