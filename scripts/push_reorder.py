#!/usr/bin/env python3
"""Print write_range JSON for reordered Vuelos sheet (stdin = current CSV export)."""
from __future__ import annotations

import json
import sys

from reorder_sheet import reorder_csv

SID = "1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE"


def normalize(rows: list[list]) -> list[list]:
    out = []
    for i, row in enumerate(rows):
        r = list(row)
        if i > 0:
            if r[0] and r[0] != "sin dato":
                try:
                    r[0] = int(float(str(r[0]).replace(",", "")))
                except ValueError:
                    pass
            if r[7] and str(r[7]).isdigit():
                r[7] = int(r[7])
            if r[3] and str(r[3]).isdigit():
                r[3] = int(r[3])
        out.append(r)
    return out


def main() -> None:
    rows = normalize(reorder_csv(sys.stdin.read()))
    payload = {
        "spreadsheetId": SID,
        "sheet": "Hoja 1",
        "cells": f"A1:I{len(rows)}",
        "parseInput": True,
        "values": rows,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
