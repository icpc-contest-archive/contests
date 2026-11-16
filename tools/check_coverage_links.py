#!/usr/bin/env python3
"""Check that every coverage number equals the size of the list behind its link.

  python3 tools/check_coverage_links.py [--site site]

Reads the built contest list (contest/index.html) the way the page's own filter does: a row passes
a filter when the cell of that column has the value (data-vs: any of its values; data-v; else its
text). Then follows every counted link (a bar segment, a label, a number: anything with data-n) on
the pages that carry them and compares its number with the rows its filters select. Exit 1 on any
difference.
"""
import argparse, html, re, sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
TAG = re.compile(r"<[^>]+>")


def load_rows(index: Path):
    t = index.read_text()
    head = t[t.index("<thead>"):t.index("</thead>")]
    keys = [(re.search(r'data-k="([^"]*)"', th) or [None, None])[1] for th in re.findall(r"<th\b[^>]*>", head)]
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", t[t.index("<tbody>"):t.index("</tbody>")], re.S):
        cells = re.findall(r"<td\b([^>]*)>(.*?)</td>", tr, re.S)
        row = {}
        for k, (attrs, inner) in zip(keys, cells):
            if not k:
                continue
            vs = re.search(r'data-vs="([^"]*)"', attrs)
            v = re.search(r'data-v="([^"]*)"', attrs)
            if vs:
                row[k] = {x for x in html.unescape(vs.group(1)).split("|") if x}
            else:
                row[k] = {html.unescape(v.group(1) if v else TAG.sub("", inner)).strip()}
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=str(ROOT / "site"))
    a = ap.parse_args()
    site = Path(a.site)
    rows = load_rows(site / "contest" / "index.html")
    pages = [site / "coverage.html", site / "wanted.html", site / "index.html", site / "series" / "index.html", site / "season" / "index.html",
             site / "location" / "index.html"]
    for sub, k in (("series", 12), ("season", 12), ("location", 40)):   # the largest pages of each kind, and a spread of the rest
        files = sorted((site / sub).glob("*.html"), key=lambda f: -f.stat().st_size)
        pages += [f for f in files[:k] + files[k::max(1, len(files) // k)] if f.name != "index.html"]
    pages = list(dict.fromkeys(pages))
    bad = checked = 0
    for p in pages:
        t = p.read_text()
        # every counted link carries its number (data-n) and the filters that select what it counts
        for m in re.finditer(r'<a\b[^>]*?\bdata-n="(\d+)"[^>]*?\bhref="([^"]*#f:[^"]*)"', t):
            shown, href = m.group(1), html.unescape(m.group(2))
            f = dict(kv.split("=", 1) for kv in href.split("#f:", 1)[1].split("&") if kv)
            f = {k: unquote(v) for k, v in f.items()}
            n = sum(1 for r in rows if all(v in r.get(k, ()) for k, v in f.items()))
            checked += 1
            if n != int(shown.replace(",", "")):
                bad += 1
                if bad <= 20:
                    print(f"{p.relative_to(site)}: shows {shown}, the list has {n}: {f}")
    print(f"{checked} linked numbers checked on {len(pages)} pages, {bad} differ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
