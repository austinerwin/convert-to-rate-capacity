#!/usr/bin/env python3
"""
limit_parser.py
~~~~~~~~~~~~~~~
Convert friendly quota strings like
    "20 messages per week"
    "11 messages every half a week"
    "1 message every 3 hours"
into token-bucket parameters:

    {
        "capacity":   <int | None>,   # None ⇒ unlimited
        "rate_per_sec": <float>,      # tokens added per second
    }

Usage (CLI):
    $ python limit_parser.py "20 messages per week"
    capacity=20 rate_per_sec=3.30688e-05
"""

from __future__ import annotations

import re
import sys
from typing import Dict, Optional

# --------------------------------------------------------------------------- #
#  Constants
# --------------------------------------------------------------------------- #

UNIT_SECONDS: dict[str, float] = {
    # seconds
    "second": 1, "sec": 1, "secs": 1, "s": 1, "seconds": 1,
    # minutes
    "minute": 60, "min": 60, "mins": 60, "m": 60, "minutes": 60,
    # hours
    "hour": 3600, "hr": 3600, "hrs": 3600, "h": 3600, "hours": 3600,
    # days
    "day": 86400, "d": 86400, "days": 86400,
    # weeks
    "week": 604800, "wk": 604800, "w": 604800, "weeks": 604800,
    # months / years (rough averages)
    "month": 2_592_000, "mo": 2_592_000, "months": 2_592_000,
    "year": 31_536_000, "yr": 31_536_000, "y": 31_536_000, "years": 31_536_000,
}

FRACTIONS: dict[str, float] = {
    "half": 0.5,
    "quarter": 0.25,
    "third": 1 / 3,
    "¾": 0.75,
    "½": 0.5,
    "¼": 0.25,
}

# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #


def human_limit_to_bucket(text: str) -> Dict[str, Optional[float]]:
    """
    Convert a human-readable quota string into {capacity, rate_per_sec}.
    Raises ValueError on malformed input.
    """
    s = text.strip().lower()

    # Unlimited plans
    if "unlimited" in s:
        return {"capacity": None, "rate_per_sec": 0.0}

    # ------------------------------------------------------------------- #
    #  1) Extract message count  (capacity)
    # ------------------------------------------------------------------- #
    msg_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:msg|msgs|messages?)?\s*(?:per|\/|every)",
        s,
    )
    if not msg_match:
        raise ValueError(f"Could not find message count in: '{text}'")

    capacity = int(float(msg_match.group(1)))

    # ------------------------------------------------------------------- #
    #  2) Isolate the period phrase (everything after 'per' / 'every' / '/')
    # ------------------------------------------------------------------- #
    period_match = re.search(r"(?:per|\/|every)\s+(.+)", s)
    if not period_match:
        raise ValueError(f"Could not find period in: '{text}'")
    period_phrase = period_match.group(1).strip()

    # ------------------------------------------------------------------- #
    #  3) Convert period phrase → seconds
    # ------------------------------------------------------------------- #
    seconds = _parse_duration_seconds(period_phrase)
    if seconds == 0:
        raise ValueError("Duration cannot be zero seconds")

    return {
        "capacity": capacity,
        "rate_per_sec": capacity / seconds,
    }


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #


def _parse_duration_seconds(phrase: str) -> float:
    """
    Convert phrases like 'week', 'half a week', '0.5 weeks', '3 hours'
    into seconds. Uses rough averages for months/years.
    """
    # Normalize common fraction words / symbols to decimals
    norm = phrase
    for word, val in FRACTIONS.items():
        norm = re.sub(rf"\b{word}\b", str(val), norm)

    # Remove the optional article 'a' (e.g., 'half a week')
    norm = re.sub(r"\ba\s+", "", norm)

    # Regex: optional numeric prefix, required time unit
    unit_re = "|".join(UNIT_SECONDS.keys())
    m = re.search(
        rf"(?:(\d+(?:\.\d+)?))?\s*({unit_re})",
        norm,
    )
    if not m:
        raise ValueError(f"Could not parse duration: '{phrase}'")

    qty_str, unit = m.groups()
    qty = float(qty_str) if qty_str else 1.0
    seconds = qty * UNIT_SECONDS[unit]
    return seconds


# --------------------------------------------------------------------------- #
#  CLI entry-point
# --------------------------------------------------------------------------- #

def _cli() -> None:
    if len(sys.argv) < 2:
        print("Usage: python limit_parser.py \"<quota string>\"")
        sys.exit(1)

    inp = " ".join(sys.argv[1:])
    result = human_limit_to_bucket(inp)
    cap = result["capacity"] if result["capacity"] is not None else "unlimited"
    print(f"capacity={cap} rate_per_sec={result['rate_per_sec']}")


if __name__ == "__main__":
    _cli()
