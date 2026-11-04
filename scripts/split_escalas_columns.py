#!/usr/bin/env python3
"""Replace Cantidad de escalas with Escala IDA / Escala VUELTA."""
from __future__ import annotations

import csv
import io
import json
import sys

from reorder_sheet import escalas_celda
from trip_days import format_fecha_rango

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
    idx = {name: i for i, name in enumerate(rows[0])}
    out: list[list] = [HEADER]

    for row in rows[1:]:
        if not any(c.strip() for c in row):
            continue
        while len(row) < len(rows[0]):
            row.append("")

        ida = row[idx["Ida"]]
        vuelta = row[idx["Vuelta"]]
        precio = row[idx["Precio"]]
        if precio and precio != "sin dato":
            try:
                precio = int(float(precio))
            except ValueError:
                pass
        dias = row[idx["Cantidad de dias de viaje"]]
        if str(dias).isdigit():
            dias = int(dias)

        if "Fecha" in idx:
            fecha = row[idx["Fecha"]]
        else:
            fecha = format_fecha_rango(
                row[idx["Fecha Ida"]].strip(),
                row[idx["Fecha Vuelta"]].strip(),
            )

        out.append(
            [
                precio,
                row[idx["Origen"]],
                row[idx["Destino"]],
                fecha,
                escalas_celda(ida),
                escalas_celda(vuelta),
                row[idx["Total Horas"]],
                ida,
                vuelta,
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
            "parseInput": True,
            "values": rows,
        },
        sys.stdout,
        ensure_ascii=False,
    )


if __name__ == "__main__":
    main()
