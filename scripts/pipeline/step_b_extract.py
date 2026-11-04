#!/usr/bin/env python3
"""Legacy step B — use step2_search.search_offer."""
from __future__ import annotations

from flight_policy import offer_complete
from pipeline.step2_search import search_offer as extract_from_link

__all__ = ["extract_from_link", "offer_complete"]
