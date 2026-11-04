#!/usr/bin/env python3
"""Step 1: read sheet rows (CSV export) — origin, destination, dates, refreshed link."""
from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from route_links import UnknownRouteError, link_for_dates
from trip_days import format_date_es, parse_fecha_column


@dataclass
class SheetRowRequest:
    row_num: int
    origen: str
    destino: str
    fecha: str
    fecha_ida: str
    fecha_vuelta: str
    link: str
    link_previous: str
    dias_viaje: str
    raw: dict[str, str]
    link_error: str | None = None


def year_from_link(link: str, default: int = 2027) -> int:
    m = re.search(r"(20\d{2})-\d{2}-\d{2}", link or "")
    return int(m.group(1)) if m else default


def data_row_count(csv_path: Path | str) -> int:
    path = Path(csv_path)
    text = path.read_text(encoding="utf-8")
    return sum(1 for _ in csv.DictReader(io.StringIO(text)))


def default_row_range(csv_path: Path | str) -> tuple[int, int]:
    n = data_row_count(csv_path)
    if n == 0:
        return 2, 1
    return 2, n + 1


def load_requests(
    csv_path: Path | str,
    start_row: int,
    end_row: int,
    *,
    refresh_links: bool = True,
) -> list[SheetRowRequest]:
    path = Path(csv_path)
    text = path.read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    out: list[SheetRowRequest] = []
    for rnum in range(start_row, end_row + 1):
        idx = rnum - 2
        if idx < 0 or idx >= len(rows):
            continue
        row = rows[idx]
        fecha = (row.get("Fecha") or "").strip()
        link_previous = (row.get("Link") or "").strip()
        origen = (row.get("Origen") or "").strip()
        destino = (row.get("Destino") or "").strip()
        year = year_from_link(link_previous)
        ida_d: date | None = None
        vuelta_d: date | None = None
        link_error: str | None = None
        link = link_previous
        fecha_ida = fecha_vuelta = "sin dato"
        try:
            ida_d, vuelta_d = parse_fecha_column(fecha, year)
            fecha_ida = format_date_es(ida_d)
            fecha_vuelta = format_date_es(vuelta_d)
            if refresh_links:
                try:
                    link = link_for_dates(origen, destino, ida_d, vuelta_d)
                except UnknownRouteError as e:
                    link_error = str(e)
        except ValueError as e:
            link_error = str(e)
        out.append(
            SheetRowRequest(
                row_num=rnum,
                origen=origen,
                destino=destino,
                fecha=fecha,
                fecha_ida=fecha_ida,
                fecha_vuelta=fecha_vuelta,
                link=link,
                link_previous=link_previous,
                dias_viaje=(row.get("Cantidad de dias de viaje") or "").strip(),
                raw=dict(row),
                link_error=link_error,
            )
        )
    return out


def request_to_json(req: SheetRowRequest) -> dict:
    return asdict(req)
