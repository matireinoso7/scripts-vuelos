#!/usr/bin/env python3
"""Step 3: filter offers (price, stops, completeness)."""
from __future__ import annotations

from scrape_flight_link import ScrapedOffer

from flight_policy import offer_acceptable, reject_reason


def filter_offer(offer: ScrapedOffer | None) -> tuple[ScrapedOffer | None, str | None]:
    reason = reject_reason(offer)
    if reason:
        return None, reason
    assert offer is not None
    return offer, None


def status_line(row: int, reason: str, **extra: object) -> dict:
    return {"row": row, "status": "rejected", "reason": reason, **extra}
