#!/usr/bin/env python3
"""Apply Fredrik's 2026-11-13 rulings on the problem hunt, and the classifier matches that are ready.

  1. source removed: the Northern Subregional 2016 statements are north-russia-2016's only (off
     taurida-2016; urals-2016 never had it: its own statement is sp.urfu.ru/qf/2016/problems-ekb.pdf); the SoCal 2024-2025 problem set is socal-2024's only (off socal-2025).
  2. South Pacific divisional contests share one set (2016, 2018, 2019): shared set
     south-pacific-divisions-<year>, problems read from the common statement PDF.
  3. socal-2024: problems from its statement (was held as a duplicate of socal-2025).
  4. rmc-2001: 9 problems (numbered 0-8), not 8; list from the Live Archive.
  5. gyms named for one contest: tunisia-2022 (gym 105020), greece-2025 (gym 106151).
  6. classifier matches (reports: _hunt/problems-2026-11-13/agents-out/): gap contests with a
     high-confidence single-contest source on POJ / HDU / Timus / QOJ / Codeforces gym.

usage: apply_rulings_2026_11_13.py <harvest.json> <title-candidates.json> <categorized.json> [--dry-run]
"""
from __future__ import annotations
import collections, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, add_source, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import dump_set, pid  # noqa: E402

DATE = "2026-11-13"
TOOL = "apply_rulings_2026_11_13.py"
REMOVE = {"taurida-2016": "north-2016-statements.pdf",
          "socal-2025": "SCICPC-2024-2025-ProblemSet.pdf"}
SP = {y: [f"south-pacific-{d}-{y}" for d in ("central", "east", "west")] for y in (2016, 2018, 2019)}
READY = {**{f"far-east-russia-{y}": "poj" for y in range(2000, 2007)}, **{f"west-neerc-{y}": "poj" for y in range(2001, 2006)},
         "urals-2006": "ural", "urals-2007": "ural", "urals-2008": "ural", "central-russia-2002": "ural",
         "aec-2023": "qoj", "aec-2024": "qoj", "aec-2025": "qoj", "xian-2026": "qoj", "poland-2025": "qoj",
         "moscow-2018": "qoj", "gny-2022": "qoj", "bapc-2006": "poj", "bapc-2007": "hdu", "bapc-2026": "gym",
         "alberta-2003": "poj", "ctuo-1999": "poj", "syria-2011": "hdu", "greece-2026": "gym", "cyprus-2026": "gym"}
OJ = {"poj": ("POJ", "poj", "http://poj.org/problem?id={}"), "hdu": ("HDU", "hdu", "https://acm.hdu.edu.cn/showproblem.php?pid={}"),
      "ural": ("URAL", "timus", "https://acm.timus.ru/problem.aspx?space=1&num={}"), "qoj": ("QOJ", "qoj", "https://qoj.ac/problem/{}")}

def main() -> int:
    dry = "--dry-run" in sys.argv
    harvest = json.loads(Path(sys.argv[1]).read_text()); cands = json.loads(Path(sys.argv[2]).read_text())
    rows = json.loads(Path(sys.argv[3]).read_text())
    series = load_series(); sets = load_sets()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    rep = collections.defaultdict(list); changed = set(); touched = set(); total = 0

    def open_set(sid, members):
        s = sets.get(sid)
        if s is None:
            s = sets[sid] = {"id": sid, "contests": [], "provenance": []}
        for cid in members:
            if not any(e["contest"] == cid for e in s["contests"]): s["contests"].append({"contest": cid})
            ser, c = where[cid]
            if (c.get("problems") or {}).get("set") != sid:
                c["problems"] = {"set": sid}; touched.add(ser)
        return s

    def fill(sid, members, probs, prov, letters=True, count=None):
        """probs: [(letter or None, name, judge link or None)]"""
        nonlocal total
        for cid in members:
            old = (where[cid][1].get("problems") or {}).get("set")
            if old and old != sid and (sets.get(old) or {}).get("problems"):
                rep["skipped: contest already has a listed set"].append(f"{cid} ({old})"); return False
        s = open_set(sid, members)
        if s.get("problems"):
            rep["skipped: set already lists problems"].append(sid); return False
        out = []; lm = {}
        for L, name, link in probs:
            p = {"id": pid(None, sid, L if letters else None, name), "name": name}
            if link: p["judges"] = [link]
            out.append(p)
            if letters and L: lm[L] = p["id"]
        if len({p["id"] for p in out}) != len(out):
            rep["skipped: repeated titles"].append(sid); return False
        s["problems"] = out; s["count"] = count or len(out)
        if lm:
            for e in s["contests"]:
                if e["contest"] in members: e["letters"] = dict(lm)
            if s.get("letters") == "unknown": del s["letters"]
        elif not any(e.get("letters") for e in s["contests"]): s["letters"] = "unknown"
        s.setdefault("provenance", []).append(prov + f" ({TOOL}, {DATE})")
        changed.add(sid); total += len(out)
        rep["problems listed"].append(f"{sid} ({', '.join(members)}): {len(out)}")
        return True

    # 1. sources removed
    for cid, frag in REMOVE.items():
        ser, c = where[cid]; before = len(c.get("sources") or [])
        gone = [s["url"] for s in c.get("sources") or [] if frag in s["url"]]
        c["sources"] = [s for s in c.get("sources") or [] if frag not in s["url"]]
        if gone: touched.add(ser); rep["source removed (ruling)"].append(f"{cid}: {', '.join(gone)}")
    # 2. South Pacific divisional shared sets
    for y, members in SP.items():
        v = cands.get(members[0])
        if not v or any(cands.get(m, {}).get("problems") != v["problems"] for m in members):
            rep["skipped: south pacific lists differ"].append(str(y)); continue
        s = fill(f"south-pacific-divisions-{y}", members, [(p["letter"], p["name"], None) for p in v["problems"]],
                 f"shared set of the South Pacific divisional contests {y}; problem names read from the common statement {v['url']} "
                 f"(capture {v['path']}); ruling {DATE}: the divisions share one problem set")
        if s: sets[f"south-pacific-divisions-{y}"]["name"] = f"South Pacific divisional contests {y}"
    # 3. socal-2024
    v = cands["socal-2024"]
    fill("socal-2024", ["socal-2024"], [(p["letter"], p["name"], None) for p in v["problems"]],
         f"problem names read from the published statement {v['url']} (capture {v['path']})")
    # 4. rmc-2001
    la = sorted((int(k), t.strip()) for k, (t, src) in harvest["UVALive"].items() if re.sub(r"\s+", " ", src).strip() == "Regionals 2001 >> North America - Rocky Mountain")
    sid = (where["rmc-2001"][1].get("problems") or {}).get("set") or "rmc-2001"
    fill(sid, ["rmc-2001"], [(None, t, {"judge": "livearchive", "url": f"https://onlinejudge.org/index.php?option=com_onlinejudge&Itemid=8&page=show_problem&problem={n - 1999}", "id": str(n)}) for n, t in la],
         "problem list from the ICPC Live Archive category 'Regionals 2001 >> North America - Rocky Mountain' as mirrored by vjudge.net; "
         "count corrected from 8 to 9 (the contest numbered its problems 0-8; ruling)", letters=False, count=len(la))
    # gyms
    gyms = collections.defaultdict(dict); gname = {}
    for k, (t, src) in harvest["Gym"].items():
        m = re.match(r"(\d{6})([A-Z]\d?|\d+)$", k)
        if m: gyms[m.group(1)][m.group(2)] = t.strip(); gname[m.group(1)] = src
    def gym_fill(sid, members, g, extra=""):
        probs = [(L, t, {"judge": "codeforces", "url": f"https://codeforces.com/gym/{g}/problem/{L}", "id": f"{g}/{L}"})
                 for L, t in sorted(gyms[g].items(), key=lambda x: (len(x[0]), x[0]))]
        ok = fill(sid, members, probs, f"problem list from Codeforces gym {g} ('{gname[g]}') as mirrored by vjudge.net{extra}")
        if ok:
            for cid in members:
                ser, c = where[cid]
                if not any(f"/gym/{g}" in s["url"] for s in c.get("sources") or []):
                    add_source(c, f"https://codeforces.com/gym/{g}", "judge_page", judge="codeforces", note=f"{gname[g]} (problem hunt {DATE})"); touched.add(ser)
    # 5.
    gym_fill("tunisia-2022", ["tunisia-2022"], "105020", "; the gym is named for the 2022 contest")
    gym_fill("greece-2025", ["greece-2025"], "106151", "; the gym is named for the Greek contest")
    # 6. classifier matches
    by = collections.defaultdict(list)
    for r in rows:
        if r.get("category") == "catalogue-contest" and r.get("confidence") == "high":
            for c in r.get("contests") or []: by[c].append(r)
    done_pair = False
    for cid, oj in sorted(READY.items()):
        rs = [r for r in by.get(cid, []) if r["slice"].split("-")[0] == oj]
        if not rs: rep["ready contest without a matching row"].append(cid); continue
        members = sorted({c for r in rs for c in r["contests"]})
        if members != [cid] and members != ["cyprus-2026", "greece-2026"]:
            rep["skipped: rows name other contests too"].append(f"{cid}: {members}"); continue
        if oj == "gym":
            if members == ["cyprus-2026", "greece-2026"]:
                if done_pair: continue
                done_pair = True
                if gym_fill("cyprus-greece-2026", members, rs[0]["key"], "; one joint contest for both countries"):
                    sets["cyprus-greece-2026"]["name"] = "Greece and Cyprus Collegiate Programming Contest 2026"
            else: gym_fill(cid, [cid], rs[0]["key"])
            continue
        hname, judge, url = OJ[oj]; keys = {r["key"] for r in rs}
        items = sorted(((k, t.strip()) for k, (t, src) in harvest[hname].items() if src[:300] in keys),
                       key=lambda x: (len(x[0]), x[0]))
        if not 5 <= len(items) <= 16:
            rep["skipped: implausible problem count"].append(f"{cid}: {len(items)}"); continue
        fill((where[cid][1].get("problems") or {}).get("set") or cid, [cid],
             [(None, t, {"judge": judge, "url": url.format(k), "id": k}) for k, t in items],
             f"problem list from {hname} problems {items[0][0]}–{items[-1][0]} (source '{rs[0]['source'][:120]}') as mirrored by vjudge.net; "
             f"contest identified by the harvest classification; letters not known", letters=False)
    if not dry:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump_set(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], f"{TOOL} ({DATE})")
        lines = [f"# Rulings and classifier matches applied — {DATE}", "", f"- problems listed: {total}", ""]
        for k in sorted(rep): lines += [f"## {k} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
        (ROOT / "reports" / f"problem-hunt-rulings-{DATE}.md").write_text("\n".join(lines))
    for k, v in rep.items(): print(k, len(v), v if not k.startswith("problems listed") else "")
    print("total", total)
    return 0

if __name__ == "__main__":
    sys.exit(main())
