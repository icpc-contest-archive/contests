"""The Live Archive's problem numbers (icpcarchive.ecs.baylor.edu; gone, linked through Wayback snapshots,
ruled 2026-11-22).

A Live Archive problem has a number (what everyone cites, `id:` of a `judge: livearchive` link) and an
internal page number (`...page=show_problem&problem=<internal>`). They are NOT a fixed offset apart:
"number - 1999" holds for about 57 % of the problems and opens another problem for the rest. The map from
one to the other, read off the Live Archive's own category pages and problem pages, is
data/livearchive-problems.json (tools/build_livearchive_map.py). Every tool that writes or checks a Live
Archive link goes through here.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "icpcarchive.ecs.baylor.edu"
PAGE_URL = f"https://{HOST}/index.php?option=com_onlinejudge&Itemid=8&page=show_problem&problem={{internal}}"
INTERNAL = re.compile(r"[?&]problem=(\d+)")
STATEMENT = re.compile(r"/external/\d+/p?(\d+)\.(?:pdf|html)$")


@lru_cache(maxsize=1)
def problems() -> dict[str, dict]:
    p = ROOT / "data" / "livearchive-problems.json"
    return json.loads(p.read_text())["problems"] if p.exists() else {}


@lru_cache(maxsize=1)
def by_internal() -> dict[int, str]:
    return {i: num for num, e in problems().items() for i in e["internal"]}


def internal(number) -> int | None:
    """The internal page number of Live Archive problem `number`, or None when it is not known."""
    e = problems().get(str(number))
    return e["internal"][0] if e and len(e["internal"]) == 1 else None


def page_url(number) -> str | None:
    """The problem page's address on the Live Archive, or None when its internal number is not known."""
    i = internal(number)
    return PAGE_URL.format(internal=i) if i is not None else None


def check(link: dict) -> str | None:
    """Why a `judge: livearchive` link opens the wrong problem, or None when nothing says it does."""
    number, url = str(link.get("id") or ""), link.get("url") or ""
    m = STATEMENT.search(url)
    if m:
        return None if m.group(1) == number else f"statement file of problem {m.group(1)}, not {number}"
    m = INTERNAL.search(url)
    if not m:
        return None
    n = int(m.group(1))
    e = problems().get(number)
    if e and n not in e["internal"]:
        return f"page {n} is not problem {number} (its page is {', '.join(map(str, e['internal']))})"
    other = by_internal().get(n)
    if other and other != number:
        return f"page {n} is problem {other}, not {number}"
    return None
