#!/usr/bin/env python3
"""Audit captured archive artifacts for MISCLASSIFICATION.

We applied ~2,000 result URLs across waves 1-8 with automated verification. This
checks the CAPTURED CONTENT against the catalogue it is filed under, and flags:

  wrong-year    the page never mentions the contest's year (±1) but prominently
                shows a different year — likely the wrong edition captured
                (the syria-2017/2018 failure mode).
  not-results   filed as scoreboard/standings/rankings but the content has no
                ranking signals and looks like a homepage, problem set, or nav page.
  problemset    filed as a result but the content reads as a problem set.
  husk/dead     tiny, 404-ish, JS-shell, or login-wall content.
  caveated      already carries a content_caveat (surfaced for completeness).

Read-only. Stdlib + the captured bytes; NO network. Run in the VM (paths are the
mounted repos). Writes contests/reports/classification-audit-<date>.md + .json.

  python3 contests/tools/audit_classifications.py [--limit N] [--min-score 2]
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import re
from pathlib import Path

CONTESTS = Path(__file__).resolve().parent.parent          # .../contests
ARCHIVE = CONTESTS.parent / "archive"

TAG = re.compile(r"<[^>]+>")
YEAR = re.compile(r"\b(19[7-9]\d|20[0-4]\d)\b")
WS = re.compile(r"\s+")

RESULT_KINDS = {"scoreboard", "frozen_scoreboard", "standings", "rankings",
                "external-standings"}
RANK_TOKENS = ("rank", "place", "solved", "penalty", "score", "standing",
               "problems solved", "total time", "accepted", "1st", "gold",
               "medal", "team name", "university", "position")
PROBLEMSET_TOKENS = ("time limit", "memory limit", "sample input", "sample output",
                     "input format", "output format", "constraints", "problem a",
                     "problem set", "you are given", "1 second", "standard input")
DEAD_TOKENS = ("404", "not found", "page not found", "403 forbidden",
               "enable javascript", "please enable", "sign in", "log in to",
               "under construction", "domain for sale", "account suspended")


def text_of(path: Path) -> str:
    try:
        raw = path.read_bytes()[:300_000]
    except Exception:
        return ""
    t = raw.decode("utf-8", "replace")
    t = TAG.sub(" ", t)
    t = html.unescape(t)
    return WS.sub(" ", t).strip()


def load_catalogue():
    import yaml
    by_id = {}
    for f in sorted((CONTESTS / "series").glob("*.yaml")):
        try:
            doc = yaml.safe_load(f.read_text())
        except Exception:
            continue
        for c in (doc.get("contests") or []):
            by_id[c["id"]] = c
    return by_id


def expected_years(cid: str, c: dict) -> set[int]:
    ys = set()
    m = re.search(r"(\d{4})$", cid)
    if m:
        y = int(m.group(1))
        ys |= {y - 1, y, y + 1}          # held year ± season labeling
    for key in ("date",):
        v = str((c or {}).get(key) or "")
        m = re.match(r"(\d{4})", v)
        if m:
            yy = int(m.group(1))
            ys |= {yy - 1, yy, yy + 1}
    return ys


def audit_one(m: dict, mpath: Path, cat: dict) -> dict | None:
    cid = m.get("contest")
    kind = m.get("artifact") or m.get("kind") or ""
    cfile = m.get("content_file")
    if not cid or not cfile:
        return None
    content = mpath.parent / cfile
    flags, score = [], 0
    ev = {}

    if m.get("content_caveat"):
        return {"contest": cid, "kind": kind, "flags": ["caveated"], "score": 1,
                "url": m.get("url"), "path": str(mpath.parent.relative_to(ARCHIVE)),
                "evidence": {"caveat": m["content_caveat"]}}

    txt = text_of(content)
    low = txt.lower()
    n = len(txt)

    if n < 200:
        flags.append("husk/dead"); score += 2; ev["length"] = n
    dead_hit = [t for t in DEAD_TOKENS if t in low]
    if dead_hit and n < 4000:
        flags.append("husk/dead"); score += 2; ev["dead_tokens"] = dead_hit[:4]

    c = cat.get(cid, {})
    exp = expected_years(cid, c)
    yrs = [int(y) for y in YEAR.findall(txt)]
    if exp and yrs:
        from collections import Counter
        top = Counter(yrs).most_common(4)
        hit = any(y in exp for y in yrs)
        if not hit:
            flags.append("wrong-year"); score += 3
            ev["expected_year"] = sorted(exp)
            ev["found_years"] = [f"{y}x{n_}" for y, n_ in top]
    elif exp and not yrs and kind in RESULT_KINDS and n > 200:
        flags.append("wrong-year"); score += 1
        ev["expected_year"] = sorted(exp); ev["found_years"] = []

    if kind in RESULT_KINDS and "husk/dead" not in flags:
        rank_hits = sum(1 for t in RANK_TOKENS if t in low)
        ps_hits = sum(1 for t in PROBLEMSET_TOKENS if t in low)
        rows = low.count("<tr") + low.count("\n")  # tags already stripped; proxy on digits below
        digit_runs = len(re.findall(r"\b\d{1,4}\b", txt))
        looks_ranked = rank_hits >= 2 or digit_runs >= 40
        if ps_hits >= 3 and rank_hits < 2:
            flags.append("problemset"); score += 2
            ev["problemset_tokens"] = ps_hits; ev["rank_tokens"] = rank_hits
        elif not looks_ranked and n > 200:
            flags.append("not-results"); score += 2
            ev["rank_tokens"] = rank_hits; ev["digit_runs"] = digit_runs

    if not flags:
        return None
    snippet = txt[:180]
    return {"contest": cid, "kind": kind, "flags": flags, "score": score,
            "url": m.get("url"), "source": m.get("source"),
            "path": str(mpath.parent.relative_to(ARCHIVE)),
            "evidence": ev, "snippet": snippet}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-score", type=int, default=2)
    args = ap.parse_args()

    cat = load_catalogue()
    manifests = sorted(ARCHIVE.glob("*/*/*/*/manifest.json"))
    if args.limit:
        manifests = manifests[: args.limit]

    findings, seen = [], 0
    for mp in manifests:
        try:
            m = json.loads(mp.read_text())
        except Exception:
            continue
        seen += 1
        r = audit_one(m, mp, cat)
        if r and (r["score"] >= args.min_score or "caveated" in r["flags"]):
            findings.append(r)

    findings.sort(key=lambda r: (-r["score"], r["contest"]))
    from collections import Counter
    byflag = Counter(f for r in findings for f in r["flags"])
    bykind = Counter(r["kind"] for r in findings)

    date = datetime.date.today().isoformat()
    outj = CONTESTS / "reports" / f"classification-audit-{date}.json"
    outj.write_text(json.dumps({"generated": date, "scanned": seen,
                                "flagged": len(findings),
                                "by_flag": dict(byflag), "by_kind": dict(bykind),
                                "findings": findings}, indent=1, ensure_ascii=False))

    lines = [f"# Classification audit — {date}", "",
             f"Scanned **{seen}** captured artifacts; flagged **{len(findings)}** "
             f"(score ≥ {args.min_score}). Read-only content-vs-catalogue check. "
             f"Machine list + evidence: `data`/`reports/classification-audit-{date}.json`.",
             "",
             "Flag counts: " + ", ".join(f"{k} {v}" for k, v in byflag.most_common()),
             "", "Meaning: **wrong-year** = captured page's years don't include the "
             "contest's (likely wrong edition). **not-results** = filed as a board but no "
             "ranking signal (homepage/nav?). **problemset** = reads as a problem set. "
             "**husk/dead** = tiny/404/JS-shell/login. **caveated** = already flagged.",
             "", "## Top suspects", "",
             "| score | contest | kind | flags | evidence | snippet |",
             "|--:|---|---|---|---|---|"]
    for r in findings[:120]:
        ev = "; ".join(f"{k}={v}" for k, v in r["evidence"].items())[:70]
        sn = (r.get("snippet") or "").replace("|", "¦")[:60]
        lines.append(f"| {r['score']} | {r['contest']} | {r['kind']} | "
                     f"{','.join(r['flags'])} | {ev} | {sn} |")
    if len(findings) > 120:
        lines.append(f"\n…and {len(findings)-120} more in the JSON.")
    (CONTESTS / "reports" / f"classification-audit-{date}.md").write_text("\n".join(lines) + "\n")
    print(f"scanned {seen}, flagged {len(findings)}")
    print("by flag:", dict(byflag))
    print("by kind:", dict(bykind))
    print(f"-> reports/classification-audit-{date}.md (+ .json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
