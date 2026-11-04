#!/usr/bin/env python3
"""Execution timestamp for column Actualizado (America/Buenos_Aires)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("America/Buenos_Aires")
except Exception:
    TZ = timezone(timedelta(hours=-3))
MONTHS = ("ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC")


def format_actualizado(when: datetime | None = None) -> str:
    dt = when or datetime.now(TZ)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    else:
        dt = dt.astimezone(TZ)
    mon = MONTHS[dt.month - 1]
    return f"{dt.day:02d}-{mon}-{dt.year} {dt.hour:02d}:{dt.minute:02d}"
