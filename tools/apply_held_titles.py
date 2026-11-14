#!/usr/bin/env python3
"""Apply the statement-title candidates that apply_statement_titles.py held for ruling, where an
existing ruling or practice already decides them (2026-11-14):

  shared      the list equals another contest's set (flags same-as / same-set): the contest joins
              that set with its own letter map (ruling 2026-11-12: duplicate sets are one shared set).
              Every title must be found in the set (a title cut short in a standings header counts
              when it is the start of exactly one name there, as does a one-letter misspelling).
              A set that lists only some of the names is completed from the joining contest's
              list when every name it has is in that list. When no named contest has a list yet,
              the first one opens the set and the others join it.
  no-labels   the source prints no letters: names are recorded, letters stay unknown (as for lists
              that come from an online judge).
  standings   names read from the contest's own standings header: recorded; may be abbreviated.
  ocr         names read by OCR from a scanned statement: recorded, said so in the provenance.
  partial     some names only: recorded without a count.

Still held, for a ruling: identity? / divisions / two-rounds / truncated? / secondary-source /
count disagreements, a shared list where the contest's own set has holdings, and anything that fails the checks.

usage: apply_held_titles.py <candidates.json> --date YYYY-MM-DD [--dry-run]
"""
from __future__ import annotations
import argparse, collections, difflib, json, re, sys, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, dump_series, load_judges, load_series, load_sets  # noqa: E402
from add_statement_sources import statement_source  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

HOLD = {"identity?", "divisions", "two-rounds", "truncated?", "secondary-source", "letters-not-contiguous", "count"}


def norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9а-яё]+", "", s)


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("candidates"); ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--report", default=None); a = ap.parse_args()
    cands = json.loads(Path(a.candidates).read_text())
    series = load_series(); sets = load_sets(); judges = load_judges()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    rep = collections.defaultdict(list); touched = set(); changed = set(); gone = []; nprob = njoin = 0

    def set_of(cid):
        c = where.get(cid, (None, {}))[1]; s = sets.get((c.get("problems") or {}).get("set"))
        return s if s and s.get("problems") else None

    for cid, v in sorted(cands.items()):
        if not v.get("flags") or cid not in where:
            continue
        ser, c = where[cid]; probs = v["problems"]; flags = v["flags"]; kinds = {f.split(":")[0] for f in flags}
        line = f"{cid}: {len(probs)} problems <- {v['url']}  [{'; '.join(flags)}]"
        own = sets.get((c.get("problems") or {}).get("set"))
        if own and own.get("problems"):
            rep["set already lists problems (skipped)"].append(line); continue
        if c.get("status") == "upcoming":
            rep["contest has not run"].append(line); continue
        if kinds & HOLD:
            rep["still held: " + sorted(kinds & HOLD)[0]].append(line); continue
        names = [p["name"].replace("ı́", "í").strip() for p in probs]
        if len({norm(n) for n in names}) != len(names) or not all(norm(n) for n in names):
            rep["still held: two problems with one name, or an empty name"].append(line); continue
        how = ("its standings header" if "standings-header" in kinds else "the published statement") + f" {v['url']}" + (" (read by OCR)" if "ocr" in kinds else "")
        others = [o for f in flags if f.startswith(("same-as:", "same-set:")) for o in f.split(":", 1)[1].split(",")]
        target = next((set_of(o) for o in others if set_of(o)), None)
        if target is not None and own and any(k in own for k in ("repo", "statement", "data")):
            rep["still held: shared list, but the contest's own set has holdings"].append(line); continue
        if target is not None:
            by = {norm(p["name"]): p["id"] for p in target["problems"]}; letters = {}; miss = []

            def find(k):
                if k in by: return by[k]
                near = [i for kk, i in by.items() if (len(k) >= 6 and kk.startswith(k)) or (len(k) >= 10 and difflib.SequenceMatcher(None, k, kk).ratio() >= 0.92)]
                return near[0] if len(near) == 1 else None
            for p, n in zip(probs, names):
                hit = find(norm(n))
                if hit: letters[p["letter"]] = hit
                else: miss.append((p["letter"], n))
            if len(set(letters.values())) != len(letters):
                rep["still held: not the same list as " + target["id"]].append(line); continue
            if miss:   # the shared set lists fewer names than this contest's source: the rest are added when nothing disagrees
                if len(set(letters.values())) != len(target["problems"]) or (target.get("count") and target["count"] != len(probs)) or "no-labels" in kinds:
                    rep["still held: not the same list as " + target["id"]].append(line + "  not found: " + " | ".join(n for _l, n in miss)); continue
                for letter, n in miss:
                    row = {"id": pid(None, target["id"], letter, n), "name": n}
                    target["problems"].append(row); letters[letter] = row["id"]; nprob += 1
                target.setdefault("provenance", []).append(f"{len(miss)} more names from {cid}: {how} (tools/apply_held_titles.py, {a.date})")
                rep["shared set completed from the joining contest"].append(f"{target['id']} +{len(miss)} from {cid}: " + " | ".join(n for _l, n in miss))
            if own:   # an empty set of its own: the shared set takes its place
                target.setdefault("aliases", []).append(own["id"]); gone.append(own["id"]); del sets[own["id"]]
            e = {"contest": cid}
            if "no-labels" not in kinds: e["letters"] = letters
            target["contests"].append(e); c["problems"] = {"set": target["id"]}; touched.add(ser)
            target.setdefault("provenance", []).append(f"{cid} sat this set: the same list in {how} (tools/apply_held_titles.py, {a.date})")
            changed.add(target["id"]); njoin += 1; rep["joined a shared set"].append(f"{cid} -> {target['id']}")
        else:
            sid = own["id"] if own else cid
            if not own and sid in sets:
                rep["still held: set id taken"].append(line); continue
            if own and own.get("count") and own["count"] != len(probs):
                rep["still held: count"].append(line + f"  [set count {own['count']}]"); continue
            s = own or {"id": sid, "contests": [{"contest": cid}], "provenance": []}
            sets[sid] = s; nolab = "no-labels" in kinds
            rows = [{"id": pid(None, sid, None if nolab else p["letter"], n), "name": n} for p, n in zip(probs, names)]
            if len({r["id"] for r in rows}) != len(rows):
                rep["still held: id clash"].append(line); continue
            s["problems"] = rows
            if "partial" in kinds: s["complete"] = False
            else: s["count"] = len(rows)
            e = next(e for e in s["contests"] if e["contest"] == cid)
            if nolab: s["letters"] = "unknown"
            else: e["letters"] = {p["letter"]: r["id"] for p, r in zip(probs, rows)}
            s.setdefault("provenance", []).append(f"problem names read from {how}" + (f" (capture {v['path']})" if v.get("path") else "")
                                                  + ("; the source prints no letters" if nolab else "") + ("; titles may be abbreviated" if "standings-header" in kinds else "")
                                                  + f" (tools/apply_held_titles.py, {a.date})")
            c["problems"] = {"set": sid}; touched.add(ser); changed.add(sid); nprob += len(rows)
            rep["applied: " + ("no-labels" if nolab else "standings header" if "standings-header" in kinds else "ocr" if "ocr" in kinds else "partial" if "partial" in kinds else "first of a shared set")].append(f"{cid}: {len(rows)} problems")
        if "standings-header" not in kinds and statement_source(c, v["url"].split(" + ")[0], judges)[1]:
            touched.add(ser)
    if not a.dry_run:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for sid in gone: (ROOT / "problemsets" / f"{sid}.yaml").unlink()
        for ser in touched: dump_series(ser, series[ser], f"apply_held_titles.py ({a.date})")
        lines = [f"# Held statement titles applied — {a.date}", "", f"Generated by `tools/apply_held_titles.py` from `{a.candidates}`.", "",
                 f"- problems created: {nprob}", f"- contests that joined a shared set: {njoin}", ""]
        for k in sorted(rep, key=lambda k: (k.startswith("still"), k)):
            lines += [f"## {k} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
        (ROOT / "reports" / (a.report or f"held-titles-{a.date}.md")).write_text("\n".join(lines))
    print({k: len(v) for k, v in rep.items()}, "problems", nprob, "joins", njoin)
    for k in rep:
        if k.startswith("still held: not the same") or "clash" in k or "one name" in k or "taken" in k:
            print(k); [print("   ", x[:260]) for x in rep[k]]
    return 0


if __name__ == "__main__":
    sys.exit(main())
