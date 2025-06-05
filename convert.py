#!/usr/bin/env python3
"""
convert.py  —  friendly-quota → {capacity, rate_per_sec}
Usage:
    $ python3 convert.py "1000 messages per month"
    capacity=1000  rate_per_sec=0.00038580246913580245
"""

import re
import sys
from typing import Optional, Dict

UNIT_SECONDS: Dict[str, int] = {
    # seconds
    "seconds": 1, "second": 1, "secs": 1, "sec": 1, "s": 1,
    # minutes
    "minutes": 60, "minute": 60, "mins": 60, "min": 60, "m": 60,
    # hours
    "hours": 3600, "hour": 3600, "hrs": 3600, "hr": 3600, "h": 3600,
    # days
    "days": 86_400, "day": 86_400, "d": 86_400,
    # weeks
    "weeks": 604_800, "week": 604_800, "wk": 604_800, "w": 604_800,
    # months (~30 d)
    "months": 2_592_000, "month": 2_592_000, "mo": 2_592_000,
    # years (~365 d)
    "years": 31_536_000, "year": 31_536_000, "yr": 31_536_000, "y": 31_536_000,
}

FRACTIONS = {
    "half": 0.5,
    "quarter": 0.25,
    "third": 1 / 3,
    "¾": 0.75,
    "½": 0.5,
    "¼": 0.25,
}

# ---- helpers ----------------------------------------------------------- #

def _parse_duration_seconds(phrase: str) -> float:
    """Turn 'half a week', '3 hours', '0.5 months' → seconds."""
    text = phrase.lower()
    for word, val in FRACTIONS.items():
        text = re.sub(rf"\b{word}\b", str(val), text)
    text = re.sub(r"\ba\s+", "", text)        # drop the 'a' in 'half a week'

    # longest-first prevents 'm' matching inside 'month'
    unit_re = "|".join(sorted(UNIT_SECONDS, key=len, reverse=True))
    m = re.search(rf"\b(?:(\d+(?:\.\d+)?))?\s*({unit_re})\b", text)
    if not m:
        raise ValueError(f"Could not parse duration: '{phrase}'")
    qty_str, unit = m.groups()
    qty = float(qty_str) if qty_str else 1.0
    return qty * UNIT_SECONDS[unit]


def human_limit_to_bucket(expr: str) -> Dict[str, Optional[float]]:
    """Main entry – '20 msgs / wk' → {'capacity': 20, 'rate_per_sec': …}"""
    s = expr.strip().lower()

    if "unlimited" in s:
        return {"capacity": None, "rate_per_sec": 0.0}

    # capacity
    m_count = re.search(r"(\d+(?:\.\d+)?)\s*(?:msg|msgs|messages?)?\s*(?:per|\/|every)", s)
    if not m_count:
        raise ValueError(f"Could not find message count in: '{expr}'")
    capacity = int(float(m_count.group(1)))

    # period
    m_period = re.search(r"(?:per|\/|every)\s+(.+)", s)
    if not m_period:
        raise ValueError(f"Could not find period in: '{expr}'")
    seconds = _parse_duration_seconds(m_period.group(1).strip())
    if seconds == 0:
        raise ValueError("Duration cannot be zero")

    return {"capacity": capacity, "rate_per_sec": capacity / seconds}


# ---- CLI --------------------------------------------------------------- #

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 convert.py \"<quota string>\"")
        sys.exit(1)

    inp = " ".join(sys.argv[1:])
    result = human_limit_to_bucket(inp)
    rate_str = f"{rate:.17f}".rstrip("0").rstrip(".")
    print(f"capacity={cap}  rate_per_sec={rate_str}")
