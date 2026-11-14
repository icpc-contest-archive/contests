#!/usr/bin/env python3
"""Problem lists, letters, QOJ links and editorials from icpcarchive.github.io.

icpcarchive.github.io (an unofficial archive) was rebuilt in 2026 as a copy of QOJ's ICPC category:
one folder per QOJ contest with problems.json (QOJ contest id, and per problem its letter, QOJ
problem id and title), statements_en.pdf and, for some, tutorials_en.pdf. QOJ's own contest pages
need a login, so this is how the letter-by-letter lists are read. data/icpcarchive-2026-11-14/
contests.json is the 505 problems.json files as fetched 2026-11-14.

A folder is tied to a catalogue contest by the QOJ contest address the contest already has as a
source. Then, for the contest's set:
  - no problems: the list is recorded (letters, QOJ links, count);
  - every name it has is in the list: the missing problems are added (not when the set states
    another count), letters are filled in where the contest had none, QOJ links are added;
  - otherwise only QOJ links are added, to problems whose title is in the list.
tutorials_en.pdf becomes an `editorial` source of the contest. Letters already recorded are never
changed; disagreements are reported.

    python3 tools/import_icpcarchive.py [--dry-run]
"""
import collections, json, re, sys, unicodedata, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, add_source, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402


def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def main() -> int:
    dry = "--dry-run" in sys.argv
    data = json.loads((ROOT / "data" / "icpcarchive-2026-11-14" / "contests.json").read_text())
    series = load_series(); sets = load_sets(); byq = collections.defaultdict(list); where = {}
    for ser, d in series.items():
        for c in d["contests"]:
            where[c["id"]] = (ser, c)
            for s in c.get("sources") or []:
                m = re.search(r"qoj\.ac/contest/(\d+)", s["url"])
                if m and c["id"] not in byq[m.group(1)]: byq[m.group(1)].append(c["id"])
    rep = collections.defaultdict(list); changed = set(); touched = set(); made = links = lets = eds = 0
    for folder, v in sorted(data.items()):
        q = str(v["qoj"]); pr = [(l, i, t.strip()) for l, i, t in v["problems"] if t]
        cids = byq.get(q)
        if not cids:
            rep["QOJ contest is not a source of any catalogue contest"].append(f"{v['name']} (qoj {q}, {len(pr)} problems)"); continue
        if len({norm(t) for _l, _i, t in pr}) != len(pr) or not pr:
            rep["list has repeated or no titles (left alone)"].append(f"{v['name']} (qoj {q})"); continue
        for cid in cids:
            ser, c = where[cid]
            if v["tutorial"] and add_source(c, "https://icpcarchive.github.io/" + urllib.parse.quote(folder) + "/tutorials_en.pdf", "editorial")[1]:
                touched.add(ser); eds += 1
            if c.get("status") == "upcoming": continue
            s = sets.get((c.get("problems") or {}).get("set"))
            if s is None and len(cids) > 1:
                rep["QOJ contest is a source of several contests, none with a list (left alone)"].append(f"{cid} <- {v['name']} (qoj {q})"); continue
            if s is None:
                if cid in sets: rep["set id taken (left alone)"].append(cid); continue
                s = sets[cid] = {"id": cid, "contests": [{"contest": cid}], "problems": [], "provenance": []}
                c["problems"] = {"set": cid}; touched.add(ser)
            probs = s.setdefault("problems", []); have = {norm(p["name"]): p for p in probs}; lst = {norm(t) for _l, _i, t in pr}
            e = next((e for e in s["contests"] if e["contest"] == cid), None)
            if e is None: rep["contest not a member of its set (left alone)"].append(cid); continue
            n0 = len(probs); grow = set(have) <= lst and len(cids) == 1
            if grow and probs and s.get("count") and s["count"] != len(pr): grow = False; rep["count disagrees: links only"].append(f"{cid}: count {s['count']}, list {len(pr)}")
            if not grow and len(set(have) & lst) < 0.6 * min(len(have), len(lst)):
                rep["few titles in common (left alone)"].append(f"{cid} <- {v['name']} (qoj {q}): {len(set(have) & lst)} of {len(lst)}"); continue
            touchedset = False
            for l, i, t in pr:
                p = have.get(norm(t))
                if p is None:
                    if not grow: continue
                    p = {"id": pid(None, s["id"], l, t), "name": t}
                    if p["id"] in {x["id"] for x in probs}: continue
                    probs.append(p); have[norm(t)] = p; made += 1; touchedset = True
                if not any(j["judge"] == "qoj" for j in p.get("judges") or []):
                    p.setdefault("judges", []).append({"judge": "qoj", "url": f"https://qoj.ac/problem/{i}", "id": str(i)}); links += 1; touchedset = True
            lm = {l: have[norm(t)]["id"] for l, _i, t in pr if l and norm(t) in have}
            if len(cids) == 1 and lm and len(lm) == len([1 for l, _i, _t in pr if l]):
                old = e.get("letters") if isinstance(e.get("letters"), dict) else None
                if old is None:
                    e["letters"] = lm; lets += 1; touchedset = True
                    if s.get("letters") == "unknown": del s["letters"]
                elif any(lm.get(k) not in (None, x) for k, x in old.items()):
                    rep["letters disagree with the list (kept as they were)"].append(cid)
                elif len(old) < len(lm):
                    e["letters"] = lm; touchedset = True
            if grow and len(s["contests"]) == 1 and not any(k in s for k in ("statement", "data")) and len(probs) == len(pr): s["count"] = len(pr)
            if touchedset:
                if len(probs) != n0 or n0 == 0:
                    s.setdefault("provenance", []).append(f"problem list of QOJ contest {q} as copied by icpcarchive.github.io ({folder}/problems.json), read 2026-11-14 (tools/import_icpcarchive.py)")
                    rep["problems added"].append(f"{cid}: {n0} -> {len(probs)}")
                changed.add(s["id"])
    if not dry:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], "import_icpcarchive.py (2026-11-14)")
        lines = ["# icpcarchive.github.io (a copy of QOJ's ICPC category) — 2026-11-14", "", "Generated by `tools/import_icpcarchive.py`.", "",
                 f"- problems created: {made}", f"- QOJ links added: {links}", f"- contests given letters: {lets}", f"- editorial sources added: {eds}", ""]
        for k in sorted(rep):
            lines += [f"## {k} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
        (ROOT / "reports" / "icpcarchive-2026-11-14.md").write_text("\n".join(lines))
    print({k: len(x) for k, x in rep.items()}, "made", made, "links", links, "letters", lets, "editorials", eds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
