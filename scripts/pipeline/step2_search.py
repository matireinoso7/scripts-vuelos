#!/usr/bin/env python3
"""Step 2: search flights via Playwright (no price/stop filter)."""
from __future__ import annotations

from scrape_flight_link import ScrapedOffer
from scrape_google_roundtrip import scrape_google_on_page, scrape_google_url
from scrape_kayak_roundtrip import scrape_kayak_on_page, scrape_kayak_url

from flight_policy import offer_complete
from pipeline.step_a_urls import kayak_to_google


def search_offer(link: str, page=None, *, check_budget: bool = False) -> ScrapedOffer:
    """Scrape cheapest offer from Link; budget check off for step 2 (filter in step 3)."""
    del check_budget  # scrapers may still optimize; step 3 is source of truth
    if "google.com/travel/flights" in link:
        if page is not None:
            return scrape_google_on_page(page, link)
        return scrape_google_url(link)
    if "kayak" in link:
        alt = kayak_to_google(link)
        offer: ScrapedOffer | None = None
        try:
            offer = scrape_kayak_on_page(page, link) if page else scrape_kayak_url(link)
        except RuntimeError:
            offer = None
        if offer and offer_complete(offer):
            return offer
        if alt:
            if page is not None:
                return scrape_google_on_page(page, alt)
            return scrape_google_url(alt)
        if offer:
            return offer
        raise RuntimeError("Kayak scrape failed and no Google fallback")
    raise ValueError(f"Unsupported link: {link}")
