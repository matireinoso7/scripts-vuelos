#!/usr/bin/env python3
"""Apply all queued MCP batches via Google Sheets API (requires agent MCP — prints payloads)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PENDING = ROOT / "scripts" / "mcp_apply_pending.py"


def main() -> None:
    while True:
        st = subprocess.check_output(
            [sys.executable, str(PENDING), "--status"], text=True
        )
        info = json.loads(st)
        if info["pending_batches"] == 0:
            break
        out = subprocess.check_output([sys.executable, str(PENDING), "--dump"], text=True)
        payloads = json.loads(out or "[]")
        print(json.dumps({"action": "apply", "count": len(payloads), "payloads": payloads}))
        subprocess.check_call([sys.executable, str(PENDING), "--mark-done"])


if __name__ == "__main__":
    main()
