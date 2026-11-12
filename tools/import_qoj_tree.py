#!/usr/bin/env python3
"""Apply the QOJ ICPC category tree (qoj.ac/category/2) as judge_page sources.

QOJ (the Universal Cup judge) keeps every ICPC contest it mirrors in one category tree:
World Finals, the continental championships and the regionals of all eight regions, each
contest titled like the original ("The 2024 ICPC Asia Hangzhou Regional Contest"). The tree
is public but sits behind a Cloudflare browser check, so it was read once from a logged-out
browser session (2026-11-12) and frozen in data/import/qoj-tree-<date>.txt as

    <token>: <year>[/<variant>]=<qoj contest id> ...

where <token> is the series the title names (see TOKENS / ASIA below; `SKIP-*` tokens are
online qualifiers and warm-ups, which are not catalogue contests).

What this tool does, deterministically (a second run changes nothing):
  - every (token, year) that resolves to a contest in the catalogue (or the non-mainline
    registry) gets a `judge_page` source `https://qoj.ac/contest/<id>` with `judge: qoj`,
    via catalogue.add_source; a division or onsite/online variant is named in the note;
  - the shared Latin America set ("The <year> ICPC Latin America Regional Contests") is
    attached to every Latin America series of tier `regional` that ran that year;
  - everything else goes to the report: titles with no contest in the catalogue (gaps),
    and the skipped online qualifiers / warm-ups.

QOJ contest pages and problem lists need a QOJ login, so only the contest-level page is
recorded here; per-problem links wait for a logged-in pass (reports/qoj-tree-<date>.md).
QOJ standings are replays (Universal Cup stages), never the original results — these
sources are judge pages only.

  python3 tools/import_qoj_tree.py [--dry-run] [--file data/import/qoj-tree-2026-11-12.txt]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import Dumper, add_source, dump_series, load_series  # noqa: E402

TOOL = "import_qoj_tree.py"
# title family -> catalogue series (identity unless listed)
TOKENS = {"amppz": "poland", "ctu-open": "ctuo", "gcpc": "germany", "east-siberian": "east-siberia",
          "west-siberian": "west-siberia", "nwrrc": "north-russia", "ecfinal": "aec"}
# "ICPC Asia <city> Regional": host city -> series
ASIA = {"aizu": "japan", "hakodate": "japan", "kyoto": "japan", "tokyo": "japan", "tsukuba": "japan",
        "kanazawa": "japan", "ehime": "japan", "fukuoka": "japan", "yokohama": "japan",
        "daejeon": "korea", "seoul": "korea",
        "taipei": "taiwan", "taipei-hsinchu": "taiwan", "taoyuan": "taiwan", "taichung": "taiwan",
        "hanoi": "vietnam", "da-nang": "vietnam", "can-tho": "vietnam", "ho-chi-minh-city": "vietnam",
        "bangkok": "thailand", "xi-an": "xian"}
VARIANT = {"d1": "Div. 1", "d2": "Div. 2", "online": "online round", "onsite": "onsite round"}
SKIP_WHY = {"SKIP-ec-online": "Asia East Continent online qualifier (not a catalogue contest)",
            "SKIP-taiwan-online": "Taiwan Online Programming Contest (qualifier, not a catalogue contest)",
            "SKIP-warmup": "EC-Final warm-up round"}
HELD = {"tehran-online": "Tehran online regional 2023 (a second, online edition next to tehran-2023) — which contest is it?"}


def parse(path: Path):
    rows, date = [], re.search(r"(\d{4}-\d{2}-\d{2})", path.name).group(1)
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        tok, rest = line.split(": ", 1)
        for item in rest.split():
            yv, qid = item.split("=")
            m = re.match(r"(\d{4})(?:/?([a-z0-9]+))?$", yv)
            rows.append((tok, int(m.group(1)), m.group(2), int(qid)))
    return rows, date


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--file", default=str(ROOT / "data" / "import" / "qoj-tree-2026-11-12.txt"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows, date = parse(Path(a.file))
    series = load_series()
    where: dict[str, tuple[str, dict]] = {}
    for sid, doc in series.items():
        for c in doc["contests"]:
            where[c["id"]] = (sid, c)
    nm_path = ROOT / "registry" / "non-mainline.yaml"
    nm_text = nm_path.read_text()
    nm_doc = yaml.safe_load(nm_text)
    for c in nm_doc.get("non_mainline_contests") or []:
        where.setdefault(c["id"], ("non-mainline", c))
    latam = [sid for sid, d in series.items() if d["series"].get("region") == "Latin America" and d["series"].get("tier") == "regional"]

    applied, already, gaps, skipped, held = [], [], [], [], []
    touched: set[str] = set()
    for tok, year, var, qid in sorted(rows, key=lambda r: (r[0], r[1], r[2] or "")):
        url = f"https://qoj.ac/contest/{qid}"
        if tok in SKIP_WHY:
            skipped.append((tok, year, var, url))
            continue
        if tok in HELD:
            held.append((tok, year, url))
            continue
        if tok == "latam":
            targets = [f"{s}-{year}" for s in latam]
            extra = "shared Latin America regional problem set"
        else:
            sid = ASIA.get(tok[5:], tok[5:]) if tok.startswith("asia:") else TOKENS.get(tok, tok)
            targets = [f"{sid}-{year}"]
            extra = VARIANT.get(var or "", "")
        hit = False
        for cid in targets:
            if cid not in where:
                continue
            hit = True
            sid, c = where[cid]
            if c.get("status") == "upcoming":
                held.append((tok, year, url + f" — {cid} is marked upcoming, but QOJ mirrors its set: it ran"))
                continue
            note = f"QOJ / Universal Cup (QOJ ICPC category tree {date}" + (f"; {extra}" if extra else "") + ")"
            _s, changed = add_source(c, url, "judge_page", judge="qoj", note=note)
            (applied if changed else already).append((cid, url, extra))
            if changed:
                touched.add(sid)
        if not hit:
            gaps.append((tok, year, var, url, targets))

    rep = [f"# QOJ ICPC category tree — import of {date}", "",
           f"Source: https://qoj.ac/category/2 (92 categories, {len(rows)} contests), read from a logged-out browser session on {date}; "
           f"frozen in `data/import/{Path(a.file).name}`; applied by `tools/{TOOL}`.", "",
           f"- judge_page sources added: **{len(applied)}** (already present: {len(already)}) on {len({c for c, *_ in applied + already})} contests",
           f"- titles with no contest in the catalogue: **{len(gaps)}**",
           f"- held for a ruling: {len(held)}", f"- skipped (qualifiers, warm-ups): {len(skipped)}", "",
           "QOJ contest pages and their problem lists redirect to a login that sits behind a human-verification step; only the category tree is "
           "public. Per-problem QOJ links therefore need a logged-in browser pass (the list of pages to read is every applied URL below).", "",
           "## Applied", ""]
    by_series = defaultdict(list)
    for cid, url, extra in applied + already:
        by_series[where[cid][0]].append(f"{cid} → {url}" + (f" ({extra})" if extra else ""))
    for sid in sorted(by_series):
        rep.append(f"- **{sid}** ({len(by_series[sid])}): " + "; ".join(sorted(by_series[sid])))
    rep += ["", "## Not in the catalogue (gaps)", "",
            "A QOJ mirror exists, but the catalogue has no contest with this id — a missing edition, a different id year, or a non-catalogue contest.", ""]
    rep += [f"- {tok} {year}{'/' + var if var else ''} → {url} (looked for {', '.join(t)})" for tok, year, var, url, t in gaps]
    rep += ["", "## Held for a ruling", ""] + [f"- {tok} {year}: {url}" + (f" — {HELD[tok]}" if tok in HELD else "") for tok, year, url in held]
    rep += ["", "## Skipped", ""] + [f"- {SKIP_WHY[tok]} {year}{var or ''}: {url}" for tok, year, var, url in skipped]
    report = ROOT / "reports" / f"qoj-tree-{date}.md"
    print(f"qoj tree: {len(rows)} contests -> {len(applied)} added, {len(already)} already there, {len(gaps)} gaps, {len(held)} held, {len(skipped)} skipped")
    if a.dry_run:
        print("\n".join(rep[-(len(gaps) + len(held) + len(skipped) + 8):]))
        return 0
    for sid in sorted(touched):
        if sid == "non-mainline":
            hdr = "".join(ln + "\n" for ln in nm_text.split("\n") if ln.startswith("#"))
            nm_path.write_text(hdr + yaml.dump(nm_doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
        else:
            dump_series(sid, series[sid], TOOL)
    report.write_text("\n".join(rep) + "\n")
    print(f"wrote {len(touched)} files and {report.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
