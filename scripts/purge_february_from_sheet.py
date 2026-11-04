#!/usr/bin/env python3
"""List / filter sheet rows that touch February (Fecha or Link)."""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

from fecha_filter import fecha_touches_february, link_touches_february

ROOT = Path(__file__).resolve().parents[1]
SID = "1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE"
SHEET = "Hoja 1"


def row_is_february(row: dict[str, str]) -> bool:
    return fecha_touches_february(row.get("Fecha", "")) or link_touches_february(
        row.get("Link", "")
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=ROOT / "sheet_live.csv")
    ap.add_argument(
        "--write-filtered",
        type=Path,
        help="Write CSV without February rows (for compact sheet upload)",
    )
    ap.add_argument(
        "--emit-compact-json",
        action="store_true",
        help="Print write_range JSON for full data block A1:K{n}",
    )
    args = ap.parse_args()
    text = args.csv.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    kept: list[dict[str, str]] = []
    removed_rows: list[int] = []
    for sheet_row, row in enumerate(reader, start=2):
        if row_is_february(row):
            removed_rows.append(sheet_row)
        else:
            kept.append(row)
    if not args.emit_compact_json:
        print(json.dumps({"removed_sheet_rows": removed_rows, "count": len(removed_rows)}))
    if args.write_filtered:
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(kept)
        args.write_filtered.write_text(out.getvalue(), encoding="utf-8")
        sys.stderr.write(f"Wrote {len(kept)} data rows to {args.write_filtered}\n")
    if args.emit_compact_json:
        if not fieldnames:
            sys.exit(1)
        values = [fieldnames]
        for row in kept:
            values.append([row.get(c, "") for c in fieldnames])
        payload = {
            "spreadsheetId": SID,
            "sheet": SHEET,
            "cells": f"A1:K{len(values)}",
            "parseInput": False,
            "values": values,
        }
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
