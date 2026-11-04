#!/usr/bin/env python3
"""Shared Playwright settings: faster loads, one browser per batch."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Browser, Page, Playwright, sync_playwright

# Keep stylesheets — Google Flights does not render offer cards without CSS.
BLOCK_RESOURCE_TYPES = frozenset({"image", "media", "font"})


def _route_handler(route) -> None:
    if route.request.resource_type in BLOCK_RESOURCE_TYPES:
        route.abort()
    else:
        route.continue_()


@contextmanager
def flight_browser(headless: bool = True) -> Iterator[tuple[Playwright, Browser]]:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        try:
            yield p, browser
        finally:
            browser.close()


def new_flight_page(browser: Browser, *, locale: str = "es-AR") -> Page:
    page = browser.new_page(locale=locale)
    page.route("**/*", _route_handler)
    return page
