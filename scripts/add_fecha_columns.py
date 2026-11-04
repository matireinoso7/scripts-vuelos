#!/usr/bin/env python3
"""Merge Fecha Ida/Vuelta from archived export (by Link) into current sheet layout."""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from reorder_sheet import escalas_celda
from trip_days import format_date_es, format_fecha_rango, split_fechas
from datetime import date

SID = "1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE"
ARCHIVE = Path(__file__).resolve().parents[1] / "sheet_export.csv"


def fechas_from_link(link: str) -> tuple[str, str] | None:
    if not link:
        return None
    kayak = re.search(r"/(\d{4}-\d{2}-\d{2})/(\d{4}-\d{2}-\d{2})", link)
    if kayak:
        y1, m1, d1 = map(int, kayak.group(1).split("-"))
        y2, m2, d2 = map(int, kayak.group(2).split("-"))
        return format_date_es(date(y1, m1, d1)), format_date_es(date(y2, m2, d2))
    q = unquote(link)
    on = re.search(r"on%20(\d{4}-\d{2}-\d{2})|on%20(\d{4}-\d{2}-\d{2})", q)
    through = re.search(r"through%20(\d{4}-\d{2}-\d{2})", q)
    if not through:
        through = re.search(r"through%20(\d{4}-\d{2}-\d{2})", link)
    start_m = re.search(r"on%20(\d{4}-\d{2}-\d{2})", link)
    if start_m and through:
        y1, m1, d1 = map(int, start_m.group(1).split("-"))
        y2, m2, d2 = map(int, through.group(1).split("-"))
        return format_date_es(date(y1, m1, d1)), format_date_es(date(y2, m2, d2))
    return None


def load_fechas_by_link(archive: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    with archive.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            link = row.get("Link", "").strip()
            fechas = row.get("Fechas", "").strip()
            if link and fechas:
                out[link] = fechas
    return out


def build_rows(current_csv: str, fechas_map: dict[str, str]) -> list[list]:
    reader = csv.reader(io.StringIO(current_csv))
    rows = list(reader)
    header = rows[0]
    idx = {name: i for i, name in enumerate(header)}

    out: list[list] = [
        [
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
        ]
    ]

    for row in rows[1:]:
        if not any(c.strip() for c in row):
            continue
        while len(row) < len(header):
            row.append("")
        link = row[idx["Link"]].strip()
        fechas_raw = fechas_map.get(link)
        if fechas_raw:
            try:
                ida, vuelta = split_fechas(fechas_raw)
            except ValueError:
                ida, vuelta = "sin dato", "sin dato"
        else:
            parsed = fechas_from_link(link)
            if parsed:
                ida, vuelta = parsed
            else:
                ida, vuelta = "sin dato", "sin dato"

        precio = row[idx["Precio"]]
        if precio and precio != "sin dato":
            try:
                precio = int(float(precio))
            except ValueError:
                pass
        ida_txt = row[idx["Ida"]]
        vuelta_txt = row[idx["Vuelta"]]
        if "Cantidad de escalas" in idx and "Escala IDA" not in idx:
            # legacy sheet: recompute per leg from itinerary text
            esc_ida = escalas_celda(ida_txt)
            esc_vuelta = escalas_celda(vuelta_txt)
        elif "Escala IDA" in idx:
            esc_ida = row[idx["Escala IDA"]]
            esc_vuelta = row[idx["Escala VUELTA"]]
            if str(esc_ida).isdigit():
                esc_ida = int(esc_ida)
            if str(esc_vuelta).isdigit():
                esc_vuelta = int(esc_vuelta)
        else:
            esc_ida = escalas_celda(ida_txt)
            esc_vuelta = escalas_celda(vuelta_txt)
        dias = row[idx["Cantidad de dias de viaje"]]
        if str(dias).isdigit():
            dias = int(dias)

        fecha = format_fecha_rango(ida, vuelta)

        out.append(
            [
                precio,
                row[idx["Origen"]],
                row[idx["Destino"]],
                fecha,
                esc_ida,
                esc_vuelta,
                row[idx["Total Horas"]],
                ida_txt,
                vuelta_txt,
                dias,
                link,
            ]
        )
    return out


def main() -> None:
    archive = ARCHIVE
    fechas_map = load_fechas_by_link(archive)
    current = sys.stdin.read()
    rows = build_rows(current, fechas_map)
    payload = {
        "spreadsheetId": SID,
        "sheet": "Hoja 1",
        "cells": f"A1:K{len(rows)}",
        "parseInput": False,
        "values": rows,
    }
    json.dump(payload, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
