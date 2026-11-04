#!/usr/bin/env python3
"""Step A: resolve search URLs (Kayak → Google fallback URL)."""
from __future__ import annotations

import re
from urllib.parse import quote


def kayak_to_google(url: str) -> str | None:
    m = re.search(
        r"kayak\.com\.ar/flights/([A-Z]{3})-([A-Z]{3})/(\d{4}-\d{2}-\d{2})/(\d{4}-\d{2}-\d{2})",
        url,
    )
    if not m:
        return None
    orig, dest, ida, vuelta = m.groups()
    city = {"PVG": "Shanghai", "PEK": "Beijing", "BJS": "Beijing"}.get(dest, dest)
    q = f"Flights to {city} from {orig} on {ida} through {vuelta}"
    return (
        "https://www.google.com/travel/flights/search?q="
        + quote(q)
        + "&curr=USD&hl=es"
    )


def search_urls_for_link(link: str) -> list[str]:
    """Ordered URLs to try for one sheet Link cell."""
    if "google.com/travel/flights" in link:
        return [link]
    if "kayak" in link:
        alt = kayak_to_google(link)
        return [link] + ([alt] if alt else [])
    raise ValueError(f"Unsupported link: {link}")
