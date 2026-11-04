#!/usr/bin/env python3
"""Step C: build Google Sheets write_range payloads."""
from __future__ import annotations

import json
from typing import Any

from scrape_flight_link import ScrapedOffer
from trip_days import parse_fecha_column

SPREADSHEET_ID = "1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE"
SHEET_NAME = "Hoja 1"

FIELDS = [
    "Precio",
    "Origen",
    "Destino",
    "Fecha",
    "Escala IDA",
    "Escala VUELTA",
    "Total Horas",
    "Ida",
    "Vuelta",
    "Cantidad de dias de viaje",
    "Link",
    "Actualizado",
]


def inclusive_trip_days(fecha_cell: str, year: int = 2027) -> int | str:
    try:
        start, end = parse_fecha_column(fecha_cell.strip(), year)
        return (end - start).days + 1
    except ValueError:
        return "sin dato"


def row_values(
    sheet_row: dict[str, str],
    offer: ScrapedOffer,
    link: str,
    *,
    actualizado: str,
    trip_year: int = 2027,
) -> list[Any]:
    fecha = sheet_row.get("Fecha", "")
    days = inclusive_trip_days(fecha, trip_year)
    return [
        offer.precio,
        sheet_row["Origen"],
        sheet_row["Destino"],
        fecha,
        offer.esc_ida,
        offer.esc_vuelta,
        offer.total_horas,
        offer.ida,
        offer.vuelta,
        days,
        link,
        actualizado,
    ]


def write_range_payload(row_num: int, values: list[Any]) -> dict[str, Any]:
    return {
        "spreadsheetId": SPREADSHEET_ID,
        "sheet": SHEET_NAME,
        "cells": f"A{row_num}:L{row_num}",
        "parseInput": False,
        "values": [values],
    }


def header_payload() -> dict[str, Any]:
    return {
        "spreadsheetId": SPREADSHEET_ID,
        "sheet": SHEET_NAME,
        "cells": "A1:L1",
        "parseInput": False,
        "values": [FIELDS],
    }


def emit_jsonl(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False) + "\n"
