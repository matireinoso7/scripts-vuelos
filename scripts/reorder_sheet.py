#!/usr/bin/env python3
"""Build reordered rows for the Vuelos sheet."""
from __future__ import annotations

import csv
import io
import re
import sys


def escalas_en_tramo(texto: str) -> int | None:
    if not texto or "sin dato" in texto.lower():
        return None
    m = re.search(r"\(([^)]+)\)", texto)
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).split("+") if p.strip()]
    return len(parts) if parts else None


def escalas_celda(texto: str) -> str | int:
    n = escalas_en_tramo(texto)
    return "sin dato" if n is None else n


def count_escalas(ida: str, vuelta: str) -> str:
    """Deprecated: prefer escalas_celda per leg."""
    a, b = escalas_en_tramo(ida), escalas_en_tramo(vuelta)
    if a is None and b is None:
        return "sin dato"
    if a is None:
        return str(b)
    if b is None:
        return str(a)
    return str(max(a, b))


def reorder_csv(content: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return []
    header = rows[0]
    idx = {name: i for i, name in enumerate(header)}
    out: list[list[str]] = [
        [
            "Precio",
            "Origen",
            "Destino",
            "Cantidad de escalas",
            "Total Horas",
            "Ida",
            "Vuelta",
            "Cantidad de dias de viaje",
            "Link",
        ]
    ]
    for row in rows[1:]:
        if not any(cell.strip() for cell in row):
            continue
        while len(row) < 9:
            row.append("")
        origen = row[idx.get("Origen", 0)]
        destino = row[idx.get("Destino", 1)]
        precio = row[idx.get("Precio i/v (USD)", 3)]
        ida = row[idx.get("Ida", 4)]
        vuelta = row[idx.get("Vuelta", 5)]
        total = row[idx.get("Total", 6)]
        link = row[idx.get("Link", 7)]
        dias = row[idx.get("Días viaje", 8)]
        escalas = count_escalas(ida, vuelta)
        out.append([precio, origen, destino, escalas, total, ida, vuelta, dias, link])
    return out


if __name__ == "__main__":
    data = sys.stdin.read()
    w = csv.writer(sys.stdout)
    for row in reorder_csv(data):
        w.writerow(row)
