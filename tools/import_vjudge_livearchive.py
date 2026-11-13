#!/usr/bin/env python3
"""Import ICPC Live Archive problem lists as mirrored by vjudge.net (OJ "UVALive").

Input: a harvest file {"UVALive": {"<number>": ["<title>", "Regionals 2012 >> Asia - Jakarta"]}, ...}
(the vjudge problem list, read with a signed-in browser session; the Live Archive itself is gone).
Each Live Archive source ("Regionals <year> >> <region> - <site>", "World Finals >> <year> - <city>")
is mapped to a catalogue contest by SITES below.

  contest's set lists no problems  -> the problems are created (no letters: the archive numbers
                                      problems, it does not letter them), count = the archive's
                                      count unless the set has one; a larger archive list than
                                      the set's count is held back
  set already lists problems       -> a livearchive judge link is added to problems whose
                                      title matches and that have none
  source maps to no contest        -> reported (catalogue gap or mapping to rule on)

usage: import_vjudge_livearchive.py <harvest.json> --date YYYY-MM-DD [--dry-run]
"""
from __future__ import annotations
import argparse, collections, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import dump_set, norm_title, pid  # noqa: E402

LA_URL = "https://onlinejudge.org/index.php?option=com_onlinejudge&Itemid=8&page=show_problem&problem={n}"
SITES = {  # Live Archive site -> series (contest id = <series>-<year>)
    "Africa/Middle East - South Africa": "south-africa", "Africa/Middle East - South African": "south-africa",
    "Africa/Middle East - Africa and Arab": "acpc", "Africa/Middle East - Arab and North Africa": "acpc",
    "Africa/Middle East - Arab Contest": "acpc",
    "South Pacific": "south-pacific",
    "North America - Southeast USA": "seusa", "North America - Mid-Central USA": "mcpc",
    "North America - Northeast NA": "nena", "North America - Rocky Mountain": "rmc",
    "North America - Greater NY": "gny", "North America - East Central NA": "ecna",
    "North America - Mid-Atlantic USA": "mausa", "North America - North Central NA": "ncna",
    "North America - Pacific Northwest": "pacnw", "North America - South Central USA": "scusa",
    "North America - Southern California": "socal",
    "Latin America - Mexico and Central America": "central-america", "Latin America - South America": "south-america",
    "Latin America": "latam",
    "Europe - Southeastern": "seerc", "Europe - Central": "cerc", "Europe - Mid-Central": "mcerc",
    "Europe - Northwestern": "nwerc", "Europe - Northeastern": "neerc", "Europe - Northeastern-Eurasia": "neerc",
    "Europe - Southwestern": "swerc",
    "Asia - Shanghai": "shanghai", "Asia - Hong Kong": "hong-kong", "Asia - Tehran": "tehran",
    "Asia - Seoul-Taejon": "korea", "Asia - Taejon": "korea", "Asia - Seoul": "korea", "Asia - Daejeon": "korea",
    "Asia - Tsukuba": "japan", "Asia - Hakodate": "japan", "Asia - Kanazawa": "japan", "Asia - Aizu": "japan",
    "Asia - Ehime": "japan", "Asia - Tokyo": "japan", "Asia - Yokohama": "japan", "Asia - Fukuoka": "japan",
    "Asia - Taipei": "taiwan", "Asia - Kaohsiung": "taiwan", "Asia - Hsinchu": "taiwan", "Asia - Chia-Yi": "taiwan",
    "Asia - Taichung": "taiwan", "Asia - Chung-Li": "taiwan", "Asia - Hua-Lien": "taiwan",
    "Asia - Hanoi": "vietnam", "Asia - Danang": "vietnam", "Asia - Ho-Chi-Minh-City": "vietnam",
    "Asia - Ho-Chi-Minh City Site": "vietnam", "Asia - Nha Trang": "vietnam",
    "Asia - Phuket": "thailand", "Asia - Hatyai": "thailand", "Asia - Bangkok": "thailand",
    "Asia - Nakhon Pathom Site": "thailand",
    "Asia - Dhaka": "dhaka", "Asia - Singapore": "singapore", "Asia - Kanpur": "kanpur", "Asia - Manila": "manila",
    "Asia - Beijing": "beijing", "Asia - Xian": "xian", "Asia - Kolkata-Roorkee": "kolkata-roorkee",
    "Asia - Guangzhou": "guangzhou", "Asia - Bombay": "bombay", "Asia - Kolkata": "kolkata",
    "Asia - ChengDu": "chengdu", "Asia - Chengdu": "chengdu", "Asia - Hangzhou": "hangzhou",
    "Asia - Coimbatore": "coimbatore", "Asia - Nanjing": "nanjing", "Asia - Amritapuri": "amritapuri",
    "Asia - Changchun": "changchun", "Asia - Jakarta": "jakarta", "Asia - Hefei": "hefei", "Asia - Harbin": "harbin",
    "Asia - Kuala Lumpur": "kuala-lumpur", "Asia - Gwalior-Kanpur": "gwalior-kanpur", "Asia - Wuhan": "wuhan",
    "Asia - Ningbo": "ningbo", "Asia - Tianjin": "tianjin", "Asia - Fuzhou": "fuzhou", "Asia - Dalian": "dalian",
    "Asia - Kharagpur": "kharagpur", "Asia - Jinhua": "jinhua", "Asia - Changsha": "changsha",
    "Asia - Mudanjiang": "mudanjiang", "Asia - Gwalior": "gwalior", "Asia - Gwalior Site": "gwalior",
    "Asia - Anshan": "anshan", "Asia - Lahore": "pakistan", "Asia - Shenyang": "shenyang",
    "Asia - EC Final": "aec", "Asia - China Final": "aec", "Asia - East Continent League Finals": "aec",
    "Asia - Chennai": "chennai", "Asia - QingDao": "qingdao", "Asia - Yangon": "yangon",
    "Asia - India Final": "india", "Asia - Pyongyang": "pyongyang", "Asia - Kabul": "kabul",
    "Asia - Nanning": "nanning", "Asia - Kolkata-Kanpur Site": "kolkata-kanpur", "Asai - Urumqi": "urumqi",
}

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("harvest"); ap.add_argument("--date", required=True)
    ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
    la = json.loads(Path(a.harvest).read_text())["UVALive"]
    groups = collections.defaultdict(list)
    for num, (title, src) in la.items():
        groups[re.sub(r"\s+", " ", src).strip()].append((int(num), title.strip()))
    series = load_series(); sets = load_sets()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    rep = collections.defaultdict(list); changed = set(); touched = set(); nnew = nlink = 0
    for src, probs in sorted(groups.items()):
        probs.sort(); line = f"{src}: {len(probs)} problems ({probs[0][0]}–{probs[-1][0]})"
        m = re.match(r"Regionals (\d{4}) >> (.+)$", src); w = re.match(r"World Finals >> (\d{4}) - ", src)
        if w: cid = f"wf-{w.group(1)}"
        elif m and m.group(2) in SITES:
            cid = f"{SITES[m.group(2)]}-{m.group(1)}"
            if cid.startswith("neerc-") and int(m.group(1)) >= 2017: cid = "nerc-" + m.group(1)  # NEERC renamed NERC in 2017
        else:
            rep["source with no mapping rule"].append(line); continue
        setid = None
        if cid.startswith("latam-"):
            setid = cid if cid in sets else None
            if not setid: rep["no latam set for that year"].append(line); continue
            s = sets[setid]
        else:
            if cid not in where:
                rep["mapped contest not in the catalogue"].append(f"{cid} <- {line}"); continue
            ser, c = where[cid]
            if c.get("status") == "upcoming": continue
            setid = (c.get("problems") or {}).get("set")
            if setid and setid in sets: s = sets[setid]
            elif cid in sets:
                rep["set id taken (skipped)"].append(f"{cid} <- {line}"); continue
            else:
                setid = cid; s = sets[setid] = {"id": setid, "contests": [{"contest": cid}], "provenance": []}
                c["problems"] = {"set": setid}; touched.add(ser)
        link = lambda n: {"judge": "livearchive", "url": LA_URL.format(n=n - 1999), "id": str(n)}
        if s.get("problems"):
            by = collections.defaultdict(list)
            for p in s["problems"]: by[norm_title(p["name"])].append(p)
            got = 0
            for n, t in probs:
                ps = by.get(norm_title(t)) or []
                if len(ps) == 1 and not any(j["judge"] == "livearchive" for j in ps[0].get("judges") or []):
                    ps[0].setdefault("judges", []).append(link(n)); got += 1
            if got:
                nlink += got; changed.add(setid); rep["judge links added to listed problems"].append(f"{cid}: {got} of {len(probs)}")
            continue
        if s.get("count") and len(probs) > s["count"]:
            rep["held back: archive lists more problems than the set's count"].append(f"{cid} (count {s['count']}) <- {line}"); continue
        if len({norm_title(t) for _, t in probs}) != len(probs):
            rep["held back: repeated titles"].append(f"{cid} <- {line}"); continue
        if s.get("count") and len(probs) < s["count"]: s["complete"] = False
        elif not s.get("count"): s["count"] = len(probs)
        s["problems"] = [{"id": pid(None, setid, None, t), "name": t, "judges": [link(n)]} for n, t in probs]
        if not any("letters" in e for e in s["contests"]): s["letters"] = "unknown"
        s.setdefault("provenance", []).append(
            f"problem list from the ICPC Live Archive category '{src}' as mirrored by vjudge.net (UVALive), "
            f"read {a.date}; the archive numbers problems, letters not known (tools/import_vjudge_livearchive.py)")
        nnew += len(probs); changed.add(setid); rep["problems created"].append(f"{cid}: {len(probs)} <- {src}")
    if not a.dry_run:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump_set(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], f"import_vjudge_livearchive.py ({a.date})")
        lines = [f"# Live Archive problem lists via vjudge — {a.date}", "", f"- problems created: {nnew}", f"- judge links added: {nlink}", ""]
        for k in sorted(rep): lines += [f"## {k} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
        (ROOT / "reports" / f"vjudge-livearchive-{a.date}.md").write_text("\n".join(lines))
    print({k: len(v) for k, v in rep.items()}, "new", nnew, "links", nlink)
    return 0

if __name__ == "__main__":
    sys.exit(main())
