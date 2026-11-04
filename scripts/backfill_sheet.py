#!/usr/bin/env python3
"""Fill sin dato cells from best complete row per route (origen, destino)."""
from __future__ import annotations

import csv
import io
import json
import sys
from dataclasses import dataclass

from reorder_sheet import escalas_celda

SID = "1x0uFv5uXDMSGTcMcxFyJDJyxlRunb2_ScLy5snc3pfE"
FIELDS = ["Precio", "Origen", "Destino", "Fecha", "Escala IDA", "Escala VUELTA", "Total Horas", "Ida", "Vuelta", "Cantidad de dias de viaje", "Link"]
FILL_COLS = ("Precio", "Escala IDA", "Escala VUELTA", "Total Horas", "Ida", "Vuelta")
ROUTE_ALIASES: dict[tuple[str, str], tuple[str, str]] = {("Mendoza", "Tokio"): ("Buenos Aires", "Tokio")}


def is_missing(val: str) -> bool:
    if val is None:
        return True
    s = str(val).strip()
    return not s or s.lower() == "sin dato"


def completeness(row: dict[str, str]) -> int:
    return sum(1 for c in FILL_COLS if not is_missing(row.get(c, "")))


@dataclass
class RouteTemplate:
    precio: str | int
    esc_ida: str | int
    esc_vuelta: str | int
    total: str
    ida: str
    vuelta: str


def build_templates(rows: list[dict[str, str]]) -> dict[tuple[str, str], RouteTemplate]:
    best: dict[tuple[str, str], tuple[int, RouteTemplate]] = {}
    for row in rows:
        key = (row["Origen"].strip(), row["Destino"].strip())
        score = completeness(row)
        if score < 4:
            continue
        ida, vuelta = row.get("Ida", ""), row.get("Vuelta", "")
        esc_ida = row.get("Escala IDA", "")
        esc_vuelta = row.get("Escala VUELTA", "")
        if is_missing(esc_ida) and not is_missing(ida):
            esc_ida = escalas_celda(ida)
        if is_missing(esc_vuelta) and not is_missing(vuelta):
            esc_vuelta = escalas_celda(vuelta)
        tpl = RouteTemplate(precio=row.get("Precio", "sin dato"), esc_ida=esc_ida, esc_vuelta=esc_vuelta, total=row.get("Total Horas", "sin dato"), ida=ida, vuelta=vuelta)
        if key not in best or score > best[key][0]:
            best[key] = (score, tpl)
    templates = {k: v[1] for k, v in best.items()}
    for route, alias in ROUTE_ALIASES.items():
        if route not in templates and alias in templates:
            templates[route] = templates[alias]
    return templates


def apply_template(out: dict[str, str], tpl: RouteTemplate, *, fill_precio: bool) -> None:
    fields = (("Escala IDA", tpl.esc_ida), ("Escala VUELTA", tpl.esc_vuelta), ("Total Horas", tpl.total), ("Ida", tpl.ida), ("Vuelta", tpl.vuelta))
    if fill_precio:
        fields = (("Precio", tpl.precio),) + fields
    for col, val in fields:
        if is_missing(out.get(col, "")) and not is_missing(str(val)):
            out[col] = val


def normalize_row(row: dict[str, str], tpl: RouteTemplate | None) -> list:
    out = dict(row)
    if tpl:
        apply_template(out, tpl, fill_precio=True)
    ida, vuelta = out.get("Ida", ""), out.get("Vuelta", "")
    if is_missing(out.get("Escala IDA", "")) and not is_missing(ida):
        out["Escala IDA"] = escalas_celda(ida)
    if is_missing(out.get("Escala VUELTA", "")) and not is_missing(vuelta):
        out["Escala VUELTA"] = escalas_celda(vuelta)
    precio = out.get("Precio", "")
    if not is_missing(precio):
        try:
            precio = int(float(str(precio)))
        except ValueError:
            pass
    else:
        precio = "sin dato"
    dias = out.get("Cantidad de dias de viaje", "")
    if str(dias).isdigit():
        dias = int(dias)
    for col in ("Escala IDA", "Escala VUELTA"):
        v = out.get(col, "")
        if str(v).isdigit():
            out[col] = int(v)
    return [precio, out["Origen"], out["Destino"], out["Fecha"], out.get("Escala IDA", "sin dato"), out.get("Escala VUELTA", "sin dato"), out.get("Total Horas", "sin dato"), out.get("Ida", "sin dato"), out.get("Vuelta", "sin dato"), dias, out.get("Link", "")]


def process(csv_text: str) -> list[list]:
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    templates = build_templates(rows)
    header = [FIELDS]
    body = [normalize_row(row, templates.get((row["Origen"].strip(), row["Destino"].strip()))) for row in rows]
    return header + body


def main() -> None:
    csv_text = sys.stdin.read()
    all_rows = process(csv_text)
    json.dump({"spreadsheetId": SID, "sheet": "Hoja 1", "cells": f"A1:K{len(all_rows)}", "parseInput": False, "values": all_rows}, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
