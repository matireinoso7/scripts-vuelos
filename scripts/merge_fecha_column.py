#!/usr/bin/env python3
"""Replace Fecha Ida / Fecha Vuelta with one Fecha column (DD-MON a DD-MON)."""
from __future__ import annotations

import csv
import io
import json
import sys

from trip_days import format_fecha_rango, normalize_fecha_cell

SID = "1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE"

HEADER = [
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


def transform(current_csv: str) -> list[list]:
    reader = csv.reader(io.StringIO(current_csv))
    rows = list(reader)
    if not rows:
        return [HEADER]
    idx = {name: i for i, name in enumerate(rows[0])}
    out: list[list] = [HEADER]

    for row in rows[1:]:
        if not any(c.strip() for c in row):
            continue
        while len(row) < len(rows[0]):
            row.append("")

        if "Fecha" in idx and "Fecha Ida" not in idx:
            fecha = normalize_fecha_cell(row[idx["Fecha"]].strip())
        elif "Fecha Ida" in idx:
            fecha = format_fecha_rango(
                row[idx["Fecha Ida"]].strip(),
                row[idx["Fecha Vuelta"]].strip(),
            )
        else:
            fecha = "sin dato"

        precio = row[idx["Precio"]]
        if precio and precio != "sin dato":
            try:
                precio = int(float(precio))
            except ValueError:
                pass

        esc_ida = row[idx["Escala IDA"]]
        esc_vuelta = row[idx["Escala VUELTA"]]
        if str(esc_ida).isdigit():
            esc_ida = int(esc_ida)
        if str(esc_vuelta).isdigit():
            esc_vuelta = int(esc_vuelta)

        dias = row[idx["Cantidad de dias de viaje"]]
        if str(dias).isdigit():
            dias = int(dias)

        out.append(
            [
                precio,
                row[idx["Origen"]],
                row[idx["Destino"]],
                fecha,
                esc_ida,
                esc_vuelta,
                row[idx["Total Horas"]],
                row[idx["Ida"]],
                row[idx["Vuelta"]],
                dias,
                row[idx["Link"]],
            ]
        )
    return out


def main() -> None:
    rows = transform(sys.stdin.read())
    json.dump(
        {
            "spreadsheetId": SID,
            "sheet": "Hoja 1",
            "cells": f"A1:K{len(rows)}",
            "parseInput": False,
            "values": rows,
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
