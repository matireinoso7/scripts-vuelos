#!/usr/bin/env python3
"""Backward-compatible price checks (see flight_policy.py)."""
from __future__ import annotations

from flight_policy import MAX_PRICE_USD, OverBudgetError, offer_acceptable
from scrape_flight_link import ScrapedOffer


def offer_within_budget(offer: ScrapedOffer) -> bool:
    return int(offer.precio) <= MAX_PRICE_USD
