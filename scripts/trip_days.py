#!/usr/bin/env python3
"""Parse Spanish date ranges from the Vuelos sheet and compute inclusive trip days."""

from __future__ import annotations

import re
from datetime import date, timedelta

MONTHS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def _month_num(token: str) -> int:
    key = token.lower().replace("á", "a")[:3]
    if key not in MONTHS:
        raise ValueError(f"Unknown month: {token}")
    return MONTHS[key]


def _parse_fechas_simple(text: str) -> tuple[date, date]:
    t = text.strip().lower()
    year_m = re.search(r"(\d{4})\s*$", t)
    if not year_m:
        raise ValueError(text)
    year = int(year_m.group(1))
    body = t[: year_m.start()].strip()

    parts = re.split(r"\s*-\s*", body)
    if len(parts) != 2:
        raise ValueError(text)

    def parse_part(part: str, default_month: int | None = None) -> date:
        part = part.strip()
        dm = re.match(r"^(\d{1,2})\s+([a-záéíóúñ]+)$", part)
        if dm:
            return date(year, _month_num(dm.group(2)), int(dm.group(1)))
        dm = re.match(r"^(\d{1,2})$", part)
        if dm and default_month:
            return date(year, default_month, int(dm.group(1)))
        raise ValueError(part)

    left = parts[0].strip()
    right = parts[1].strip()

    right_dm = re.match(r"^(\d{1,2})\s+([a-záéíóúñ]+)$", right)
    if not right_dm:
        raise ValueError(text)
    end = date(year, _month_num(right_dm.group(2)), int(right_dm.group(1)))

    left_dm = re.match(r"^(\d{1,2})\s+([a-záéíóúñ]+)$", left)
    if left_dm:
        start = date(year, _month_num(left_dm.group(2)), int(left_dm.group(1)))
    else:
        left_d = re.match(r"^(\d{1,2})$", left)
        if not left_d:
            raise ValueError(text)
        start = date(year, end.month, int(left_d.group(1)))

    if end < start:
        raise ValueError(f"End before start: {text}")
    return start, end


MONTHS_ES = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}


def format_date_es(d: date) -> str:
    return f"{d.day} {MONTHS_ES[d.month]} {d.year}"


def format_date_dd_mm(d: date) -> str:
    return f"{d.day:02d}-{d.month:02d}"


def format_date_dd_mon(d: date) -> str:
    return f"{d.day:02d}-{MONTHS_ES[d.month].upper()}"


def _parse_fecha_token(part: str, year: int) -> date:
    part = part.strip()
    dm = re.match(r"^(\d{1,2})-(\d{1,2})$", part)
    if dm:
        return date(year, int(dm.group(2)), int(dm.group(1)))
    dm = re.match(r"^(\d{1,2})-([a-záéíóúñ]{3})$", part, re.I)
    if dm:
        return date(year, _month_num(dm.group(2)), int(dm.group(1)))
    raise ValueError(part)


def parse_fecha_column(text: str, year: int = 2027) -> tuple[date, date]:
    t = text.strip()
    if not t or "sin dato" in t.lower():
        raise ValueError(text)
    parts = re.split(r"\s+a\s+", t, flags=re.I)
    if len(parts) != 2:
        raise ValueError(text)
    return _parse_fecha_token(parts[0], year), _parse_fecha_token(parts[1], year)


def normalize_fecha_cell(text: str, year: int = 2027) -> str:
    if not text or "sin dato" in text.strip().lower():
        return "sin dato"
    start, end = parse_fecha_column(text, year)
    return f"{format_date_dd_mon(start)} a {format_date_dd_mon(end)}"


def parse_date_es(text: str) -> date:
    t = text.strip().lower()
    m = re.match(r"^(\d{1,2})\s+([a-záéíóúñ]+)\s+(\d{4})$", t)
    if not m:
        raise ValueError(text)
    return date(int(m.group(3)), _month_num(m.group(2)), int(m.group(1)))


def format_fecha_rango(ida: str, vuelta: str) -> str:
    if not ida or not vuelta:
        return "sin dato"
    if "sin dato" in ida.lower() or "sin dato" in vuelta.lower():
        return "sin dato"
    start, end = parse_date_es(ida), parse_date_es(vuelta)
    return f"{format_date_dd_mon(start)} a {format_date_dd_mon(end)}"


def split_fechas(text: str) -> tuple[str, str]:
    start, end = _parse_fechas_simple(text)
    return format_date_es(start), format_date_es(end)


def inclusive_days(text: str) -> int:
    start, end = _parse_fechas_simple(text)
    return (end - start).days + 1


def days_in_month(text: str, month: int) -> int:
    start, end = _parse_fechas_simple(text)
    count = 0
    d = start
    while d <= end:
        if d.month == month:
            count += 1
        d += timedelta(days=1)
    return count


def score_window(start: date, end: date) -> tuple[int, int, int]:
    days = (end - start).days + 1
    mar = sum(1 for i in range(days) if (start + timedelta(days=i)).month == 3)
    feb = sum(1 for i in range(days) if (start + timedelta(days=i)).month == 2)
    score = mar - 3 * feb
    return score, mar, days


def candidate_windows(year: int = 2027, limit: int | None = 15) -> list[tuple[date, date, int, int, int]]:
    from search_windows import all_trip_windows

    wins = all_trip_windows(year)
    if limit is None:
        return wins
    return wins[:limit]


if __name__ == "__main__":
    samples = [
        "20 may - 14 jun 2027",
        "15 feb - 10 mar 2027",
        "2 - 27 mar 2027",
        "2 - 26 feb 2027",
    ]
    for s in samples:
        print(s, "->", inclusive_days(s))

    print("\nTop windows:")
    for start, end, score, mar, days in candidate_windows()[:8]:
        print(start, end, "days", days, "mar", mar, "score", score)
