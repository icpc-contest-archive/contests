#!/usr/bin/env python3
"""Problem count and letters read off scoreboards we hold (2026-11-16).

  python3 tools/letters_from_scoreboards.py [--write] [--report reports/scoreboard-letters-<date>.md]

A scoreboard has a column per problem, so a contest whose scoreboard we hold cannot have
"nothing known" about its problems: the header gives how many there were and what they were
called (A, B, C ... or 0, 1, 2 ...). For every contest that ran, has no problem count and no
problem list, and of which we hold a scoreboard (archive checked out beside this repo):

  one reading       every held scoreboard that can be read gives the same labels: the contest gets
                    a problem set of its own with `count` and, on its member entry, `labels`
                    (an existing empty set is filled in);
  shared set        a Latin America regional site joins the season's `latam-<year>` set when its
                    scoreboard has as many problems as the set, with the set's letters;
  held              two scoreboards that disagree (divisions, usually) are listed, not applied;
  not read          a scoreboard in a form the reader does not know is listed, not guessed.

Names are not read here (tools/import_scoreboard_titles_b.py does that where a header prints
them). Without --write nothing is changed.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, archived, by_role, dump_series, load_series, load_sets, set_of  # noqa: E402
from import_judge_links import dump  # noqa: E402

ARCHIVE = ROOT.parent / "archive"
TOOL = "tools/letters_from_scoreboards.py"
LATAM = ("brazil", "mexico", "caribbean", "central-america", "south-america-north", "south-america-south", "bolivia")


def text(x: str) -> str:
    x = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", x)
    x = re.sub(r"(?i)<br\s*/?>", " ", x)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", x))).strip()


def load(p: Path) -> str | None:
    b = p.read_bytes()
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return None


WORDED = re.compile(r"(?i)(?:problem|prob|p|задача)\s*\.?\s*([A-Z]|\d{1,2})")


def labels_of(cells: list[str]) -> list[str]:
    """The longest run of header cells that are problem labels in order: A B C … / 1 2 3 … /
    `A. Title` / `Problem A`. It must start at A, 1 or 0 and have at least three."""
    best: list[str] = []
    run: list[str] = []
    for raw in cells + [""]:
        t = text(raw)
        lab = None
        if re.fullmatch(r"[A-Z]\d?", t) or re.fullmatch(r"\d{1,2}", t):
            lab = t
        elif len(t) <= 60 and re.match(r"^[A-Z][.:)\s-]", t):
            lab = t[0]
        elif WORDED.fullmatch(t):
            lab = WORDED.fullmatch(t).group(1).upper()
        if lab is not None and run:
            prev = run[-1]
            follows = ((prev.isdigit() and lab.isdigit() and int(lab) == int(prev) + 1)
                       or (len(prev) == 1 and len(lab) == 1 and prev.isalpha() and lab.isalpha() and ord(lab) == ord(prev) + 1))
            if not follows:
                best, run = (run if len(run) > len(best) else best), []
        if lab is None:
            best, run = (run if len(run) > len(best) else best), []
        else:
            run.append(lab)
    return best if len(best) >= 3 and best[0] in ("A", "1", "0") else []


def read_scoreboard(p: Path) -> list[str]:
    s = load(p)
    if not s:
        return []
    best: list[str] = []
    for row in re.findall(r"(?is)<tr\b.*?(?=<tr\b|</table>|$)", s)[:400]:
        cells = re.findall(r"(?is)<t[hd]\b[^>]*>(.*?)(?=<t[hd]\b|</tr>|$)", row)
        if len(cells) >= 4:
            labs = labels_of(cells)
            if len(labs) > len(best):
                best = labs
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--report", default=None)
    a = ap.parse_args()
    if not ARCHIVE.exists():
        sys.exit("the archive repository is not checked out beside this one")
    today = datetime.date.today().isoformat()
    series, sets = load_series(), load_sets()
    held = collections.defaultdict(list)
    bad = set()
    for e in json.loads((ROOT / "data" / "archive-index.json").read_text())["captures"]:
        if e.get("content_caveat") or "html" not in (e.get("content_type") or ""):
            bad.add(e["path"])
        elif e.get("artifact") == "scoreboard":
            held[e["contest"]].append(e["path"])
    # and every copy the catalogue ties to a scoreboard source, whatever kind it was filed as when it was captured
    for doc in series.values():
        for c in doc["contests"]:
            for s in by_role(c, "scoreboard"):
                for p in archived(s):
                    if p not in bad and p not in held[c["id"]] and re.search(r"\.(html?|aspx|php|shtml)$", p, re.I):
                        held[c["id"]].append(p)
    rep = collections.defaultdict(list)
    touched_series, touched_sets = set(), set()
    for sid, doc in series.items():
        for c in doc["contests"]:
            cid = c["id"]
            if c.get("status") == "upcoming" or cid not in held:
                continue
            own = set_of(c, sets)
            if own and (own.get("problems") or own.get("count")):
                continue
            readings = {}
            for p in held[cid]:
                f = ARCHIVE / p
                labs = read_scoreboard(f) if f.exists() else []
                if labs:
                    readings[p] = labs
            if not readings:
                rep["not read"].append(f"{cid}: " + ", ".join(held[cid]))
                continue
            if len({tuple(v) for v in readings.values()}) > 1:
                rep["held: its scoreboards disagree"].append(f"{cid}: " + "; ".join(f"{len(v)} ({v[0]}–{v[-1]}) in {p}" for p, v in readings.items()))
                continue
            path, labs = next(iter(readings.items()))
            year = cid.rsplit("-", 1)[1]
            shared = sets.get(f"latam-{year}") if sid in LATAM else None
            if shared and not own:
                n = shared.get("count") or len(shared.get("problems") or [])
                if n != len(labs):
                    rep["held: a Latin America site whose scoreboard does not match the shared set"].append(f"{cid}: {len(labs)} problems on its scoreboard, {n} in latam-{year}")
                    continue
                first = next((m.get("letters") for m in shared["contests"] if m.get("letters")), None)
                entry = {"contest": cid}
                if first and list(first) == labs:
                    entry["letters"] = dict(first)
                shared["contests"].append(entry)
                shared.setdefault("provenance", []).append(
                    f"{cid} sat this set: the Latin America regional is one shared set, and its scoreboard {path} has the same {len(labs)} problems ({labs[0]}–{labs[-1]}) ({TOOL}, {today})")
                c["problems"] = {"set": shared["id"]}
                touched_sets.add(shared["id"]); touched_series.add(sid)
                rep["joined the shared set"].append(f"{cid} -> latam-{year} ({len(labs)} problems)")
                continue
            if sid in LATAM and not own:
                rep["held: a Latin America site with no shared set for its year"].append(f"{cid}: {len(labs)} problems ({labs[0]}–{labs[-1]})")
                continue
            st = own or {"id": cid, "contests": [{"contest": cid}]}
            st["count"] = len(labs)
            entry = next((m for m in st["contests"] if m["contest"] == cid), None)
            if entry is None or len(st["contests"]) > 1:
                rep["held: an empty set shared by several contests"].append(f"{cid}: set {st['id']}")
                continue
            entry["labels"] = labs
            st.setdefault("provenance", []).append(f"count and letters read off the scoreboard {path} ({TOOL}, {today})")
            sets[st["id"]] = st
            c["problems"] = {**(c.get("problems") or {}), "set": st["id"]}
            touched_sets.add(st["id"]); touched_series.add(sid)
            rep["count and letters recorded"].append(f"{cid}: {len(labs)} problems, {labs[0]}–{labs[-1]}")
    if a.write:
        for s in sorted(touched_sets):
            order = ("id", "name", "aliases", "repo", "count", "complete", "letters", "statement", "data", "solutions", "package", "counts", "contests", "problems", "provenance", "notes")
            doc = {k: sets[s][k] for k in order if k in sets[s]}
            (ROOT / "problemsets" / f"{s}.yaml").write_text(dump(doc))
        for sid in sorted(touched_series):
            dump_series(sid, series[sid], "letters_from_scoreboards.py")
    lines = [f"# Problem count and letters from held scoreboards — {today}", "",
             "Contests that ran, had no problem count and no problem list, and of which we hold a scoreboard.", ""]
    for k in ("count and letters recorded", "joined the shared set"):
        lines += [f"## {k[0].upper() + k[1:]} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
    for k in sorted(k for k in rep if k.startswith("held")):
        lines += [f"## {k[0].upper() + k[1:]} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
    lines += [f"## Not read ({len(rep['not read'])})", "", "The scoreboard is in a form the reader does not know (a grid without a header row, an app, a division layout).", ""] + [f"- {x}" for x in rep["not read"]] + [""]
    if a.report and a.write:
        (ROOT / a.report).write_text("\n".join(lines))
    print("\n".join(f"{len(v):4} {k}" for k, v in rep.items()) + ("" if a.write else "\n(dry run; --write to apply)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
