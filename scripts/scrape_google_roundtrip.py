#!/usr/bin/env python3
"""Playwright: cheapest Google Flights round trip for a search URL."""
from __future__ import annotations

import argparse
import html
import re
import time

from playwright.sync_api import Page

from playwright_common import flight_browser, new_flight_page
from scrape_flight_link import ScrapedOffer, _fmt_leg

GOOGLE_OFFER_SEL = 'li.pIav2d div.JMc5Xc[aria-label*="precio total de ida y vuelta"]'


def _parse_label(lab: str) -> dict | None:
    lab = html.unescape(lab.replace("\xa0", " ")).replace("\u00a0", " ")
    pm = re.search(r"A partir de ([\d\.]+)\s*dólares", lab)
    if not pm or "precio total de ida y vuelta" not in lab:
        return None
    dm = re.search(
        r"Duración total: ([0-9]+)\s*h(?:\s*([0-9]+)\s*min)?",
        lab.replace("\xa0", " "),
    )
    if not dm:
        return None
    sm = re.search(r"Vuelo con (\d+) escala", lab)
    stops = 0
    if sm:
        stops = int(sm.group(1))
    elif "vuelo directo" not in lab.lower():
        return None
    am = re.search(r"escalas de ([^.]+)\.", lab)
    lay = re.findall(
        r"escala \(\d+ de \d+\) es una escala de [^.]+ en (.+?)\.\s*(?:Esta escala|$)",
        lab,
    )
    return {
        "price": int(pm.group(1).replace(".", "")),
        "dur": f"{dm.group(1)}h{(dm.group(2) or '0').zfill(2)}",
        "stops": stops,
        "airline": am.group(1).strip() if am else "?",
        "lay": lay,
        "label": lab,
    }


def _labels(page: Page) -> list[str]:
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('li.pIav2d div.JMc5Xc[aria-label]'))
        .map(e => e.getAttribute('aria-label'))
        .filter(x => x && x.includes('precio total de ida y vuelta'));"""
    )


def _departure_airport(lab: str) -> str:
    m = re.search(r"Sale de ([^.]+)\.", html.unescape(lab))
    return m.group(1).lower() if m else ""


def _is_return_leg_label(lab: str) -> bool:
    dep = _departure_airport(lab)
    if not dep:
        return False
    china = (
        "pudong",
        "shanghai",
        "shangh",
        "pekin",
        "pekín",
        "beijing",
        "capital",
        "daxing",
        "hongqiao",
    )
    return any(k in dep for k in china)


def _wait_for_offers(page: Page, timeout_ms: int = 45000) -> None:
    try:
        page.wait_for_selector(GOOGLE_OFFER_SEL, timeout=timeout_ms)
    except Exception:
        page.wait_for_timeout(min(8000, timeout_ms // 4))


def _offer_from_page_state(page: Page, raw_labels: list[str]) -> ScrapedOffer:
    outbound: list[dict] = []
    for i, lab in enumerate(raw_labels):
        parsed = _parse_label(lab)
        if parsed:
            parsed["card_index"] = i
            outbound.append(parsed)
    if not outbound:
        raise RuntimeError("No se encontraron vuelos de ida en Google Flights")
    best = min(outbound, key=lambda x: x["price"])
    offer_cards = page.locator("li.pIav2d").filter(
        has=page.locator('div.JMc5Xc[aria-label*="precio total de ida y vuelta"]')
    )
    offer_cards.nth(best["card_index"]).click(force=True, timeout=15000)
    ret_labels: list[str] = []
    for _ in range(8):
        try:
            page.wait_for_function(
                """() => {
                  const labs = Array.from(document.querySelectorAll('li.pIav2d div.JMc5Xc[aria-label]'))
                    .map(e => e.getAttribute('aria-label') || '');
                  return labs.some(l => /pekin|pekín|beijing|shanghai|pudong|capital|hongqiao|daxing/i.test(l));
                }""",
                timeout=6000,
            )
        except Exception:
            pass
        ret_labels = _labels(page)
        if any(_is_return_leg_label(l) for l in ret_labels):
            break
        if len(ret_labels) < max(1, len(raw_labels) // 3):
            break
        page.wait_for_timeout(1500)

    ret: list[dict] = []
    for lab in ret_labels:
        if not _is_return_leg_label(lab):
            continue
        parsed = _parse_label(lab)
        if parsed:
            ret.append(parsed)

    ob = best
    ida = _fmt_leg(ob["dur"], ob["airline"], ob["lay"])
    precio = ob["price"]
    vuelta = "sin dato"
    esc_vuelta = 0
    total = "sin dato"
    if ret:
        rb = min(ret, key=lambda x: x["price"])
        precio = rb["price"]
        vuelta = _fmt_leg(rb["dur"], rb["airline"], rb["lay"])
        esc_vuelta = rb["stops"]
        m1 = re.match(r"(\d+)h(\d+)", ob["dur"])
        m2 = re.match(r"(\d+)h(\d+)", rb["dur"])
        if m1 and m2:
            mins = int(m1.group(1)) * 60 + int(m1.group(2))
            mins += int(m2.group(1)) * 60 + int(m2.group(2))
            total = f"{mins // 60}h{mins % 60:02d}"
    return ScrapedOffer(
        precio=precio,
        ida=ida,
        vuelta=vuelta,
        esc_ida=ob["stops"],
        esc_vuelta=esc_vuelta,
        total_horas=total,
    )


def scrape_google_on_page(page: Page, url: str) -> ScrapedOffer:
    page.goto(url, timeout=90000, wait_until="domcontentloaded")
    _wait_for_offers(page)
    raw_labels = _labels(page)
    if not raw_labels:
        page.wait_for_timeout(4000)
        raw_labels = _labels(page)
    return _offer_from_page_state(page, raw_labels)


def scrape_google_url(url: str, wait_ms: int = 22000) -> ScrapedOffer:
    del wait_ms  # legacy arg; selector-based wait used instead
    last_err: Exception | None = None
    last_incomplete: ScrapedOffer | None = None
    for attempt in range(3):
        try:
            with flight_browser() as (_p, browser):
                page = new_flight_page(browser)
                offer = scrape_google_on_page(page, url)
            if not offer.vuelta.startswith("sin dato"):
                return offer
            last_incomplete = offer
            time.sleep(5)
        except RuntimeError as e:
            last_err = e
            time.sleep(5)
    if last_incomplete:
        return last_incomplete
    raise last_err or RuntimeError("Google scrape failed")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    args = ap.parse_args()
    print(scrape_google_url(args.url))


if __name__ == "__main__":
    main()
