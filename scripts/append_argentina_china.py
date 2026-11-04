#!/usr/bin/env python3
"""Build new sheet rows for missing Argentina→China windows; output append JSON."""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from datetime import date
from route_links import link_for_dates
from search_windows import all_trip_windows, fecha_cell
from trip_days import format_date_dd_mon

SID = "1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE"

ROUTES: list[tuple[str, str, str]] = [
    ("Buenos Aires", "Shanghái", "Shanghai"),
    ("Buenos Aires", "Pekín", "Beijing"),
    ("Mendoza (incluye vuelo Mendoza–Buenos Aires)", "Shanghái", "PVG"),
    ("Mendoza (incluye vuelo Mendoza–Buenos Aires)", "Pekín", "Beijing"),
]


def dates_from_link(link: str) -> tuple[date, date] | None:
    m = re.search(r"/(\d{4}-\d{2}-\d{2})/(\d{4}-\d{2}-\d{2})", link)
    if m:
        y1, m1, d1 = map(int, m.group(1).split("-"))
        y2, m2, d2 = map(int, m.group(2).split("-"))
        return date(y1, m1, d1), date(y2, m2, d2)
    on = re.search(r"on%20(\d{4}-\d{2}-\d{2})", link)
    through = re.search(r"through%20(\d{4}-\d{2}-\d{2})", link)
    if on and through:
        y1, m1, d1 = map(int, on.group(1).split("-"))
        y2, m2, d2 = map(int, through.group(1).split("-"))
        return date(y1, m1, d1), date(y2, m2, d2)
    return None


def load_existing_keys(sheet_csv: str) -> set[tuple[str, str, date, date]]:
    keys: set[tuple[str, str, date, date]] = set()
    reader = csv.DictReader(io.StringIO(sheet_csv))
    for row in reader:
        origen = row.get("Origen", "").strip()
        destino = row.get("Destino", "").strip()
        fecha = row.get("Fecha", "").strip()
        link = row.get("Link", "").strip()
        start = end = None
        if link:
            parsed = dates_from_link(link)
            if parsed:
                start, end = parsed
        if start is None and fecha and "sin dato" not in fecha.lower():
            try:
                from trip_days import parse_fecha_column

                start, end = parse_fecha_column(fecha)
            except ValueError:
                pass
        if start and end and origen and destino:
            keys.add((origen, destino, start, end))
    return keys


def build_new_rows(sheet_csv: str) -> list[list]:
    existing = load_existing_keys(sheet_csv)
    rows: list[list] = []
    for start, end, _score, _mar, length in all_trip_windows():
        for origen, destino, _code in ROUTES:
            if (origen, destino, start, end) in existing:
                continue
            link = link_for_dates(origen, destino, start, end)
            rows.append(
                [
                    "sin dato",
                    origen,
                    destino,
                    fecha_cell(start, end),
                    "sin dato",
                    "sin dato",
                    "sin dato",
                    "sin dato",
                    "sin dato",
                    length,
                    link,
                    "",
                ]
            )
            existing.add((origen, destino, start, end))
    return rows


def main() -> None:
    sheet = sys.stdin.read()
    rows = build_new_rows(sheet)
    sys.stderr.write(f"new_rows={len(rows)}\n")
    json.dump(
        {
            "spreadsheetId": SID,
            "sheet": "Hoja 1",
            "values": rows,
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
