#!/usr/bin/env python3
"""Step 5: remove sheet/CSV rows that violate price or stop limits."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from flight_policy import sheet_row_reject_reason

SPREADSHEET_ID = "1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE"
SHEET_NAME = "Hoja 1"
SHEET_ID = 0


def scan_violations(csv_path: Path) -> list[tuple[int, str, dict[str, str]]]:
    """Return (1-based row_num, reason, row_dict) for each violating data row."""
    text = csv_path.read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    out: list[tuple[int, str, dict[str, str]]] = []
    for i, row in enumerate(reader, start=2):
        reason = sheet_row_reject_reason(row)
        if reason:
            out.append((i, reason, dict(row)))
    return out


def purge_csv(csv_path: Path, *, dry_run: bool = False) -> tuple[int, list[int], list[dict]]:
    """
    Drop violating rows from CSV. Returns (kept_count, removed_row_nums_before_purge, removed_details).
    """
    violations = scan_violations(csv_path)
    if not violations:
        return _data_row_count(csv_path), [], []

    remove_nums = {r for r, _, _ in violations}
    text = csv_path.read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return 0, sorted(remove_nums), []

    fieldnames = list(rows[0].keys())
    kept = [r for idx, r in enumerate(rows, start=2) if idx not in remove_nums]
    details = [
        {"row": r, "reason": reason, "precio": row.get("Precio"), "esc_ida": row.get("Escala IDA"), "esc_vuelta": row.get("Escala VUELTA")}
        for r, reason, row in violations
    ]

    if not dry_run:
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(kept)
        csv_path.write_text(out.getvalue(), encoding="utf-8")

    return len(kept), sorted(remove_nums), details


def _data_row_count(csv_path: Path) -> int:
    text = csv_path.read_text(encoding="utf-8")
    return sum(1 for _ in csv.DictReader(io.StringIO(text)))


def mcp_delete_plan(removed_row_nums: list[int]) -> list[dict]:
    """Google Sheets delete_rows: must delete from highest row first (1-based)."""
    plan: list[dict] = []
    for row_num in sorted(removed_row_nums, reverse=True):
        plan.append(
            {
                "spreadsheetId": SPREADSHEET_ID,
                "sheetId": SHEET_ID,
                "dimension": "ROWS",
                "position": row_num,
                "count": 1,
            }
        )
    return plan


def write_purge_manifest(path: Path, removed: list[int], details: list[dict]) -> None:
    payload = {
        "removed_rows_1based_before_delete": removed,
        "removed_count": len(removed),
        "details": details,
        "mcp_delete_rows_or_columns": mcp_delete_plan(removed),
        "note": "Apply mcp_delete_rows_or_columns in order (high row first). Then re-export sheet to CSV.",
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
