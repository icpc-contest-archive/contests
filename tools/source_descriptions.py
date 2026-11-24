"""Source descriptions: what a reader of our copy wrote about a source (data/source-descriptions/README.md).
The data is data/source-descriptions/<series>/<contest>.yaml, written by
tools/describe_apply.py; this module loads it and renders it for the source page.

    load()                      {(contest id, norm_key(address)): entry}
    block(url, cits, rel, ...)  the "What it contains" section of a source page, "" when there is none
    ABOUT                       the paragraph of about.html that says how descriptions are made
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import yaml

from resources import norm_key

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "data" / "source-descriptions"
FIELDS = ("url", "read", "rubric", "copy", "title", "title_en", "language", "contest_date", "teams", "problems", "times", "tries",
          "pages", "description")
LANG_NAMES = {"en": "English", "ru": "Russian", "zh": "Chinese", "es": "Spanish", "pt": "Portuguese", "fr": "French", "de": "German",
              "ja": "Japanese", "ko": "Korean", "pl": "Polish", "uk": "Ukrainian", "it": "Italian", "nl": "Dutch", "sv": "Swedish",
              "fa": "Persian", "ar": "Arabic", "tr": "Turkish", "vi": "Vietnamese", "id": "Indonesian", "th": "Thai", "ro": "Romanian",
              "hu": "Hungarian", "cs": "Czech", "sk": "Slovak", "bg": "Bulgarian", "sr": "Serbian", "hr": "Croatian", "el": "Greek",
              "he": "Hebrew", "ka": "Georgian", "hy": "Armenian", "kk": "Kazakh", "uz": "Uzbek", "ky": "Kyrgyz", "az": "Azerbaijani",
              "be": "Belarusian", "lt": "Lithuanian", "lv": "Latvian", "et": "Estonian", "fi": "Finnish", "da": "Danish", "no": "Norwegian",
              "nb": "Norwegian", "is": "Icelandic", "bn": "Bengali", "hi": "Hindi", "mn": "Mongolian", "ca": "Catalan", "sl": "Slovenian",
              "ms": "Malay", "tl": "Filipino", "mk": "Macedonian", "la": "Latin"}
ABOUT = """<p class="intro" id="descriptions">A source whose copy we hold can have a <b>description</b>: what the document is and what it contains, with the
few facts the document states about itself (its title, its language, the contest date it gives, how many teams and problems it shows). Descriptions are written by an
automated reader (a language model) that was given our copy and nothing else, and a sample of them is checked against the copies. They describe the copy, not the
contest: where a document is wrong, so is its description. A description that misstates its document is an error of ours; tell us (see Contribute below).</p>"""

_cache: dict | None = None


def load(fresh: bool = False) -> dict:
    global _cache
    if _cache is None or fresh:
        _cache = {}
        for f in sorted(DIR.glob("*/*.yaml")):
            doc = yaml.safe_load(f.read_text()) or {}
            for e in doc.get("sources") or []:
                _cache[(doc.get("contest") or f.stem, norm_key(e["url"]))] = e
    return _cache


def paragraphs(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", (text or "").strip()) if p.strip()]


def facts(e: dict) -> list[tuple[str, str]]:
    """The document facts of an entry as (label, html) rows."""
    esc = lambda s: html.escape(str(s), quote=True)  # noqa: E731
    fx = []
    if e.get("title"):
        fx.append(("title, as printed", esc(e["title"]) + (f' <span class="muted">({esc(e["title_en"])})</span>' if e.get("title_en") else "")))
    if e.get("language"):
        fx.append(("language", esc(", ".join(LANG_NAMES.get(x, x) for x in e["language"]))))
    if e.get("contest_date"):
        fx.append(("contest date, as stated", esc(e["contest_date"])))
    if e.get("teams"):
        fx.append(("teams listed", f'{e["teams"]:,}'))
    if e.get("problems"):
        fx.append(("problems", str(e["problems"])))
    if e.get("times") is not None or e.get("tries") is not None:
        got = [w for w, on in (("attempts", e.get("tries")), ("times", e.get("times"))) if on]
        fx.append(("per problem", " and ".join(got) if got else "solved or not, nothing more"))
    if e.get("pages"):
        fx.append(("pages", str(e["pages"])))
    return fx


def block(url: str, cits: list[dict], rel: str, contest_ref, help_link, site_copy: bool = True) -> str:
    """The description section of a source page. `cits` are the contests that cite the address
    (each a dict with `contest`). A document several contests cite is described once per copy
    that was read: the same copy read for two contests is shown once, under the first.
    `site_copy` says whether a crawled website is among the source's copies: a description read from
    a crawl is not shown on a source that holds none (the crawl was of another address, 2026-11-24)."""
    D = load()
    seen, es = set(), []
    for c in cits:
        e = D.get((c["contest"], norm_key(url)))
        if e and not site_copy and "/website/" in str(e.get("copy") or "") + "/":
            continue
        if e and e.get("description") and e.get("copy") not in seen:
            seen.add(e.get("copy"))
            es.append((c, e))
    if not es:
        return ""
    b = ['<h2 id="contains">What it contains</h2>']
    for c, e in es:
        if len(es) > 1:
            b.append(f'<h3>As read for {contest_ref(c["contest"], rel)}</h3>')
        b.append('<div class="descr">' + "".join(f'<p class="intro">{html.escape(p)}</p>' for p in paragraphs(e["description"])) + "</div>")
        fx = facts(e)
        if fx:
            b.append('<dl class="facts">' + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in fx) + "</dl>")
        b.append('<p class="note">Written by an automated reader from our copy. It says what the copy shows, and it can be wrong. '
                 f'{help_link("descriptions", rel, "how descriptions are made")}</p>')
    return "\n".join(b)
