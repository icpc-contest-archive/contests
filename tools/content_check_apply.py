#!/usr/bin/env python3
"""Apply content-check verdicts to the catalogue (rulings 14-18 of 2026-11-14).

  python3 tools/content_check_apply.py --name run-2026-11-15 --packs ../_content-check/run1 [--write]

Applied (high confidence only):
  retier        the document is a different kind than filed: roles (and a missing scope) are set
  move          a source about another edition that exists in the catalogue: moved there
  remove-wrong  a source about another contest that is named nowhere in the catalogue: removed
Listed, not applied:
  year-reused   wrong edition on an address that is reused every year, or that carries no
                number at all so may be one (ruling 16)
  not-document  our copy is not the document, or holds nothing about the contest: recapture, and
                remove the source if the page itself turns out empty (ruling 17)
  review        everything else that is not a plain confirmation (ruling 18)
Without --write nothing is changed; the lists and the report are written either way.
"""
import argparse, copy, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit
import catalogue as cat

ROOT = Path(__file__).resolve().parent.parent


def undated(url: str) -> bool:
    """An address with no digit after the host name: the kind that serves a new edition every
    year, so a copy of the wrong edition says little about what the address once held."""
    u = urlsplit(url)
    return not re.search(r"\d", u.path + "?" + u.query)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--packs", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    run = ROOT / "data" / "content-check" / a.name
    verdicts = {}
    for f in sorted(run.glob("w*.json")):
        verdicts.update(json.loads(f.read_text()))
    series = cat.load_series()
    contests = {}
    for sid, doc in series.items():
        for c in doc["contests"]:
            contests[c["id"]] = (sid, c)
    lists = defaultdict(list)
    count = Counter()
    touched = set()
    moves = []  # done after the loop so a moved source is not judged twice

    def row(cid, s, v, **extra):
        r = {"contest": cid, "url": s["url"], "was": list(s.get("roles") or []), "verdict": v["verdict"],
             "confidence": v.get("confidence"), "roles": v.get("roles") or [], "scope": v.get("scope"),
             "flags": v.get("flags") or [], "evidence": v.get("evidence")}
        r.update(extra)
        return r

    for cid, ver in sorted(verdicts.items()):
        if cid not in contests:
            count["contest gone"] += 1
            continue
        sid, c = contests[cid]
        pack = {s["n"]: s for s in json.loads((Path(a.packs) / cid / "pack.json").read_text())["sources"]}
        for v in ver["sources"]:
            p = pack[v["n"]]
            s = cat.find_source(c, p["url"])
            kind = v["verdict"]
            if s is None:
                count["source gone since the pack"] += 1
                continue
            if sorted(s["roles"]) != sorted(p["roles"]):
                if kind not in ("confirm", "no-copy"):
                    lists["review"].append(row(cid, s, v, why="roles changed since the check"))
                count["changed since the pack"] += 1
                continue
            high = v.get("confidence") == "high"
            flags = v.get("flags") or []
            new = [r for r in (v.get("roles") or []) if r in cat.RANK]
            new.sort(key=lambda r: cat.RANK[r])
            facts = v.get("facts") or {}
            if kind in ("confirm", "no-copy"):
                count[kind] += 1
                continue
            if kind in ("correct", "same-as"):
                if kind == "same-as" and (not new or sorted(new) == sorted(s["roles"])):
                    count["same-as (confirms)"] += 1
                    continue
                if not high:
                    lists["review"].append(row(cid, s, v, why="correction below high confidence"))
                elif new and sorted(new) != sorted(s["roles"]):
                    lists["retier"].append(row(cid, s, v))
                    s["roles"] = new
                    if v.get("scope") and not s.get("scope"):
                        s["scope"] = v["scope"]
                    if "judge" in s and not ({"problemset", "problem"} & set(new)):
                        del s["judge"]
                    touched.add(sid)
                elif new:
                    if v.get("scope") and not s.get("scope"):
                        lists["scope"].append(row(cid, s, v))
                        s["scope"] = v["scope"]
                        touched.add(sid)
                    else:
                        count["correct (nothing to change)"] += 1
                        continue
                elif s["roles"] == ["web"] and ("year-reused" in flags or undated(s["url"])):
                    lists["year-reused"].append(row(cid, s, v, belongs_to=facts.get("belongs_to")))
                else:
                    lists["not-document"].append(row(cid, s, v))
            elif kind == "wrong-contest":
                to = facts.get("belongs_to")
                if "year-reused" in flags or undated(s["url"]):
                    lists["year-reused"].append(row(cid, s, v, belongs_to=to))
                elif not high:
                    lists["review"].append(row(cid, s, v, belongs_to=to, why="wrong contest below high confidence"))
                elif to in contests and to != cid:
                    moves.append((cid, s, v, to))
                else:
                    lists["remove-wrong"].append(row(cid, s, v, belongs_to=to, named=facts.get("contest_named")))
                    c["sources"].remove(s)
                    touched.add(sid)
            elif kind == "not-the-document":
                lists["not-document"].append(row(cid, s, v))
            else:
                lists["review"].append(row(cid, s, v, why=kind))

    for cid, s, v, to in moves:
        sid, c = contests[cid]
        tsid, t = contests[to]
        there = cat.find_source(t, s["url"])
        lists["move"].append(row(cid, s, v, belongs_to=to, already_there=there is not None))
        c["sources"].remove(s)
        touched.add(sid)
        if there is None:
            n = copy.deepcopy(s)
            new = [r for r in (v.get("roles") or []) if r in cat.RANK]
            if new:
                n["roles"] = sorted(new, key=lambda r: cat.RANK[r])
            if v.get("scope"):
                n["scope"] = v["scope"]
            note = f"moved from {cid} by the content check"
            n["note"] = f"{n['note']}; {note}" if n.get("note") else note
            t.setdefault("sources", []).append(cat.normalise_source(n))
            for r in n["roles"]:
                if r in (t.get("none") or []):
                    t["none"].remove(r)
            if t.get("none") == []:
                del t["none"]
            touched.add(tsid)

    for sid in touched:
        for c in series[sid]["contests"]:
            if c.get("sources") == []:
                del c["sources"]
            else:
                cat.sort_sources(c)

    out = run / "lists"
    out.mkdir(exist_ok=True)
    for k, rows in lists.items():
        (out / f"{k}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    for k in ("retier", "scope", "move", "remove-wrong", "year-reused", "not-document", "review"):
        print(f"{k:14} {len(lists[k]):5}")
    for k, n in count.most_common():
        print(f"  {k}: {n}")
    tr = Counter((tuple(r["was"]), tuple(r["roles"])) for r in lists["retier"])
    for (w, n), k in tr.most_common(12):
        print(f"   {k:4} {'+'.join(w)} -> {'+'.join(n)}")
    print("series files touched:", len(touched))
    if a.write:
        for sid in sorted(touched):
            cat.dump_series(sid, series[sid], "content_check_apply.py")
        print("written")


if __name__ == "__main__":
    sys.exit(main())
