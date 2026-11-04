#!/usr/bin/env python3
"""Playwright: cheapest Kayak round trip (MDZ-PVG etc.)."""
from __future__ import annotations

import argparse
import re

from playwright.sync_api import Page

from playwright_common import flight_browser, new_flight_page
from scrape_flight_link import ScrapedOffer, _fmt_leg

KAYAK_PRICE_HINT = re.compile(r"US\$[\s]*([\d,]+)")


def _dismiss_cookies(page: Page) -> None:
    for sel in (
        'button:has-text("Aceptar")',
        'button:has-text("Accept")',
        'button:has-text("Entendido")',
        'button:has-text("Acepto")',
    ):
        try:
            page.locator(sel).first.click(timeout=1500)
            return
        except Exception:
            pass


def _parse_kayak_body(html: str, text: str) -> ScrapedOffer:
    prices = [int(x.replace(",", "")) for x in KAYAK_PRICE_HINT.findall(html + text)]
    if not prices:
        prices = [int(x.replace(",", "")) for x in re.findall(r"\$\s*([\d,]+)", text)]
    prices = [p for p in prices if 400 <= p <= 15000]
    if not prices:
        raise RuntimeError("Kayak: no se encontró precio en la página")
    precio = min(prices)
    durs = re.findall(r"(\d+)\s*h\s*(\d+)\s*m", text, re.I)
    ida = vuelta = "sin dato"
    esc_ida = esc_vuelta = 0
    if len(durs) >= 2:
        ida = f"{durs[0][0]}h{durs[0][1].zfill(2)} (ver Kayak)"
        vuelta = f"{durs[1][0]}h{durs[1][1].zfill(2)} (ver Kayak)"
        mins = int(durs[0][0]) * 60 + int(durs[0][1]) + int(durs[1][0]) * 60 + int(durs[1][1])
        total = f"{mins // 60}h{mins % 60:02d}"
    else:
        total = "sin dato"
    return ScrapedOffer(
        precio=precio,
        ida=ida,
        vuelta=vuelta,
        esc_ida=esc_ida,
        esc_vuelta=esc_vuelta,
        total_horas=total,
        notas="Kayak: revisar escalas en link si faltan paréntesis",
    )


def scrape_kayak_on_page(page: Page, url: str) -> ScrapedOffer:
    page.goto(url, timeout=90000, wait_until="domcontentloaded")
    _dismiss_cookies(page)
    try:
        page.wait_for_function(
            """() => /US\\$\\s*[\\d,]+/.test(document.body.innerText)""",
            timeout=35000,
        )
    except Exception:
        page.wait_for_timeout(5000)
    html = page.content()
    text = page.inner_text("body")
    return _parse_kayak_body(html, text)


def scrape_kayak_url(url: str, wait_ms: int = 25000) -> ScrapedOffer:
    del wait_ms
    with flight_browser() as (_p, browser):
        page = new_flight_page(browser)
        return scrape_kayak_on_page(page, url)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    args = ap.parse_args()
    print(scrape_kayak_url(args.url))


if __name__ == "__main__":
    main()
