#!/usr/bin/env python3
"""Check and apply the results of the description round (tools/describe_pack.py, describe_rubric.md).

  python3 tools/describe_apply.py --check ../_describe/pilot/nordic-2015
  python3 tools/describe_apply.py --run ../_describe/pilot --name pilot-2026-11-16 [--write]

Each <run>/<contest>/result.json is a reader's second reading of the contest's held sources: a
verdict on whether each copy is the document the catalogue says it is, a few facts the document
shows about itself, and a description.

--check prints `ok`, or what is wrong with one result (shape, lengths, words a description must
not use). A result that does not check is not applied.

Applied with --write:
  descriptions   data/source-descriptions/<series>/<contest>.yaml gets, per source the reader took
                 for the document (confirm or correct; not low confidence): the description, the
                 document facts (title, language, the contest date as stated, teams, problems,
                 times, tries, pages), the copy that was read and the day. An entry is replaced
                 when its source is read again; other entries of the file are kept.
  blanks         (only with --fill-blanks) a contest without a date gets the full date a document
                 states, and a contest with no location of any kind gets the place a document
                 states — only at high confidence, only when every document that states one states
                 the same, and for a date only within a year of the contest's own; with a
                 `provenance:` line. Without the flag they are listed as fills-blank, not written.
Listed, never applied (data/describe/<name>/, and the report):
  second-reading.json   every source the reader did not confirm, or where the reader disagrees
                        with the content check of 2026-11-14
  contest-facts.json    every contest fact a document states, classed: fills-blank, conflict, same
Collected: data/describe/<name>/verdicts/<series>.json (the verdicts without the descriptions).
Without --write nothing in the repo is changed; the report goes to <run>/report-dry-run.md.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogue as cat  # noqa: E402
from resources import norm_key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUBRIC = 1
VERDICTS = ("confirm", "correct", "not-the-document", "wrong-contest", "cannot-tell", "no-copy")
DESCRIBED = ("confirm", "correct")
DOC_KEYS = ("title", "title_en", "language", "contest_date", "teams", "problems", "times", "tries", "pages")
WORDS_MAX, WORDS_MIN, PARAS_MAX = 260, 15, 3
# what a description must not say: our plumbing, and praise
PLUMBING = [(r"\bpack(\.json)?\b", "the pack"), (r"\bdigest\b", "the digest"), (r"\bthe catalogue\b", "the catalogue"),
            (r"\bearlier (reader|verdict|check)\b", "the earlier reader"), (r"/mnt/|/sessions/|\.json\b|\bs\d+\.txt\b", "a path on our disk"),
            (r"https?://|\bwww\.", "an address"), (r"\bverdict\b", "the verdict"), (r"\bI (saw|opened|read|could|cannot|did)\b", "yourself")]
PRAISE = r"\b(comprehensive|valuable|invaluable|insightful|interesting|impressive|rich|detailed overview|provides an overview|offers insight|a wealth of)\b"
OPENERS = r"^(this|the) (document|source|page|file|copy) (is|contains|shows|provides|presents)\b"
MARKDOWN = r"(?m)^\s*(#{1,6} |[-*•] |\d+\. |>|```)|\*\*|\]\("


def paragraphs(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def check_description(d: str) -> list[str]:
    out = []
    ps = paragraphs(d)
    words = len(d.split())
    if len(ps) > PARAS_MAX:
        out.append(f"description has {len(ps)} paragraphs (at most {PARAS_MAX})")
    if words > WORDS_MAX:
        out.append(f"description has {words} words (at most about 220)")
    if words < WORDS_MIN:
        out.append(f"description has only {words} words")
    for rx, what in PLUMBING:
        m = re.search(rx, d, re.I if what != "yourself" else 0)
        if m:
            out.append(f"description mentions {what} ('{m.group(0)}')")
    m = re.search(PRAISE, d, re.I)
    if m:
        out.append(f"description judges instead of describing ('{m.group(0)}')")
    if re.search(OPENERS, d.strip(), re.I):
        out.append("description opens with 'This document/source/page …': start with the thing itself")
    if re.search(MARKDOWN, d):
        out.append("description uses markdown (plain text only, paragraphs separated by an empty line)")
    return out


def check(pack: dict, res: dict) -> list[str]:
    """What is wrong with a result, as sentences for the reader. Empty: it can be applied."""
    out: list[str] = []
    if not isinstance(res, dict) or not isinstance(res.get("sources"), list):
        return ["not an object with a `sources` list"]
    if res.get("contest") != pack["contest"]:
        out.append(f"`contest` is {res.get('contest')!r}, the pack is {pack['contest']!r}")
    if [s.get("n") for s in res["sources"]] != [s["n"] for s in pack["sources"]]:
        return out + [f"`sources` must have one entry per source of the pack, in order: n = {[s['n'] for s in pack['sources']]}"]
    for s, q in zip(res["sources"], pack["sources"]):
        w = f"source {q['n']}: "
        v = s.get("verdict")
        if v not in VERDICTS:
            out.append(w + f"verdict {v!r} is not one of {', '.join(VERDICTS)}")
            continue
        if (q.get("copy") is None) != (v == "no-copy"):
            out.append(w + ("it has no copy: the verdict must be no-copy" if q.get("copy") is None else "it has a copy: the verdict cannot be no-copy"))
            continue
        if v == "no-copy":
            if s.get("description"):
                out.append(w + "no copy, so no description")
            continue
        roles = s.get("roles")
        if not isinstance(roles, list) or any(r not in cat.ROLES for r in roles):
            out.append(w + f"`roles` must be a list out of {', '.join(cat.ROLES)}")
        elif v == "confirm" and sorted(roles) != sorted(q["roles"]):
            out.append(w + f"verdict confirm but roles {roles} are not the pack's {q['roles']}: use correct, or give the pack's roles")
        elif v == "correct" and sorted(roles) == sorted(q["roles"]) :
            out.append(w + "verdict correct but the roles are the pack's: use confirm")
        if s.get("confidence") not in ("high", "medium", "low"):
            out.append(w + "`confidence` must be high, medium or low")
        if not (s.get("evidence") or "").strip():
            out.append(w + "`evidence` is empty")
        if q.get("earlier"):
            if not isinstance(s.get("agrees_with_earlier"), bool):
                out.append(w + "`agrees_with_earlier` must be true or false (the pack has an earlier verdict)")
            elif s["agrees_with_earlier"] is False and not (s.get("disagreement") or "").strip():
                out.append(w + "`disagreement` must say what differs from the earlier reader")
        d = s.get("description")
        if v in DESCRIBED:
            if not isinstance(d, str) or not d.strip():
                out.append(w + "a description is needed (verdict confirm or correct)")
            else:
                out += [w + x for x in check_description(d)]
            doc = s.get("document")
            if not isinstance(doc, dict):
                out.append(w + "`document` must be an object")
            else:
                lang = doc.get("language")
                if lang is not None and not (isinstance(lang, list) and lang and all(isinstance(x, str) and re.fullmatch(r"[a-z]{2,3}", x) for x in lang)):
                    out.append(w + "`document.language` must be a list of ISO 639-1 codes, e.g. [\"en\"]")
                cd = doc.get("contest_date")
                if cd is not None and not (isinstance(cd, str) and re.fullmatch(r"\d{4}(-\d\d(-\d\d)?)?", cd)):
                    out.append(w + "`document.contest_date` must be YYYY-MM-DD, YYYY-MM or YYYY")
                for k in ("teams", "problems", "pages"):
                    if doc.get(k) is not None and not (isinstance(doc[k], int) and not isinstance(doc[k], bool) and 0 < doc[k] < 100000):
                        out.append(w + f"`document.{k}` must be a whole number or null")
                for k in ("times", "tries"):
                    if doc.get(k) is not None and not isinstance(doc[k], bool):
                        out.append(w + f"`document.{k}` must be true, false or null")
                for k in ("title", "title_en"):
                    if doc.get(k) is not None and not (isinstance(doc[k], str) and 0 < len(doc[k].strip()) <= 160):
                        out.append(w + f"`document.{k}` must be a string of at most 150 characters, or null")
        elif d:
            out.append(w + f"verdict {v}: `description` must be null")
    for f in res.get("contest_facts") or []:
        if not isinstance(f, dict) or not f.get("fact") or f.get("value") in (None, "") or not isinstance(f.get("from"), int):
            out.append(f"contest_facts: each needs fact, value and from (a source n): {json.dumps(f, ensure_ascii=False)[:120]}")
        elif f["fact"] == "date" and not re.fullmatch(r"\d{4}-\d\d-\d\d", str(f["value"])):
            out.append(f"contest_facts: a date must be YYYY-MM-DD, got {f['value']!r} (leave it out if the document gives no full date)")
    return out


class Lit(str):
    pass


class _Dumper(yaml.SafeDumper):
    pass


_Dumper.add_representer(Lit, lambda d, s: d.represent_scalar("tag:yaml.org,2002:str", str(s), style="|"))


def entry(q: dict, s: dict, day: str) -> dict:
    doc = s.get("document") or {}
    e: dict = {"url": q["url"], "read": day, "rubric": RUBRIC, "copy": q["copy"]["path"]}
    roles = set(s.get("roles") or [])
    for k in DOC_KEYS:
        v = doc.get(k)
        if v is None or v == "" or v == []:
            continue
        if k in ("times", "tries") and not roles & {"scoreboard", "frozen_scoreboard"}:
            continue   # per-problem times and attempts: a scoreboard's facts only
        if k == "teams" and not roles & {"scoreboard", "frozen_scoreboard", "standings", "rankings", "teams"}:
            continue
        e[k] = v.strip() if isinstance(v, str) else v
    e["description"] = Lit("\n\n".join(paragraphs(s["description"])))
    return e


def write_descriptions(series_id: str, cid: str, new: list[dict], current: set) -> tuple[int, int]:
    """Merge `new` into the contest's file. Entries of addresses the contest no longer cites are
    dropped. Returns (written, kept from before)."""
    f = ROOT / "data" / "source-descriptions" / series_id / f"{cid}.yaml"
    old = (yaml.safe_load(f.read_text()) or {}).get("sources") or [] if f.exists() else []
    fresh = {norm_key(e["url"]) for e in new}
    kept = [e for e in old if norm_key(e["url"]) not in fresh and norm_key(e["url"]) in current]
    for e in kept:
        e["description"] = Lit(e["description"])
    doc = {"contest": cid, "sources": kept + new}
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("# Written by tools/describe_apply.py from readings of the copies we hold. See README.md in data/source-descriptions.\n"
                 + yaml.dump(doc, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=10000))
    return len(new), len(kept)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check")
    ap.add_argument("--run")
    ap.add_argument("--name")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--fill-blanks", action="store_true", help="with --write: also write the blank dates and locations into the series files")
    a = ap.parse_args()
    if a.check:
        d = Path(a.check)
        try:
            res = json.loads((d / "result.json").read_text())
        except Exception as e:  # noqa: BLE001
            print(f"result.json cannot be read as JSON: {e}")
            return 1
        bad = check(json.loads((d / "pack.json").read_text()), res)
        print("\n".join(bad) if bad else "ok")
        return 1 if bad else 0
    if not (a.run and a.name):
        ap.error("--run and --name, or --check")
    run = Path(a.run).resolve()
    series = cat.load_series()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    index = json.loads((run / "index.json").read_text())
    n = Counter()
    second, facts, verdicts, bad, missing = [], [], defaultdict(dict), [], []
    desc: dict = {}       # contest -> [entries]
    touched = set()
    samples = []
    for x in index:
        cid = x["contest"]
        if not x["with_copy"]:
            n["contests with nothing held"] += 1
            continue
        p = run / cid / "result.json"
        if not p.exists():
            missing.append(cid)
            continue
        pack = json.loads((run / cid / "pack.json").read_text())
        try:
            res = json.loads(p.read_text())
            problems = check(pack, res)
        except Exception as e:  # noqa: BLE001
            problems = [f"not JSON: {e}"]
        if problems:
            bad.append((cid, problems))
            continue
        if cid not in where:
            bad.append((cid, ["the contest is no longer in the catalogue"]))
            continue
        sid, c = where[cid]
        n["contests read"] += 1
        vs = []
        for s, q in zip(res["sources"], pack["sources"]):
            v = s["verdict"]
            n["sources"] += 1
            if v == "no-copy":
                n["no copy"] += 1
                continue
            n["read"] += 1
            n["verdict " + v] += 1
            e = q.get("earlier")
            vs.append({"url": q["url"], "verdict": v, "roles": s.get("roles"), "was": q["roles"], "confidence": s.get("confidence"),
                       "evidence": s.get("evidence"), "same_as": s.get("same_as"), "agrees_with_earlier": s.get("agrees_with_earlier"),
                       "disagreement": s.get("disagreement"), "copy": q["copy"]["path"]})
            if e is None:
                n["first readings"] += 1
            elif s.get("agrees_with_earlier") is False:
                n["disagrees with the earlier reader"] += 1
            if v != "confirm" or s.get("agrees_with_earlier") is False:
                second.append({"contest": cid, "url": q["url"], "catalogue_roles": q["roles"], "verdict": v, "roles": s.get("roles"),
                               "confidence": s.get("confidence"), "evidence": s.get("evidence"), "disagreement": s.get("disagreement"),
                               "earlier": ({k: e.get(k) for k in ("verdict", "roles", "confidence", "evidence", "same_copy")} if e else None)})
            if v in DESCRIBED and s.get("confidence") != "low" and cat.find_source(c, q["url"]):
                desc.setdefault(cid, []).append(entry(q, s, a.date))
                n["described"] += 1
                n["words"] += len(s["description"].split())
                samples.append((cid, q, s))
            elif v in DESCRIBED:
                n["description held (low confidence or source gone)"] += 1
        verdicts[sid][cid] = {"read": a.date, "rubric": RUBRIC, "sources": vs, "notes": res.get("notes") or ""}
        # ---- contest facts ----
        by_fact = defaultdict(list)
        for f in res.get("contest_facts") or []:
            by_fact[str(f["fact"]).lower()].append(f)
        for fact, fs in by_fact.items():
            vals = {str(f["value"]).strip() for f in fs}
            has = {"date": str(c.get("date") or ""), "location": c.get("location") or ("(sites)" if c.get("sites") else "")}.get(fact)
            for f in fs:
                src = pack["sources"][f["from"] - 1]["url"] if 0 < f["from"] <= len(pack["sources"]) else None
                kind = "listed"
                if has is not None:
                    kind = "fills-blank" if not has else "same" if str(f["value"]).strip() == has else "conflict"
                row = {"contest": cid, "fact": fact, "value": f["value"], "catalogue": has, "from": src, "confidence": f.get("confidence"),
                       "seen": f.get("seen"), "class": kind, "applied": False}
                if kind == "fills-blank" and f.get("confidence") == "high" and len(vals) == 1 and src:
                    ok = True
                    if fact == "date":
                        y = int(cid.rsplit("-", 1)[1])
                        ok = abs(int(str(f["value"])[:4]) - y) <= 1
                    if ok and (fact, cid) not in touched:
                        c[fact] = str(f["value"]).strip()
                        c.setdefault("provenance", []).append(f"{fact} read from {src} (description round {a.date})")
                        touched.add((fact, cid))
                        row["applied"] = bool(a.write and a.fill_blanks)
                        row["would_fill"] = True
                        n[f"blank {fact} " + ("filled" if row["applied"] else "that a document fills (not written: --fill-blanks)")] += 1
                n["contest facts " + kind] += 1
                facts.append(row)
    # ---- write ----
    lists = (ROOT / "data" / "describe" / a.name) if a.write else (run / "lists-dry-run")
    lists.mkdir(parents=True, exist_ok=True)
    (lists / "second-reading.json").write_text(json.dumps(second, indent=1, ensure_ascii=False) + "\n")
    (lists / "contest-facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False) + "\n")
    if a.write:
        (lists / "verdicts").mkdir(exist_ok=True)
        for sid, v in sorted(verdicts.items()):
            f = lists / "verdicts" / f"{sid}.json"
            old = json.loads(f.read_text()) if f.exists() else {}
            old.update(v)
            f.write_text(json.dumps(old, indent=0, ensure_ascii=False, sort_keys=True) + "\n")
        files = 0
        for cid, new in sorted(desc.items()):
            sid, c = where[cid]
            write_descriptions(sid, cid, new, {norm_key(s["url"]) for s in cat.sources(c)})
            files += 1
        filled = {cid for _, cid in touched} if a.fill_blanks else set()
        for sid in sorted({where[cid][0] for cid in filled}):
            series[sid]["contests"] = [cat.normalise_contest(k) if k["id"] in filled else k for k in series[sid]["contests"]]
            cat.dump_series(sid, series[sid], "describe_apply.py")
        print(f"written: {files} description files, {len({where[cid][0] for cid in filled})} series files")
    # ---- report ----
    L = [f"# Source descriptions: {a.name}", "",
         f"Run of {a.date}, rubric {RUBRIC} (`tools/describe_rubric.md`). " + ("Applied." if a.write else "DRY RUN: nothing applied."), "",
         "| | |", "| --- | --- |"]
    for k in ("contests read", "contests with nothing held", "sources", "no copy", "read", "first readings", "described",
              "description held (low confidence or source gone)", "verdict confirm", "verdict correct", "verdict not-the-document",
              "verdict wrong-contest", "verdict cannot-tell", "disagrees with the earlier reader", "blank date filled", "blank location filled",
              "blank date that a document fills (not written: --fill-blanks)", "blank location that a document fills (not written: --fill-blanks)",
              "contest facts fills-blank", "contest facts conflict", "contest facts same", "contest facts listed"):
        if n[k]:
            L.append(f"| {k} | {n[k]:,} |")
    if n["described"]:
        L.append(f"| words per description | {n['words'] // n['described']} |")
    L += ["", f"Not finished: {len(missing)} contests" + (": " + ", ".join(missing[:40]) if missing else "") + ".",
          f"Results that do not check: {len(bad)}." , ""]
    for cid, pr in bad[:30]:
        L.append(f"- `{cid}`: " + "; ".join(pr[:3]))
    L += ["", f"## Second reading: {len(second)} sources to look at", "",
          "The reader did not confirm the catalogue, or disagrees with the content check of 2026-11-14. Nothing here was applied.", "",
          "| contest | address | catalogue | this reading | earlier reading | what the reader saw |", "| --- | --- | --- | --- | --- | --- |"]
    for r in second:
        e = r["earlier"] or {}
        L.append(f"| {r['contest']} | {r['url'][:70]} | {'+'.join(r['catalogue_roles'])} | {r['verdict']}"
                 + (f" → {'+'.join(r['roles'] or []) or 'no role'}" if r["verdict"] == "correct" else "") + f" ({r['confidence']})"
                 + f" | {e.get('verdict', 'none')}" + (f" → {'+'.join(e.get('roles') or [])}" if e.get("verdict") == "correct" else "")
                 + f" | {(r['disagreement'] or r['evidence'] or '').replace('|', '/')[:220]} |")
    cf = [f for f in facts if f["class"] in ("fills-blank", "conflict")]
    L += ["", f"## Contest facts: {len(cf)} that fill a blank or differ", "",
          "| contest | fact | document says | catalogue | confidence | applied | where it is stated |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for f in sorted(cf, key=lambda f: (f["class"], f["contest"])):
        L.append(f"| {f['contest']} | {f['fact']} | {str(f['value'])[:60]} | {str(f['catalogue'] or '—')[:50]} | {f['confidence']} | "
                 f"{'yes' if f['applied'] else 'no'} | {str(f.get('seen') or '').replace('|', '/')[:160]} |")
    rep = (ROOT / "reports" / f"source-descriptions-{a.name}.md") if a.write else (run / "report-dry-run.md")
    rep.write_text("\n".join(L) + "\n")
    print(json.dumps(dict(n), indent=0)[:1500])
    print(f"not finished: {len(missing)}; do not check: {len(bad)}; report -> {rep}")
    for cid, pr in bad[:10]:
        print("BAD", cid, pr[:2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
