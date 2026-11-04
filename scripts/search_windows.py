#!/usr/bin/env python3
"""All 25–30 day trip windows: ida from 01-MAR, vuelta through 05-APR (2027). February excluded."""
from __future__ import annotations

from datetime import date, timedelta

from trip_days import format_date_dd_mon, score_window

YEAR = 2027
MIN_LENGTH = 25
MAX_LENGTH = 30
EARLIEST_START = date(YEAR, 3, 1)
LATEST_APR_RETURN_DAY = 5


def all_trip_windows(year: int = YEAR) -> list[tuple[date, date, int, int, int]]:
    """Return (start, end, score, mar_days, length) sorted by score then mar days."""
    earliest = date(year, 3, 1)
    out: list[tuple[date, date, int, int, int]] = []
    seen: set[tuple[date, date]] = set()

    for length in range(MIN_LENGTH, MAX_LENGTH + 1):
        for day in range(1, 32):
            try:
                start = date(year, 3, day)
            except ValueError:
                continue
            if start < earliest:
                continue
            end = start + timedelta(days=length - 1)
            if end.year != year:
                continue
            if end.month == 4 and end.day > LATEST_APR_RETURN_DAY:
                continue
            if start.month == 2 or end.month == 2:
                continue
            key = (start, end)
            if key in seen:
                continue
            seen.add(key)
            score, mar, days = score_window(start, end)
            out.append((start, end, score, mar, days))

    out.sort(key=lambda x: (-x[2], -x[3], x[0], x[1]))
    return out


def fecha_cell(start: date, end: date) -> str:
    return f"{format_date_dd_mon(start)} a {format_date_dd_mon(end)}"


if __name__ == "__main__":
    wins = all_trip_windows()
    print(f"{len(wins)} windows")
    for start, end, score, mar, days in wins[:6]:
        print(fecha_cell(start, end), "len", days, "score", score)
