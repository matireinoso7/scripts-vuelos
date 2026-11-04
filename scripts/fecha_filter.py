#!/usr/bin/env python3
"""Skip rows whose Fecha touches February (policy: no February trips)."""
from __future__ import annotations

import re

_FEB_RE = re.compile(r"\bfeb\b|febrero", re.I)


def fecha_touches_february(fecha: str) -> bool:
    if not fecha or "sin dato" in fecha.lower():
        return False
    return bool(_FEB_RE.search(fecha))


def link_touches_february(link: str) -> bool:
    if not link:
        return False
    return "-02-" in link or "%2F02%2F" in link or "%2F2027-02-" in link
