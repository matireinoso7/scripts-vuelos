#!/usr/bin/env python3
"""Scrape cheapest round-trip offer from a Google Flights or Kayak URL (headless Chrome)."""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass


@dataclass
class ScrapedOffer:
    precio: int
    ida: str
    vuelta: str
    esc_ida: int
    esc_vuelta: int
    total_horas: str
    notas: str = ""


def _norm(s: str) -> str:
    s = html.unescape(s).replace("\xa0", " ")
    s = unicodedata.normalize("NFKD", s)
    return s


def _short_city(name: str) -> str:
    """Turn long airport phrase into sheet-style city label."""
    name = name.strip()
    low = name.lower()
    if " de " in low:
        name = name.split(" de ")[-1].strip()
    name = re.sub(r"\s*ADD\b", "", name).strip()
    replacements = {
        "São Paulo-Guarulhos": "São Paulo",
        "São Paulo": "São Paulo",
        "Adís Abeba": "Adís Abeba",
        "Istanbul Airport": "Estambul",
        "Aeropuerto Internacional de Pekín": "Pekín",
        "Buenos Aires": "Buenos Aires",
        "Ezeiza": "Ezeiza",
    }
    for k, v in replacements.items():
        if k.lower() in low:
            return v
    if len(name) > 40:
        name = name.split(",")[0]
    return name


def _fmt_leg(duration: str, airline: str, layovers: list[str]) -> str:
    cities = " + ".join(_short_city(x) for x in layovers if x)
    if cities:
        return f"{duration} {airline} ({cities})"
    return f"{duration} {airline}"


def _parse_google(html_text: str) -> ScrapedOffer | None:
    text = _norm(html_text)
    offers: list[dict] = []
    for lab in re.findall(r'aria-label="([^"]{80,1500})"', text):
        if "precio total de ida y vuelta" not in lab or "dólares" not in lab:
            continue
        lab = html.unescape(lab)
        pm = re.search(r"A partir de ([\d\.]+)\s*dólares estadounidenses", lab)
        if not pm:
            continue
        price = int(pm.group(1).replace(".", ""))
        dm = re.search(r"Duración total: ([0-9]+)\s*h\s*([0-9]+)\s*min", lab)
        dur = f"{dm.group(1)}h{dm.group(2).zfill(2)}" if dm else "sin dato"
        sm = re.search(r"Vuelo con (\d+) escala", lab)
        stops = int(sm.group(1)) if sm else 0
        am = re.search(r"escalas de ([^.]+)\.", lab)
        airline = am.group(1).strip() if am else "sin dato"
        lay = re.findall(
            r"escala \(\d+ de \d+\) es una escala de [^.]+ en ([^.]+?) de ", lab
        )
        offers.append(
            dict(price=price, dur=dur, stops=stops, airline=airline, lay=lay, raw=lab)
        )
    if not offers:
        return None
    best = min(offers, key=lambda x: x["price"])
    ida = _fmt_leg(best["dur"], best["airline"], best["lay"])
    vuelta = "sin dato"
    esc_vuelta = "sin dato"
    ret_offers = []
    for lab in re.findall(r'aria-label="([^"]{80,1500})"', text):
        if "regreso" in lab.lower() and "dólares" in lab and "precio total" in lab:
            lab = html.unescape(lab)
            pm = re.search(r"A partir de ([\d\.]+)\s*dólares", lab)
            dm = re.search(r"Duración total: ([0-9]+)\s*h\s*([0-9]+)\s*min", lab)
            sm = re.search(r"Vuelo con (\d+) escala", lab)
            am = re.search(r"escalas de ([^.]+)\.", lab)
            if pm and dm:
                lay = re.findall(r"escala[^.]* en ([^.]+?) de ", lab)
                ret_offers.append(
                    dict(
                        price=int(pm.group(1).replace(".", "")),
                        dur=f"{dm.group(1)}h{dm.group(2).zfill(2)}",
                        stops=int(sm.group(1)) if sm else 0,
                        airline=am.group(1).strip() if am else best["airline"],
                        lay=lay,
                    )
                )
    if ret_offers:
        ret = min(ret_offers, key=lambda x: x["price"])
        vuelta = _fmt_leg(ret["dur"], ret["airline"], ret["lay"])
        esc_vuelta = ret["stops"]
        total_price = ret["price"]
    else:
        total_price = best["price"]
        vuelta = f"sin dato (solo ida visible; precio RT {total_price} USD en Google)"
        esc_vuelta = "sin dato"

    total = "sin dato"
    if vuelta and "h" in best["dur"] and "h" in str(vuelta):
        def mins(s: str) -> int:
            m = re.match(r"(\d+)h(\d+)", s)
            return int(m.group(1)) * 60 + int(m.group(2)) if m else 0

        if esc_vuelta != "sin dato":
            tot_m = mins(best["dur"]) + mins(vuelta.split()[0])
            total = f"{tot_m // 60}h{tot_m % 60:02d}"

    return ScrapedOffer(
        precio=total_price if ret_offers else best["price"],
        ida=ida,
        vuelta=vuelta if isinstance(vuelta, str) else "sin dato",
        esc_ida=best["stops"],
        esc_vuelta=esc_vuelta if isinstance(esc_vuelta, int) else 0,
        total_horas=total,
        notas="" if ret_offers else "vuelta: abrir link y elegir regreso en Google",
    )


def _parse_kayak(html_text: str) -> ScrapedOffer | None:
    text = _norm(html_text)
    prices = [int(x.replace(",", "")) for x in re.findall(r"US\$[\s]*([\d,]+)", text)]
    if not prices:
        prices = [int(x) for x in re.findall(r'"price"\s*:\s*(\d{3,5})', text)]
    if not prices:
        return None
    price = min(prices)
    return ScrapedOffer(
        precio=price,
        ida="sin dato",
        vuelta="sin dato",
        esc_ida=0,
        esc_vuelta=0,
        total_horas="sin dato",
        notas="Kayak: precio mínimo en HTML; completar tramos manualmente o re-scrape",
    )


def fetch_html(url: str, budget_ms: int = 25000) -> str:
    proc = subprocess.run(
        [
            "google-chrome",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--virtual-time-budget={budget_ms}",
            "--dump-dom",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=budget_ms // 1000 + 60,
    )
    if proc.returncode != 0 and not proc.stdout:
        raise RuntimeError(proc.stderr[:500] or "chrome failed")
    return proc.stdout


def scrape_url(url: str) -> ScrapedOffer:
    html_text = fetch_html(url)
    if "google.com/travel/flights" in url:
        offer = _parse_google(html_text)
    elif "kayak" in url:
        offer = _parse_kayak(html_text)
    else:
        raise ValueError(f"Unsupported URL: {url}")
    if not offer:
        raise RuntimeError("No offers parsed from page")
    return offer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    args = ap.parse_args()
    offer = scrape_url(args.url)
    print(
        {
            "precio": offer.precio,
            "ida": offer.ida,
            "vuelta": offer.vuelta,
            "esc_ida": offer.esc_ida,
            "esc_vuelta": offer.esc_vuelta,
            "total_horas": offer.total_horas,
            "notas": offer.notas,
        }
    )


if __name__ == "__main__":
    main()
