#!/usr/bin/env python3
"""Summarize write_range JSONL for MCP apply (agent applies via Google-sheets)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from flight_policy import MAX_PRICE_USD  # noqa: E402


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/flight_writes.jsonl")
    ok = over = skip = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("status"):
            skip += 1
            continue
        precio = payload.get("values", [[None]])[0][0]
        if isinstance(precio, (int, float)) and precio > MAX_PRICE_USD:
            over += 1
            continue
        ok += 1
    print(
        f"{path}: {ok} write_range OK (≤{MAX_PRICE_USD} USD), "
        f"{over} over budget (omit), {skip} status lines — apply OK via Google-sheets MCP."
    )


if __name__ == "__main__":
    main()
