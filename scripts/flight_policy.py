#!/usr/bin/env python3
"""Acceptance rules for scraped offers (price and stops)."""
from __future__ import annotations

from scrape_flight_link import ScrapedOffer

MAX_PRICE_USD = 2300
MAX_STOPS_PER_LEG = 2  # reject if esc_ida or esc_vuelta >= 3


def offer_complete(offer: ScrapedOffer) -> bool:
    return not offer.ida.startswith("sin dato") and not offer.vuelta.startswith("sin dato")


def reject_reason(offer: ScrapedOffer | None) -> str | None:
    if offer is None:
        return "search_failed"
    if not offer_complete(offer):
        return "incomplete"
    if int(offer.precio) > MAX_PRICE_USD:
        return "over_budget"
    if offer.esc_ida > MAX_STOPS_PER_LEG or offer.esc_vuelta > MAX_STOPS_PER_LEG:
        return "too_many_stops"
    return None


def offer_acceptable(offer: ScrapedOffer) -> bool:
    return reject_reason(offer) is None


class OverBudgetError(RuntimeError):
    def __init__(self, precio: int) -> None:
        super().__init__(f"Precio {precio} USD supera tope {MAX_PRICE_USD}")
        self.precio = precio


def _parse_int_cell(value: str) -> int | None:
    v = (value or "").strip().replace(",", "")
    if not v or "sin dato" in v.lower():
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def sheet_row_reject_reason(row: dict[str, str]) -> str | None:
    """Reason to remove an existing sheet/CSV row (price or stops only)."""
    precio = _parse_int_cell(row.get("Precio", ""))
    if precio is not None and precio > MAX_PRICE_USD:
        return "over_budget"
    esc_ida = _parse_int_cell(row.get("Escala IDA", ""))
    esc_vuelta = _parse_int_cell(row.get("Escala VUELTA", ""))
    if esc_ida is not None and esc_ida > MAX_STOPS_PER_LEG:
        return "too_many_stops"
    if esc_vuelta is not None and esc_vuelta > MAX_STOPS_PER_LEG:
        return "too_many_stops"
    return None
