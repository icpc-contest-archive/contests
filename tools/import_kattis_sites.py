#!/usr/bin/env python3
"""Problem lists from Kattis contest sites (<site>.kattis.com), the judge the contest ran on.

Input: data/kattis-sites-2026-11-14/sites.json — {site: {contests: {id: {name, problems: [[letter,
kattis id, title]]}}}}, read from the public /contests/<id>/problems pages of the sites in the list
of Kattis contest sites Fredrik supplied 2026-11-14. PLAN maps a Kattis contest to a catalogue contest.

For each planned contest:
  - a set with no problems is filled from the list (letters, Kattis links, count);
  - a set whose names are all in the list gets the missing problems, the letters it lacks, and the
    count of the list (the contest's own judge page outranks a count taken from a mirror);
  - a set that already has every name gets letters and Kattis links where it had none.
A contest with two division lists (D1, D2) gets the union of both, without letters: how divisions
are stored is not decided. Anything that does not fit is reported and left alone.

    python3 tools/import_kattis_sites.py [--dry-run]
"""
import json, re, sys, unicodedata, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

M = {"naq": "naq", "ncna": "ncna", "rmc": "rmc", "ecna": "ecna", "mcpc": "mcpc", "mausa": "mausa", "scusa": "scusa", "nena": "nena",
     "naeast": "east-na", "nasouth": "south-na", "acpc": "alberta", "ncpc": "nordic", "ukiepc": "ukiepc", "asiasg": "singapore",
     "asiahk": "hong-kong", "vietnam-national": "vietnam-national", "nac": "nac", "naipc": "naipc", "hanoi": "vietnam",
     "hochiminh": "vietnam", "danang": "vietnam", "cantho": "vietnam", "atlantic-canada": "nena-atlantic"}
SKIP = re.compile(r"practice|hidden|\bopen\b|\btest|warm-?up|dress|rehears|spring|fall|sunday", re.I)


def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def main() -> int:
    dry = "--dry-run" in sys.argv
    sites = json.loads((ROOT / "data" / "kattis-sites-2026-11-14" / "sites.json").read_text())
    series = load_series(); sets = load_sets(); where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    plan = collections.defaultdict(list)   # contest -> [(site, kattis contest, problems)]
    for site, v in sorted(sites.items()):
        m = re.match(r"^(.*?)-?(\d\d)(?:-?d[12])?$", site)
        if not m or m.group(1) not in M: continue
        cid = f"{M[m.group(1)]}-20{m.group(2)}"
        for kc, x in sorted(v["contests"].items()):
            pr = x.get("problems") or []
            if len(pr) < 5 or SKIP.search(kc + " " + (x.get("name") or "")) or not re.search(m.group(2), kc): continue
            if any(k == kc for _s, k, _p in plan[cid]): continue
            plan[cid].append((site, kc, pr))
    rep = collections.defaultdict(list); changed = set(); touched = set(); made = let = links = 0
    for cid, lists in sorted(plan.items()):
        if cid not in where:
            rep["contest not in the catalogue"].append(f"{cid}: " + ", ".join(f"{s}/{k} ({len(p)})" for s, k, p in lists)); continue
        ser, c = where[cid]
        if c.get("status") == "upcoming":
            rep["contest marked upcoming"].append(f"{cid}: " + ", ".join(f"{s}/{k} ({len(p)})" for s, k, p in lists)); continue
        divs = len(lists) > 1
        union = {}
        for _s, _k, pr in lists:
            for l, kid, t in pr: union.setdefault(norm(t), (l, kid, t))
        s = sets.get((c.get("problems") or {}).get("set"))
        if s is not None and len(s["contests"]) > 1 and s.get("problems"):
            mine = {norm(p["name"]) for p in s["problems"]}
            if not set(union) <= mine:
                rep["shared set does not hold the whole Kattis list (left alone)"].append(f"{cid} in {s['id']}: {len(set(union) - mine)} of {len(union)} not there"); continue
        if s is None:
            s = sets[cid] = {"id": cid, "contests": [{"contest": cid}], "problems": [], "provenance": []}
            c["problems"] = {"set": cid}; touched.add(ser)
        probs = s.setdefault("problems", []); have = {norm(p["name"]): p for p in probs}
        if not set(have) <= set(union):
            rep["set has names the Kattis list lacks (left alone)"].append(
                f"{cid}: " + " | ".join(p["name"] for k, p in have.items() if k not in union)[:200] + f"  [Kattis: {', '.join(k for _s, k, _p in lists)}]"); continue
        total = len(set(have) | set(union))
        if s.get("count") and total != s["count"] and (divs or any(k in s for k in ("statement", "data", "repo"))):
            rep["count disagrees (left alone)"].append(f"{cid}: set count {s['count']}, Kattis gives {total}" + (" over two divisions" if divs else "")); continue
        e = next(e for e in s["contests"] if e["contest"] == cid); before = (len(probs), json.dumps(e.get("letters")))
        for k, (l, kid, t) in union.items():
            p = have.get(k)
            if p is None:
                p = {"id": pid(None, s["id"], None if divs else l, t), "name": t}; probs.append(p); have[k] = p; made += 1
            if not any(j["judge"] == "kattis" for j in p.get("judges") or []):
                p.setdefault("judges", []).append({"judge": "kattis", "url": f"https://open.kattis.com/problems/{kid}", "id": kid}); links += 1
        if not divs:
            lm = {l: have[norm(t)]["id"] for l, _kid, t in lists[0][2]}
            if e.get("letters") != lm:
                if isinstance(e.get("letters"), dict) and any(lm.get(k) != v for k, v in e["letters"].items()):
                    rep["letters disagree with Kattis (kept as they were)"].append(cid)
                else:
                    e["letters"] = lm; let += 1; s.pop("letters", None) if s.get("letters") == "unknown" else None
            if len(s["contests"]) == 1: s["count"] = len(probs)
        else:
            if not any(isinstance(x.get("letters"), dict) for x in s["contests"]): s["letters"] = "unknown"
            if not s.get("count"): s["count"] = len(probs)
        if (len(probs), json.dumps(e.get("letters"))) != before or cid in changed or True:
            src = ", ".join(f"https://{st}.kattis.com/contests/{k}/problems" for st, k, _p in lists)
            note = f"problem list of the contest's Kattis site ({src}), read 2026-11-14" + ("; two division lists, united" if divs else "") + " (tools/import_kattis_sites.py)"
            if (len(probs), json.dumps(e.get("letters"))) != before:
                s.setdefault("provenance", []).append(note); changed.add(s["id"])
                rep["updated"].append(f"{cid}: {before[0]} -> {len(probs)} problems" + (" (two divisions)" if divs else ""))
            elif s["id"] not in changed and any(True for _ in ()): pass
    # judge links alone also count as a change
    if not dry:
        for sid, s in sets.items():
            f = ROOT / "problemsets" / f"{sid}.yaml"; new = dump(s)
            if (sid in changed or sid in {where[c][1].get("problems", {}).get("set") for c in plan if c in where}) and (not f.exists() or f.read_text() != new):
                f.write_text(new)
        for ser in touched: dump_series(ser, series[ser], "import_kattis_sites.py (2026-11-14)")
        lines = ["# Kattis contest sites — 2026-11-14", "", "Generated by `tools/import_kattis_sites.py`.", "",
                 f"- problems created: {made}", f"- contests given letters: {let}", f"- Kattis links added: {links}", ""]
        for k in sorted(rep, key=lambda k: (k != "updated", k)):
            lines += [f"## {k} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
        (ROOT / "reports" / "kattis-sites-2026-11-14.md").write_text("\n".join(lines))
    print({k: len(v) for k, v in rep.items()}, "made", made, "letters", let, "links", links)
    for k, v in rep.items():
        if k != "updated": print(k); [print("   ", x[:230]) for x in v]
    print("updated:", "; ".join(rep["updated"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
