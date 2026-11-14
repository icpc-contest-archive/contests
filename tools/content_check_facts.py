#!/usr/bin/env python3
"""Turn the contest facts the content check read out of the sources into a review list.

  python3 tools/content_check_facts.py --name run-2026-11-15

Agents note what a document states about the contest itself (date, place, teams, problems) next
to what the catalogue said at the time. Nothing is applied: a fact from one source is a lead, not
a ruling. Writes data/content-check/<run>/lists/contest-facts.json (every fact, classed) and
reports/contest-facts-<date>.md (the conflicts, by kind).
"""
import argparse, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import catalogue as cat

ROOT = Path(__file__).resolve().parent.parent
KIND = {"date": "date", "regional date": "date", "location": "location", "place": "location", "host": "location",
        "hosts": "location", "locations": "location", "sites": "sites", "number of sites": "sites",
        "teams": "teams", "number of teams": "teams", "problems": "problems", "number of problems": "problems",
        "name": "name", "season": "season"}


def num(v):
    m = re.search(r"\d+", str(v or ""))
    return int(m.group()) if m else None


def iso(v):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(v or ""))
    return m.group(0) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--packs", default="../_content-check/run1")
    a = ap.parse_args()
    run = ROOT / "data" / "content-check" / a.name
    verdicts = {}
    for f in sorted(run.glob("w*.json")):
        verdicts.update(json.loads(f.read_text()))
    contests = cat.load_contests()
    rows = []
    for cid, ver in sorted(verdicts.items()):
        c = contests.get(cid)
        if not c:
            continue
        try:
            pack = {s["n"]: s for s in json.loads((Path(a.packs) / cid / "pack.json").read_text())["sources"]}
        except OSError:
            pack = {}
        bad = {v["n"] for v in ver["sources"] if v["verdict"] in ("wrong-contest", "not-the-document")}
        for f in ver.get("contest_facts") or []:
            kind = KIND.get(str(f.get("fact")).strip().lower(), "other")
            val, was = f.get("value"), f.get("pack_says")
            src = pack.get(f.get("from")) or {}
            r = {"contest": cid, "fact": f.get("fact"), "kind": kind, "value": val, "catalogue": was,
                 "source": src.get("url"), "source_roles": src.get("roles")}
            if f.get("from") in bad:
                r["class"] = "from a source that is not about this contest"
            elif kind == "date":
                now = str(c.get("date") or "") or None
                r["catalogue"] = now
                d = iso(val)
                r["class"] = ("unreadable" if not d else "new" if not now else "agrees" if d == now
                              else "differs by a day" if abs(int(d[-2:]) - int(now[-2:])) == 1 and d[:7] == now[:7]
                              else "differs")
            elif kind == "problems":
                n, m = num(val), num(was)
                r["class"] = "unreadable" if n is None else "new" if m is None else "agrees" if n == m else "differs"
            elif kind in ("teams", "sites"):
                r["class"] = "new" if was in (None, "", "null") else "agrees" if num(val) == num(was) else "differs"
            else:
                r["class"] = "new" if was in (None, "", "null") else "agrees" if str(val).strip().lower() == str(was).strip().lower() else "differs"
            rows.append(r)
    (run / "lists").mkdir(exist_ok=True)
    (run / "lists" / "contest-facts.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    tab = defaultdict(Counter)
    for r in rows:
        tab[r["kind"]][r["class"]] += 1
    classes = ["agrees", "new", "differs by a day", "differs", "unreadable", "from a source that is not about this contest"]
    day = a.name.replace("run-", "")
    out = [f"# Contest facts read by the content check, {day}", "",
           f"What the sources themselves state about each contest, next to the catalogue ({len(rows)} facts). Nothing here",
           "has been applied. Every row is in `data/content-check/" + a.name + "/lists/contest-facts.json`.", "",
           "| Fact | " + " | ".join(classes) + " |", "|---|" + "---|" * len(classes)]
    for k in ("date", "location", "sites", "teams", "problems", "name", "season", "other"):
        out.append(f"| {k} | " + " | ".join(str(tab[k][x]) for x in classes) + " |")

    def table(title, kind, cls, cols=("contest", "catalogue", "value", "source")):
        sel = [r for r in rows if r["kind"] == kind and r["class"] in cls]
        out.extend(["", f"## {title} ({len(sel)})", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)])
        for r in sel:
            out.append("| " + " | ".join(str(r.get(k) if r.get(k) is not None else "").replace("|", "/")[:110] for k in cols) + " |")
    table("Dates that differ from the catalogue", "date", ("differs",))
    table("Dates one day off", "date", ("differs by a day",))
    table("Dates the catalogue lacks", "date", ("new",), ("contest", "value", "source"))
    table("Problem counts that differ", "problems", ("differs",))
    table("Locations that differ", "location", ("differs",))
    (ROOT / "reports" / f"contest-facts-{day}.md").write_text("\n".join(out) + "\n")
    print("\n".join(out[5:15]))


if __name__ == "__main__":
    sys.exit(main())
