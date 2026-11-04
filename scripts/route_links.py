#!/usr/bin/env python3
"""Build search URLs from Origen, Destino, and trip dates."""
from __future__ import annotations

from datetime import date

from trip_days import parse_fecha_column

ROUTE_TEMPLATES: dict[tuple[str, str], str] = {
    ("Buenos Aires", "Shanghái"): "https://www.google.com/travel/flights/search?q=Flights%20to%20Shanghai%20from%20Buenos%20Aires%20on%20{ida}%20through%20{vuelta}&curr=USD&hl=es",
    ("Buenos Aires", "Pekín"): "https://www.google.com/travel/flights/search?q=Flights%20to%20Beijing%20from%20EZE%20on%20{ida}%20through%20{vuelta}&curr=USD&hl=es",
    ("Buenos Aires", "Tokio"): "https://www.google.com/travel/flights/search?q=Flights%20to%20TYO%20from%20BUE%20on%20{ida}%20through%20{vuelta}&curr=USD&hl=es",
    ("Mendoza (incluye vuelo Mendoza–Buenos Aires)", "Shanghái"): "https://www.kayak.com.ar/flights/MDZ-PVG/{ida}/{vuelta}?sort=price_a",
    ("Mendoza (incluye vuelo Mendoza–Buenos Aires)", "Pekín"): "https://www.google.com/travel/flights/search?q=Flights%20to%20Beijing%20from%20MDZ%20on%20{ida}%20through%20{vuelta}&curr=USD&hl=es",
    ("Chile", "Tokio"): "https://www.google.com/travel/flights/search?q=Flights%20to%20TYO%20from%20SCL%20on%20{ida}%20through%20{vuelta}&curr=USD&hl=es",
    ("Chile", "Pekín"): "https://www.google.com/travel/flights/search?q=Flights%20to%20Beijing%20from%20Santiago%20de%20Chile%20on%20{ida}%20through%20{vuelta}&curr=USD&hl=es",
    ("Chile", "Shanghái"): "https://www.google.com/travel/flights/search?q=Flights%20to%20Shanghai%20from%20Santiago%20de%20Chile%20on%20{ida}%20through%20{vuelta}&curr=USD&hl=es",
}


class UnknownRouteError(ValueError):
    def __init__(self, origen: str, destino: str) -> None:
        super().__init__(f"Sin plantilla de link para {origen!r} → {destino!r}")
        self.origen = origen
        self.destino = destino


def link_for_dates(origen: str, destino: str, ida: date, vuelta: date) -> str:
    key = (origen.strip(), destino.strip())
    tmpl = ROUTE_TEMPLATES.get(key)
    if not tmpl:
        raise UnknownRouteError(origen, destino)
    return tmpl.format(ida=ida.isoformat(), vuelta=vuelta.isoformat())


def link_from_fecha_cell(origen: str, destino: str, fecha_cell: str, year: int = 2027) -> str:
    ida, vuelta = parse_fecha_column(fecha_cell.strip(), year)
    return link_for_dates(origen, destino, ida, vuelta)
