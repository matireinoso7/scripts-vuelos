#!/usr/bin/env python3
"""Print write_range JSON lines (20 data rows each) from filtered CSV."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline.step_c_sheet import FIELDS  # noqa: E402

SID = "1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE"
SHEET = "Hoja 1"
CHUNK = 20


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "sheet_live.csv")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    fn = FIELDS
    for r in rows:
        for c in fn:
            r.setdefault(c, "")
    payloads = [
        {
            "spreadsheetId": SID,
            "sheet": SHEET,
            "cells": "A1:L1",
            "parseInput": False,
            "values": [fn],
        }
    ]
    for i in range(0, len(rows), CHUNK):
        chunk = rows[i : i + CHUNK]
        start_row = i + 2
        end_row = start_row + len(chunk) - 1
        values = [[r.get(c, "") for c in fn] for r in chunk]
        payloads.append(
            {
                "spreadsheetId": SID,
                "sheet": SHEET,
                "cells": f"A{start_row}:L{end_row}",
                "parseInput": False,
                "values": values,
            }
        )
    for p in payloads:
        print(json.dumps(p, ensure_ascii=False))


if __name__ == "__main__":
    main()
