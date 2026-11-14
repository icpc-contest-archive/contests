"""Review mode: the units a reader can confirm, correct or add to (DEFINITIONS.md, Review mode).

A unit is one claim that can be right or wrong on its own. build_site.py wraps each unit where
its object's own page states it; the wrapper carries the unit's key and the catalogue's value,
and does nothing until the reader switches review mode on (tools/site_assets/review.js).

A page is reviewed as it reads. Some facts are stored once and shown from both ends: a contest's
previous edition is the other contest's `next`, "fed by" is the other contests' `parent`, a
problem's appearances are the sets' problem lists and the contests' letters. Each end is a unit
of the page that shows it (`previous`, `fed_by`, `views`, `appearance`), and reading a review
means translating those to where the fact is stored.

    U(unit, inner, value)      a unit that is on the page
    row(unit, label)           a facts row for a unit with no value: shown in review mode only
    line(unit, text, value)    a line for a unit the page does not state: shown in review mode only
    slot(unit, text)           the place where one more can be added: shown in review mode only

UNITS is the single list of what can be reviewed. It is written to assets/units.js for the
script, and build_site.py refuses a unit key that is not in it.
"""
from __future__ import annotations

import html
import json
from collections import Counter

REPO = "icpc-contest-archive/reviews"  # where a review is submitted: the issue form review.yml of this repository
OPEN = False  # True once that repository and its form exist. Until then review mode is reached only by a link ending in ?review=1
STATS: Counter = Counter()  # kind -> units written, for the build's summary

# kind -> unit key -> (label, many, hint).  `many`: the object can have several, so "add" means one more.
UNITS: dict[str, dict[str, tuple[str, bool, str]]] = {
    "contest": {
        "series": ("Series", False, "the id of the series it belongs to"),
        "ran": ("Took place", False, "what is wrong: it did not take place, or it has not run yet"),
        "name": ("Name", False, "the contest's full name"),
        "date": ("Date", False, "the contest day, YYYY-MM-DD"),
        "season": ("Season", False, "the year the season ends, e.g. 2027"),
        "site": ("Site", True, "the city or institution it was held at, or: online"),
        "site_date": ("Date at this site", False, "the day this site held it, YYYY-MM-DD"),
        "advances": ("Advances to", False, "contest id, e.g. wf-2018, or: nothing"),
        "fed_by": ("Fed by", False, "ids of the contests whose teams advance to this one"),
        "previous": ("Previous edition", False, "contest id, e.g. nwerc-2019"),
        "next": ("Next edition", False, "contest id, e.g. nwerc-2021"),
        "subset_of": ("Subset of", False, "id of the larger contest this is one region's view of"),
        "views": ("Regional views", False, "ids of the contests that are one region's view of this one"),
        "cms_id": ("ICPC CMS id", False, "the number in the ICPC CMS, or: none"),
        "source": ("Source", True, ""),
        "division": ("Division", False, "the part of the contest this source covers, e.g. Division 1"),
        "none": ("There never was one", False, "say what there never was, and how you know"),
        "problemset": ("Problem set", False, "the id of the problem set it sat"),
        "letter": ("Letter", False, "the problem's letter in this contest, e.g. B"),
    },
    "series": {
        "name": ("Name", False, "the series' full name"),
        "aliases": ("Other name", True, "another name or id this series goes by"),
        "region": ("Region", False, "the ICPC region"),
        "level": ("Level", False, "world-finals, championship, regional or subregional"),
        "rotating_host": ("Host rotates", False, "yes or no"),
        "lineage": ("Lineage", True, "continues, split from or merged into: which series, which year"),
        "contest": ("Edition", True, "a contest of this series that is missing: the year and what you know of it"),
    },
    "problemset": {
        "contest": ("Used by", True, "id of a contest that sat this set"),
        "count": ("Number of problems", False, "how many problems the set has"),
        "complete": ("Problem list", False, "complete, partial or none"),
        "name": ("Name", False, "a name for the set"),
        "member": ("Problem of this set", True, "a missing problem: its letter and name"),
    },
    "problem": {
        "name": ("Name", False, "the problem's title"),
        "judge_link": ("Online-judge link", True, "the problem's address on an online judge"),
        "appearance": ("Appeared as", True, "a contest that used this problem, and its letter there"),
    },
    "location": {
        "name": ("Name", False, "the place's name"),
        "aliases": ("Other name", True, "another way the name is written"),
        "type": ("Kind", False, "country, region, city or institution"),
        "parent": ("Lies in", False, "the city, region or country it lies in"),
    },
    "judge": {
        "name": ("Name", False, "the judge's name"),
        "url": ("Address", False, "the judge's address"),
        "status": ("Open or closed", False, "active, or: closed YYYY-MM-DD"),
        "offers": ("Offers", False, "statements, submissions, both or neither"),
    },
    "source": {
        "moved": ("Address has moved", False, "the address it has moved to"),
    },
}

# Corrections every object takes, whatever its kind.
ANY = {
    "duplicate": ("Duplicate", False, "the id or address of the page this duplicates"),
    "remark": ("Remark", False, "what you want to tell us"),
}

_kind: list[str] = [""]  # the kind of the page being built, set by at()


def at(kind: str, oid: str) -> str:
    """The attribute that names a page's object; goes on its <h1>. Sets the kind for U()."""
    assert kind in UNITS, kind
    _kind[0] = kind
    return f' data-at="{html.escape(kind + "/" + str(oid), quote=True)}"'


def _attrs(unit: str, v, of, label=None) -> str:
    assert unit in UNITS[_kind[0]], f"{unit!r} is not a unit of {_kind[0]!r}"
    STATS[_kind[0]] += 1
    a = f' data-u="{unit}" data-v="{html.escape("" if v is None else str(v), quote=True)}"'
    if of is not None:
        a += f' data-of="{html.escape(str(of), quote=True)}"'
    if label:
        a += f' data-l="{html.escape(str(label), quote=True)}"'
    return a


def U(unit: str, inner: str, v, of=None, label=None) -> str:
    """A unit that is on the page: `inner` as shown, `v` the catalogue's value (compared when a
    review is read, so it is the stored value, not the display text). `of` says which one when
    the object has several; `label` names that one for the reviewer when `of` is an id."""
    return f'<span class="u"{_attrs(unit, v, of, label)}>{inner}</span>'


def row(unit: str, label: str, text: str = "not recorded") -> str:
    """A facts row for a unit with no value. Hidden unless review mode is on."""
    return f'<dt class="rvo">{label}</dt><dd class="rvo"><span class="u muted"{_attrs(unit, "", None)}>{text}</span></dd>'


def line(unit: str, text: str, v="", of=None) -> str:
    """A line of its own for a unit the page does not state. Hidden unless review mode is on."""
    return f'<p class="rvo"><span class="u"{_attrs(unit, v, of)}>{text}</span></p>'


def slot(unit: str, text: str, of=None, tag: str = "span") -> str:
    """Where one more of a `many` unit can be added. Hidden unless review mode is on."""
    return f'<{tag} class="rvo"><span class="u ua"{_attrs(unit, "", of)}>{text}</span></{tag}>'


def units_js() -> str:
    """assets/units.js: the unit list for the script."""
    out = {k: {u: {"l": l, "m": m, "h": h} for u, (l, m, h) in d.items()} for k, d in UNITS.items()}
    out["*"] = {u: {"l": l, "m": m, "h": h} for u, (l, m, h) in ANY.items()}
    return ("window.RV_UNITS=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n"
            + "window.RV_REPO=" + json.dumps(REPO) + ";\n")


def header_link(rel: str) -> str:
    """The Review button of the page header; nothing until review mode is open to everyone."""
    if not OPEN:
        return ""
    return f'<a id="rv" href="{rel}about.html#contribute" title="Review mode: confirm, correct and add to what the archive says">Review</a>'


def about_text(issues: str) -> str:
    """The Contribute paragraph of the About page."""
    lead = "If you ran, judged or took part in a contest, you may be the only person who still has its scoreboard, its problem set or its dates.\n"
    if not OPEN:
        return (f'<p class="intro">{lead}To add a source, confirm that what we show is right, or correct something, '
                f'<a class="ext" href="{issues}/issues/new">open an issue</a> and say which contest\n'
                "(its id, such as <code>nwerc-2020</code>) and what you know — a link, a file, a date, a place. "
                "Every claim is checked and recorded with where it came from.\n"
                'The <a href="wanted.html">most wanted</a> list shows what is missing.</p>')
    return (f'<p class="intro">{lead}<b>Review</b> in the header switches on review mode. Every fact on a page then has a ✓ to confirm it and a ✎ to '
            "correct it, and every list a + to add what is missing: a source, a file, a date, a place.\n"
            "Your marks stay in your browser while you go from page to page. <b>Submit review</b> then copies them all, and you paste them into one form "
            "on GitHub, which needs a GitHub account.\nEvery claim is checked and recorded with the GitHub name of who made it. "
            'The <a href="wanted.html">most wanted</a> list shows what is missing.</p>')
