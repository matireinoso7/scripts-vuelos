#!/usr/bin/env python3
"""Argentina timezone timestamp for sheet Actualizado column."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def format_actualizado(dt: datetime | None = None) -> str:
    dt = dt or datetime.now(TZ)
    return dt.strftime("%d-%b-%Y %H:%M").upper()
