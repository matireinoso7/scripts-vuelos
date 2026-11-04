#!/usr/bin/env python3
"""Step 4: build sheet row values and write_range payloads."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

from scrape_flight_link import ScrapedOffer

from pipeline.step1_read import year_from_link
from pipeline.step_c_sheet import FIELDS, emit_jsonl, row_values, write_range_payload


def save_payload(
    row_num: int,
    sheet_row: dict[str, str],
    offer: ScrapedOffer,
    link: str,
    *,
    actualizado: str,
) -> dict[str, Any]:
    year = year_from_link(link)
    values = row_values(sheet_row, offer, link, actualizado=actualizado, trip_year=year)
    return write_range_payload(row_num, values)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(emit_jsonl(payload))


def update_csv_row(csv_path: Path, row_num: int, values: list[Any]) -> None:
    text = csv_path.read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return
    fieldnames = list(FIELDS)
    for r in rows:
        for fn in fieldnames:
            r.setdefault(fn, "")
    idx = row_num - 2
    if idx < 0 or idx >= len(rows):
        return
    for i, name in enumerate(fieldnames):
        if i < len(values):
            rows[idx][name] = str(values[i])
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    csv_path.write_text(out.getvalue(), encoding="utf-8")


def offer_to_dict(offer: ScrapedOffer) -> dict:
    return {
        "precio": offer.precio,
        "ida": offer.ida,
        "vuelta": offer.vuelta,
        "esc_ida": offer.esc_ida,
        "esc_vuelta": offer.esc_vuelta,
        "total_horas": offer.total_horas,
        "notas": offer.notas,
    }


def offer_from_dict(d: dict) -> ScrapedOffer:
    return ScrapedOffer(
        precio=int(d["precio"]),
        ida=d["ida"],
        vuelta=d["vuelta"],
        esc_ida=int(d["esc_ida"]),
        esc_vuelta=int(d["esc_vuelta"]),
        total_horas=d["total_horas"],
        notas=d.get("notas", ""),
    )
