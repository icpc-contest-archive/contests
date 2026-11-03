#!/usr/bin/env python3
"""Give every problem its online-judge links, mined from the captured judge pages.

Input: the captures of each contest's judge pages (sources with role judge_page) in the
archive repo, laid out as <archive>/<series>/<contest>/judge-<judge>/<capture>/page.html
(+ manifest.json; bodies may be gzip-compressed). Per (contest, judge, url) the newest
live capture is used, else the newest Wayback one; when the preferred capture lists no
problems (Kattis "No data found", Baekjoon's "service in preparation" placeholder, a
Codeforces login page) the next older capture is tried.

Page formats (verified on the captures):
  kattis       open.kattis.com/problem-sources/<X>: rows linking /problems/<short>, title in
               the link -> url https://open.kattis.com/problems/<short>, id <short>.
               <x>.kattis.com/contests/<c>/problems: rows with the letter and a link
               /contests/<c>/problems/<short> -> url = that contest-page URL, id <short>;
               the open.kattis.com URL is added as a second link only when the same short
               name also appears on a problem-sources page of the set (offline we cannot
               tell whether the problem is on open Kattis).
  livearchive  category pages: links show_problem&problem=<internal>, text "<number> - <title>"
               -> url onlinejudge.org/...&page=show_problem&problem=<internal>, id <number>.
  baekjoon     category (detail) pages: rows <number> <letter> <a href=/problem/<n>>title</a>
               -> url https://www.acmicpc.net/problem/<n>, id n, as_of = the Wayback snapshot
               (the judge closed 2026-04-28). "Practice Session" sections are skipped;
               Division 1 / Division 2 sections are both the contest (letters from the first).
  codeforces   gym pages: rows /gym/<g>/problem/<L> + name -> id "<g>/<L>".

Matching (per set, pages of all member contests, kattis > livearchive > codeforces >
baekjoon so English titles come first): titles are normalised (NFKD, ASCII, casefold,
a leading "A - "/"A. " dropped, non-alphanumerics dropped) and matched to the set's rows
by name; the contest's letter map breaks ties and checks the match (a mismatch is
reported, the link still added — a Div-2 page letters the same problem differently). A
Baekjoon row whose title is a Korean translation matches through its letter alone when
the contest's letter map has that letter (reported separately).
  set has rows        -> add {judge, url, id} (dedupe by judge+url); a Kattis short name
                         fills short_name when the row has none; a page letter fills the
                         contest's letter map when the letter and the row are both unmapped
                         (`letters: unknown` is dropped once every member contest has a map).
                         Titles matching no row are reported, not created — unless the set
                         is `complete: false`, when they are appended (see below).
  set has no rows     -> rows are created from the page: id = p- + sha1(set|letter|name)[:8]
  (933 holdings-only)    (the pid rule of migrate_problemsets.py), letters into the contest's
                         map when the page gives them, else `letters: unknown`; `complete:
                         false` when the page lists fewer problems than `count` (or no count
                         is known).
  held back           -> a page listing MORE problems than the set's `count`, or whose
                         unmatched titles would push the row count past `count`, creates
                         nothing (links to matched rows are still added); same rule as
                         import_problem_uuids.py. Non-Latin (translated) titles are never
                         appended to a set that already has rows.
Shared sets (several contests) are updated once. Series files are not touched.

Resumable: what each capture yielded is frozen in data/import/judge-pages-<date>.json;
a rerun parses only captures not yet in that file (--reparse forces). Deterministic:
captures, sets and rows are processed in sorted order; a second run changes 0 files.

Usage (repo root):
  python3 tools/mine_judge_links.py --archive /path/to/archive [--dry-run] [--date 2026-11-02]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import Dumper, by_role, load_contests, load_judges, load_non_mainline, load_sets, set_id_of  # noqa: E402
from resources import norm_key  # noqa: E402

SET_DIR = ROOT / "problemsets"
SET_HEADER = "# Problem set (DEFINITIONS.md, Problems): holdings, member contests with letter maps, problems.\n"
HELD_KINDS = ("statement", "data", "solutions", "package")
TODAY = __import__("datetime").date.today().isoformat()
SET_KEYS = ("id", "name", "repo", "count", "complete", "letters", *HELD_KINDS, "counts",
            "contests", "problems", "provenance", "notes")
PROB_KEYS = ("id", "uuid", "aliases", "name", "short_name", "have", "status", "judges", "notes")
JUDGE_ORDER = {"kattis": 0, "livearchive": 1, "codeforces": 2, "baekjoon": 3}
LETTER = re.compile(r"^[A-Z][0-9]?$|^[0-9]{1,2}$")  # as schema/problemsets.schema.json
LA_PROBLEM = "https://onlinejudge.org/index.php?option=com_onlinejudge&Itemid=8&page=show_problem&problem={}"
BJ_PROBLEM = "https://www.acmicpc.net/problem/{}"
KATTIS_PROBLEM = "https://open.kattis.com/problems/{}"
CF_PROBLEM = "https://codeforces.com/gym/{}/problem/{}"
PRACTICE = re.compile(r"practice|연습|warm[- ]?up|dress rehearsal|test session|trial", re.I)
NON_LATIN = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏぀-ヿ一-鿿]")


# ---------------------------------------------------------------- problem sets (as in the sibling tools)
def pid(uuid: str | None, set_id: str, letter: str | None, name: str) -> str:
    """Permanent internal problem id (verbatim from migrate_problemsets.py)."""
    if uuid:
        return "p-" + hashlib.sha1(uuid.lower().encode()).hexdigest()[:8]
    h = hashlib.sha1(f"{set_id}|{letter or ''}|{name}".encode()).hexdigest()
    return "p-" + h[:8]


def order_problem(p: dict) -> dict:
    out = {k: p[k] for k in PROB_KEYS if k in p}
    out.update({k: v for k, v in p.items() if k not in out})
    return out


def dump_set(s: dict) -> str:
    doc = {k: s[k] for k in SET_KEYS if k in s}
    doc.update({k: v for k, v in s.items() if k not in doc and not k.startswith("_")})
    if "problems" in doc:
        doc["problems"] = [order_problem(p) for p in doc["problems"]]
    return SET_HEADER + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)


def set_entry(s: dict, cid: str) -> dict:
    e = next((e for e in s["contests"] if e["contest"] == cid), None)
    if e is None:
        e = {"contest": cid}
        s["contests"].append(e)
    return e


def norm_title(t: str) -> str:
    """casefold, diacritics off, a leading "A - "/"B. " dropped, only letters and digits kept
    (of any script: a Cyrillic or Korean title stays distinct instead of collapsing to "")."""
    t = unicodedata.normalize("NFKD", t or "").casefold()
    t = re.sub(r"^\s*[a-z][0-9]?\s*(?:-|\.|:|\))\s+", "", t)  # "A - Title", "B. Title"
    return "".join(ch for ch in t if ch.isalnum() and unicodedata.category(ch) != "Mn")


# ---------------------------------------------------------------- captures
def read_body(path: Path) -> str:
    b = path.read_bytes()
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return b.decode("utf-8", "replace")


def list_captures(archive: Path) -> dict[tuple[str, str, str], list[dict]]:
    """{(contest, judge, url): [manifest, ...] in preference order (live newest first, then
    Wayback newest first)}; each manifest gets `_dir` (relative to the archive)."""
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for m in sorted(archive.rglob("manifest.json")):
        o = json.loads(m.read_text())
        if not str(o.get("artifact", "")).startswith("judge-") or o.get("content_file") != "page.html":
            continue
        o["_dir"] = str(m.parent.relative_to(archive))
        groups[(o["contest"], o["artifact"][6:], o["url"])].append(o)
    for lst in groups.values():
        lst.sort(key=lambda o: (0 if o.get("source") == "live" else 1,
                                -int(re.sub(r"\D", "", (o.get("fetched") if o.get("source") == "live"
                                                        else o.get("wayback_timestamp")) or "0")[:14] or "0"),
                                o["_dir"]))
    return groups


class TableRows(HTMLParser):
    """Collects table rows under their nearest preceding h1–h3 heading.
    row = [cell], cell = {tag, text, links: [{href, text}]}. Rows and cells closed
    implicitly (Codeforces omits </tr>) are handled."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections: list[tuple[str | None, list]] = [(None, [])]
        self.row = None
        self.cell = None
        self.a = None
        self.h = None

    def _close_cell(self):
        if self.cell is not None and self.row is not None:
            self.cell["text"] = " ".join(self.cell["text"].split())
            self.row.append(self.cell)
        self.cell = None
        self.a = None

    def _close_row(self):
        self._close_cell()
        if self.row is not None:
            self.sections[-1][1].append(self.row)
        self.row = None

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3"):
            self.h = ""
        elif tag == "tr":
            self._close_row()
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self._close_cell()
            self.cell = {"tag": tag, "text": "", "links": []}
        elif tag == "a" and self.cell is not None:
            self.a = {"href": dict(attrs).get("href") or "", "text": ""}
            self.cell["links"].append(self.a)

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3") and self.h is not None:
            self.sections.append((" ".join(self.h.split()), []))
            self.h = None
        elif tag == "a" and self.a is not None:
            self.a["text"] = " ".join(self.a["text"].split())
            self.a = None
        elif tag in ("td", "th"):
            self._close_cell()
        elif tag in ("tr", "table"):
            self._close_row()

    def handle_data(self, d):
        if self.h is not None:
            self.h += d
        if self.a is not None:
            self.a["text"] += d
        if self.cell is not None:
            self.cell["text"] += d

    def close(self):
        super().close()
        self._close_row()


def letter_of(cell: dict | None) -> str | None:
    return cell["text"] if cell and LETTER.match(cell["text"]) else None


def parse_page(judge: str, url: str, text: str) -> tuple[list[dict], list[str]]:
    """-> ([{letter, id, name, url, short?, section?}] in page order, [rows skipped as not the
    contest's: Baekjoon practice problems lettered PA, PB, ...]); ([], []) when nothing parses."""
    p = TableRows()
    p.feed(text)
    p.close()
    out: list[dict] = []
    skipped: list[str] = []
    seen: set[str] = set()

    def add(item):
        if item["id"] not in seen:
            seen.add(item["id"])
            out.append(item)

    if judge == "kattis":
        contest = re.search(r"/contests/([^/]+)/problems", url)
        host = urlsplit(url).netloc
        for _, rows in p.sections:
            for row in rows:
                hit = None
                for cell in row:
                    for a in cell["links"]:
                        m = re.match(r"(?:https?://[^/]+)?/(?:contests/([^/]+)/)?problems/([A-Za-z0-9._-]+)$", a["href"])
                        if m and a["text"]:
                            hit = (m.group(1), m.group(2), a["text"])
                            break
                    if hit:
                        break
                if not hit:
                    continue
                c, short, name = hit
                if contest and c:
                    add({"letter": letter_of(row[0]), "id": short, "short": short, "name": name,
                         "url": f"https://{host}/contests/{c}/problems/{short}", "kind": "contest"})
                elif not contest and not c:
                    add({"letter": None, "id": short, "short": short, "name": name,
                         "url": KATTIS_PROBLEM.format(short), "kind": "sources"})
    elif judge == "livearchive":
        for _, rows in p.sections:
            for row in rows:
                for cell in row:
                    for a in cell["links"]:
                        m = re.search(r"show_problem.*?problem=(\d+)", a["href"])
                        mm = re.match(r"(\d+)\s*-\s*(.+)$", a["text"]) if m else None
                        if m and mm:
                            add({"letter": None, "id": mm.group(1), "name": mm.group(2).strip(),
                                 "url": LA_PROBLEM.format(m.group(1))})
    elif judge == "baekjoon":
        first_lettered = None
        for heading, rows in p.sections:
            if heading and PRACTICE.search(heading):
                continue
            for row in rows:
                for ci, cell in enumerate(row):
                    for a in cell["links"]:
                        m = re.fullmatch(r"(?:https?://[^/]+)?/problem/(\d+)", a["href"])
                        if m and a["text"]:
                            cell_text = row[ci - 1]["text"] if ci >= 1 else ""
                            letter = letter_of(row[ci - 1]) if ci >= 1 else None
                            if cell_text and not letter and re.fullmatch(r"P[A-Z]", cell_text):
                                skipped.append(f"{cell_text} {a['text']}")  # PA, PB: the practice problems
                                continue  # any other odd cell ("?") is just an unknown letter
                            if letter and first_lettered is None:
                                first_lettered = heading
                            if letter and heading != first_lettered:
                                letter = None  # Division 2 letters: another numbering of the same set
                            add({"letter": letter, "id": m.group(1), "name": a["text"],
                                 "url": BJ_PROBLEM.format(m.group(1)), "section": heading})
    elif judge == "codeforces":
        for _, rows in p.sections:
            for row in rows:
                key = name = None
                for cell in row:
                    for a in cell["links"]:
                        m = re.fullmatch(r"(?:https?://[^/]+)?/gym/(\d+)/problem/([A-Z][0-9]?)", a["href"])
                        if not m:
                            continue
                        if key is None:
                            key = (m.group(1), m.group(2))
                        elif a["text"] and a["text"] != key[1]:
                            name = a["text"]
                if key and name:
                    add({"letter": key[1], "id": f"{key[0]}/{key[1]}", "name": name,
                         "url": CF_PROBLEM.format(*key)})
    return out, skipped


def extract(groups, archive: Path, frozen: dict, reparse: bool, stats) -> None:
    """Fill frozen['pages'][key] = {contest, judge, url, capture, source, as_of, problems,
    tried: [...]} for every (contest, judge, url); parses only what is not frozen yet."""
    pages = frozen.setdefault("pages", {})
    for key, mans in sorted(groups.items()):
        k = "|".join(key)
        if k in pages and not reparse and pages[k].get("captures") == [m["_dir"] for m in mans]:
            continue
        rec = {"contest": key[0], "judge": key[1], "url": key[2], "captures": [m["_dir"] for m in mans],
               "capture": None, "source": None, "as_of": None, "problems": [], "skipped": [], "tried": []}
        for m in mans:
            path = archive / m["_dir"] / "page.html"
            try:
                probs, skipped = parse_page(key[1], key[2], read_body(path))
            except Exception as e:  # noqa: BLE001 — a broken body is a parse failure, reported
                probs, skipped = [], []
                rec["tried"].append(f"{m['_dir']}: {type(e).__name__}: {e}")
            if probs:
                rec.update(capture=m["_dir"], source=m.get("source"),
                           as_of=(m.get("wayback_timestamp") if m.get("source") == "wayback" else None),
                           problems=probs, skipped=skipped)
                break
            rec["tried"].append(f"{m['_dir']}: no problems")
        pages[k] = rec
        stats[f"{key[1]}: captures parsed"] += 1


# ---------------------------------------------------------------- apply
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--archive", default=str(ROOT.parent / "archive"), help="archive repo root")
    ap.add_argument("--date", default="2026-11-02")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reparse", action="store_true", help="ignore the frozen extraction, parse every capture again")
    ap.add_argument("--allow-translated-names", action="store_true",
                    help="also create rows whose only known title is a Korean/CJK translation (default: report them)")
    args = ap.parse_args()
    archive = Path(args.archive).resolve()
    if not archive.is_dir():
        print(f"archive root not found: {archive}", file=sys.stderr)
        return 2
    frozen_path = ROOT / "data" / "import" / f"judge-pages-{args.date}.json"
    frozen = json.loads(frozen_path.read_text()) if frozen_path.exists() else {}
    if args.reparse:  # parse every capture again, but keep the pages injected without a capture
        # (tools/apply_judge_candidates.py: capture "hunt:<brief>", captures [])
        frozen = {"pages": {k: v for k, v in (frozen.get("pages") or {}).items() if not v.get("captures")}}
    stats: Counter = Counter()
    report: dict[str, list[str]] = defaultdict(list)

    contests = load_contests()
    for c in load_non_mainline():  # registry contests have sets too (naipc, bergen, kth)
        c["_series"] = "non-mainline"
        contests.setdefault(c["id"], c)
    sets = load_sets()
    judges = load_judges()
    set_text = {sid: (SET_DIR / f"{sid}.yaml").read_text() for sid in sets}
    new_sets: list[str] = []          # sets opened from a judge page this run
    dirty_contests: set[str] = set()  # contests that got problems: {set: ...}

    # ---- 1. captures -> frozen extraction ----
    groups = list_captures(archive)
    extract(groups, archive, frozen, args.reparse, stats)
    frozen["archive_layout"] = "<series>/<contest>/judge-<judge>/<capture>/page.html"
    pages = frozen["pages"]

    # ---- 2. pages -> sets ----
    rows_at_start = {sid: len(s.get("problems") or []) for sid, s in sets.items()}
    by_set: dict[str, list[dict]] = defaultdict(list)
    for k, rec in pages.items():
        c = contests.get(rec["contest"])
        if c is None:
            report["capture for a contest not in the catalogue (skipped)"].append(f"{rec['contest']}: {rec['url']}")
            continue
        src = next((s for s in by_role(c, "judge_page") if norm_key(s["url"]) == norm_key(rec["url"])), None)
        if src is None:
            report["capture URL is not a judge_page source of its contest (skipped)"].append(f"{rec['contest']}: {rec['url']}")
            continue
        if rec["judge"] not in judges:
            report["judge not in judges.yaml (skipped)"].append(f"{rec['contest']}: {rec['judge']}")
            continue
        if not rec["problems"]:
            report[f"{rec['judge']}: pages that yielded no problems (every capture tried)"].append(
                f"{rec['contest']}: {rec['url']} — " + "; ".join(rec["tried"]))
            stats[f"{rec['judge']}: pages failed to parse"] += 1
            continue
        stats[f"{rec['judge']}: pages parsed"] += 1
        if rec.get("skipped"):
            stats[f"{rec['judge']}: practice rows skipped"] += len(rec["skipped"])
            report["rows skipped as not the contest's (practice letters)"].append(
                f"{rec['contest']}: {rec['url']}: " + ", ".join(rec["skipped"]))
        if rec["tried"]:
            report["newer capture unusable, older one used"].append(
                f"{rec['contest']}: {rec['url']} -> {rec['capture']} (skipped: " + "; ".join(rec["tried"]) + ")")
        sid = set_id_of(c)
        if not sid or sid not in sets:
            # no set yet: a judge page listing the contest's problems is enough to open one
            # (DEFINITIONS.md, Problems) — unless the contest has not run (nothing publishable)
            d = c.get("date")
            if c.get("status") == "upcoming" or (d and str(d)[:10] > TODAY):
                report["contest has not run yet (page not applied)"].append(f"{rec['contest']}: {rec['url']}")
                continue
            sid = rec["contest"]
            if sid not in sets:
                sets[sid] = {"id": sid, "contests": [{"contest": sid}],
                             "provenance": [f"problem list from the {rec['judge']} judge page ({rec['url']}); "
                                            f"count taken from that page (tools/mine_judge_links.py)"]}
                set_text[sid] = ""
                new_sets.append(sid)
            c["problems"] = {"set": sid}
            dirty_contests.add(rec["contest"])
            report["problem set opened from a judge page"].append(f"{rec['contest']}: {rec['url']}")
        by_set[sid].append(rec)

    new_sets_set = set(new_sets)
    created_sets: list[str] = []
    for sid in sorted(by_set):
        s = sets[sid]
        recs = sorted(by_set[sid], key=lambda r: (JUDGE_ORDER.get(r["judge"], 9), r["contest"], r["url"]))
        probs: list[dict] = s.get("problems") or []
        had_rows = bool(probs)
        count = s.get("count")
        # Kattis short names seen on problem-sources pages of this set (-> open.kattis.com is safe)
        open_shorts = {p["short"] for r in recs if r["judge"] == "kattis" for p in r["problems"] if p.get("kind") == "sources"}
        created_here = False

        # two passes: a page held back (or matching nothing) before another page created the rows
        # links on the second pass; observations are reported from the final pass only
        for final in (False, True):
            rep = report if final else defaultdict(list)
            st = stats if final else Counter()  # observations are counted once, from the final pass
            for r in recs:
                cid, judge = r["contest"], r["judge"]
                entry = set_entry(s, cid)
                letters: dict[str, str] = entry.get("letters") or {}
                by_id = {p["id"]: p for p in probs}
                by_name: dict[str, list[dict]] = defaultdict(list)
                for p in probs:
                    by_name[norm_title(p["name"])].append(p)
                for p in probs:  # "essentially same as <name> in <contest>": the judge may use that name
                    for m in re.finditer(r"same as (.+?) in [a-z0-9-]+-\d{4}", p.get("notes") or ""):
                        if p not in by_name[norm_title(m.group(1))]:
                            by_name[norm_title(m.group(1))].append(p)
                by_name.pop("", None)  # a title with no Latin letters or digits matches nothing by name
                where = f"{cid} ({sid}) {judge} {r['url']}"
                matched: dict[str, dict] = {}   # page problem id -> row
                unmatched: list[dict] = []
                lettering_agrees = True
                for pp in r["problems"]:
                    cands = by_name.get(norm_title(pp["name"]), [])
                    row = None
                    if len(cands) == 1:
                        row = cands[0]
                    elif len(cands) > 1:
                        row = by_id.get(letters.get(pp["letter"] or "")) if pp["letter"] else None
                        if row not in cands:
                            row = None
                            rep["ambiguous title (several rows share the name; not linked)"].append(f"{where}: {pp['name']!r}")
                            st["ambiguous (skipped)"] += 1
                            continue
                    if row is None:
                        unmatched.append(pp)
                        continue
                    if pp["letter"] and letters.get(pp["letter"]) and letters[pp["letter"]] != row["id"]:
                        other = by_id.get(letters[pp["letter"]], {}).get("name")
                        rep["letter check: page letter maps to another row (link still added)"].append(
                            f"{where}: {pp['letter']} is {pp['name']!r} on the page, {other!r} in the set")
                        st["letter mismatches"] += 1
                        lettering_agrees = False
                    matched[pp["id"]] = row

                # the page's lettering agrees with the contest's map (no name match contradicts it):
                # a title that matched nothing is the row its letter names (a translation or a rename)
                if lettering_agrees:
                    claimed = {id(v) for v in matched.values()}
                    for pp in list(unmatched):
                        row = by_id.get(letters.get(pp["letter"] or "")) if pp["letter"] else None
                        if row is not None and id(row) not in claimed:
                            matched[pp["id"]] = row
                            claimed.add(id(row))
                            unmatched.remove(pp)
                            rep["matched by letter only (title differs: a translation or a rename)"].append(
                                f"{where}: {pp['letter']} {pp['name']!r} -> {row['name']!r}")
                            st[f"{judge}: matched by letter (title differs)"] += 1

                # the set is complete and exactly one page problem and one row are left: they correspond
                if (len(unmatched) == 1 and count is not None and len(probs) == count
                        and len(probs) - len(set(id(v) for v in matched.values())) == 1):
                    left = next(p for p in probs if all(p is not v for v in matched.values()))
                    pp = unmatched.pop()
                    matched[pp["id"]] = left
                    rep["matched by elimination (last unmatched title <-> last unlinked row of a complete set)"].append(
                        f"{where}: {pp.get('letter') or '-'} {pp['name']!r} -> {left['name']!r}")
                    st[f"{judge}: matched by elimination"] += 1

                # a row claimed by two page problems: keep the first, report the second
                seen_rows: set[str] = set()
                for pp in r["problems"]:
                    row = matched.get(pp["id"])
                    if row is None:
                        continue
                    if row["id"] in seen_rows:
                        rep["two page problems match one row (second not linked)"].append(f"{where}: {pp['name']!r}")
                        del matched[pp["id"]]
                        continue
                    seen_rows.add(row["id"])

                # ---- links on matched rows ----
                for pp in r["problems"]:
                    row = matched.get(pp["id"])
                    if row is None:
                        continue
                    links = row.setdefault("judges", [])
                    new = [{"judge": judge, "url": pp["url"], "id": pp["id"]}]
                    if judge == "baekjoon" and r.get("as_of"):
                        new[0]["as_of"] = r["as_of"]
                    if judge == "kattis" and pp.get("kind") == "contest" and pp["short"] in open_shorts:
                        new.append({"judge": "kattis", "url": KATTIS_PROBLEM.format(pp["short"]), "id": pp["short"]})
                    for ln in new:
                        if not any(l["judge"] == ln["judge"] and norm_key(l["url"]) == norm_key(ln["url"]) for l in links):
                            links.append(ln)
                            stats[f"{judge}: links added"] += 1
                    if not links:
                        del row["judges"]
                    if judge == "kattis" and not row.get("short_name"):
                        row["short_name"] = pp["short"]
                        stats["short_name filled"] += 1
                    if pp["letter"] and lettering_agrees:  # letter -> row when both are unmapped
                        if pp["letter"] not in letters and row["id"] not in letters.values():
                            letters[pp["letter"]] = row["id"]
                            entry["letters"] = letters
                            stats["letters added to contest maps"] += 1

                # ---- unmatched titles: create rows when allowed ----
                if unmatched:
                    full = count is not None and len(probs) >= count
                    allow = ((not had_rows and not created_here) or s.get("complete") is False) and not full
                    n_page, n_after = len(r["problems"]), len(probs) + len(unmatched)
                    translated = [pp for pp in unmatched if NON_LATIN.search(pp["name"])]
                    if not args.allow_translated_names:
                        for pp in translated:
                            rep["translated title, no row to match (not created; the judge id is the lead to the English title)"].append(
                                f"{where}: {pp.get('letter') or '-'} {pp['id']} {pp['name']!r}")
                            st[f"{judge}: titles unmatched (translated)"] += 1
                        unmatched = [pp for pp in unmatched if pp not in translated]
                    if not unmatched:
                        pass
                    elif not allow:
                        for pp in unmatched:
                            rep["title matches no row of the set (not created)"].append(f"{where}: {pp.get('letter') or '-'} {pp['name']!r}")
                            st[f"{judge}: titles unmatched"] += 1
                    elif count and (n_page > count or n_after > count):
                        rep["held back: page lists more problems than the set's count (rows not created)"].append(
                            f"{where}: {n_page} on the page, {len(probs)} rows, count {count}: "
                            + ", ".join(f"{pp.get('letter') or '-'} {pp['name']}" for pp in unmatched))
                        st[f"{judge}: pages held back (count)"] += 1
                    else:
                        if not probs:
                            created_sets.append(sid)
                        for pp in unmatched:
                            letter = pp["letter"] if (pp["letter"] and pp["letter"] not in letters) else None
                            row = {"id": pid(None, sid, letter, pp["name"]), "name": pp["name"]}
                            if row["id"] in by_id:
                                rep["created id collides with an existing row (not created)"].append(f"{where}: {pp['name']!r}")
                                continue
                            link = {"judge": judge, "url": pp["url"], "id": pp["id"]}
                            if judge == "baekjoon" and r.get("as_of"):
                                link["as_of"] = r["as_of"]
                            row["judges"] = [link]
                            if judge == "kattis":
                                row["short_name"] = pp["short"]
                                if pp.get("kind") == "contest" and pp["short"] in open_shorts:
                                    row["judges"].append({"judge": "kattis", "url": KATTIS_PROBLEM.format(pp["short"]), "id": pp["short"]})
                            probs.append(row)
                            by_id[row["id"]] = row
                            by_name[norm_title(row["name"])].append(row)
                            if letter:
                                letters[letter] = row["id"]
                                entry["letters"] = letters
                            stats[f"{judge}: rows created"] += 1
                            stats[f"{judge}: links added"] += len(row["judges"])
                            if NON_LATIN.search(pp["name"]):
                                rep["row created with a non-Latin title (review)"].append(f"{where}: {pp.get('letter') or '-'} {pp['name']!r}")
                        s["problems"] = probs
                        created_here = True

        if not probs:
            continue
        # ---- set-level flags ----
        if any(e.get("letters") for e in s["contests"]):
            s.pop("letters", None)  # "no map is known for any contest" no longer holds
        else:
            s["letters"] = "unknown"
        if created_here:
            if sid in new_sets_set and count is None:
                s["count"] = count = len(probs)  # the page is the whole contest: it sets the count
            if count is None or len(probs) < count:
                s["complete"] = False
            elif len(probs) == count:
                s.pop("complete", None)

    # ---- 3. write ----
    note = f"online-judge pages ({args.date}, tools/mine_judge_links.py)"
    changed = sorted(sid for sid, s in sets.items() if dump_set(s) != set_text[sid])
    for sid in changed:
        prov = sets[sid].setdefault("provenance", [])
        if note not in prov:
            prov.append(note)
    if not args.dry_run:
        for sid in changed:
            (SET_DIR / f"{sid}.yaml").write_text(dump_set(sets[sid]))
        if dirty_contests:  # contests that got a `problems: {set}` link
            from catalogue import dump_series, load_series
            series = load_series()
            touched = set()
            for sid_, doc in series.items():
                for c in doc["contests"]:
                    if c["id"] in dirty_contests and c.get("problems") != contests[c["id"]].get("problems"):
                        c["problems"] = contests[c["id"]]["problems"]
                        touched.add(sid_)
            for sid_ in touched:
                dump_series(sid_, series[sid_], f"mine_judge_links.py (problem sets opened from judge pages, {args.date})")
            reg = ROOT / "registry" / "non-mainline.yaml"
            rdoc = yaml.safe_load(reg.read_text())
            rt = False
            for c in rdoc["non_mainline_contests"]:
                if c["id"] in dirty_contests and c.get("problems") != contests[c["id"]].get("problems"):
                    c["problems"] = contests[c["id"]]["problems"]
                    rt = True
            if rt:
                head = "".join(l for l in reg.read_text().splitlines(True)[:2] if l.startswith("#"))
                reg.write_text(head + yaml.dump(rdoc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
        frozen_path.parent.mkdir(parents=True, exist_ok=True)
        frozen_path.write_text(json.dumps(frozen, indent=1, ensure_ascii=False, sort_keys=True) + "\n")

    # ---- 4. report ----
    total_rows = sum(len(s.get("problems") or []) for s in sets.values())
    with_link = Counter()
    any_link = 0
    for s in sets.values():
        for p in s.get("problems") or []:
            js = {j["judge"] for j in p.get("judges") or []}
            any_link += bool(js)
            for j in js:
                with_link[j] += 1
    lines = [f"# Judge links mined from captured judge pages — {args.date}", "",
             f"Generated by `tools/mine_judge_links.py --archive {archive}` from {len(pages)} (contest, judge, url) "
             f"pages ({sum(len(v) for v in groups.values())} captures); extraction frozen in "
             f"`data/import/judge-pages-{args.date}.json`.", "",
             "## Rules applied", "",
             "- Per (contest, judge, url) the newest live capture is used, else the newest Wayback one; a capture that "
             "lists no problems falls back to the next older one (section *newer capture unusable*).",
             "- Titles match by normalised name; a page whose letters agree with the contest's letter map also matches "
             "an unmatched title through its letter (*matched by letter only*: Korean translations on Baekjoon, "
             "Portuguese/English pairs for Latin America); a page whose letters contradict the map gets links on "
             "name matches only (*letter check*). The last unmatched title of a complete set takes the last unlinked "
             "row (*matched by elimination*).",
             "- Rows are created from a page only for a set with no rows or `complete: false`, never past the set's "
             "`count` (*held back*), and never with a Korean/CJK title (*translated title, no row to match*; "
             "`--allow-translated-names` would create them). Created ids are p- + sha1(set|letter|name)[:8].",
             "- Page letters fill a contest's letter map where both the letter and the row were unmapped; "
             "`letters: unknown` is dropped once a member contest has a map (DEFINITIONS.md: it says no map is known "
             "for any contest).",
             "- Baekjoon links carry `as_of` = the Wayback snapshot mined (the judge closed 2026-04-28); Baekjoon "
             "practice problems (letters PA, PB, …) and Practice Session sections are skipped.",
             "- Kattis contest pages give the contest-page URL as the link; open.kattis.com is added only when the "
             "same short name is on a problem-sources page of the set.",
             "- Pages are applied in two passes per set so a page processed before another page created the rows "
             "still gets its links; a rerun changes nothing.", "",
             "## Per judge", ""]
    for j in sorted(judges, key=lambda j: JUDGE_ORDER.get(j, 9)):
        if not any(k.startswith(j + ":") for k in stats):
            continue
        lines.append(f"### {j}")
        lines.append("")
        for key in ("pages parsed", "pages failed to parse", "links added", "rows created", "titles unmatched",
                    "pages held back (count)", "matched by letter (title differs)", "matched by elimination",
                    "titles unmatched (translated)", "practice rows skipped"):
            lines.append(f"- {key}: {stats.get(f'{j}: {key}', 0)}")
        lines.append("")
    lines += ["## Totals", "",
              f"- problem rows now: {total_rows} (before: {sum(rows_at_start.values())})",
              f"- rows with at least one judge link: {any_link}",
              *[f"- rows with a {j} link: {n}" for j, n in sorted(with_link.items())],
              f"- sets that went from no rows to rows: {len(created_sets)}",
              f"- problemsets files {'that would change' if args.dry_run else 'written'}: {len(changed)}",
              *[f"- {k}: {v}" for k, v in sorted(stats.items()) if ":" not in k], ""]
    lines += ["## Sets that went from no rows to rows", ""] + [f"- {sid}" for sid in sorted(created_sets)] + [""]
    for k in sorted(report):
        lines += [f"## {k} ({len(report[k])})", ""] + [f"- {x}" for x in report[k]] + [""]
    rep = ROOT / "reports" / f"judge-links-{args.date}.md"
    if not args.dry_run:
        rep.write_text("\n".join(lines))
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print(f"rows: {sum(rows_at_start.values())} -> {total_rows}; with a link: {any_link}; sets from no rows to rows: "
          f"{len(created_sets)}; problemsets files {'that would change' if args.dry_run else 'written'}: {len(changed)}; "
          f"report sections: {len(report)} -> {rep.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
