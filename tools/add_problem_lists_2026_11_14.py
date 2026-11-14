#!/usr/bin/env python3
"""Problem lists found in the 2026-11-14 judge sweep (reports/judge-sweep-2026-11-14.md) for
contests whose set had no problems, or fewer than the contest had.

Each entry names one source group on one judge (as vjudge.net lists it) that carries the
contest's name, so the assignment is by the judge's own source string, not by title. Problems
already in the set (same title, or listed in `same`) only gain the judge link; the rest are
created. Judges that have closed (FZU, HIT, CSU, HRBUST, HUST's old archive) and KRSU, whose
address could not be opened, give names only. Letters are recorded only where the judge shows
them. A new set gets no count: nothing says the judge has every problem.

    python3 tools/add_problem_lists_2026_11_14.py [--dry-run]
"""
import json, re, sys, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import URL, dump  # noqa: E402

URL = dict(URL, sgu="https://codeforces.com/problemsets/acmsguru/problem/99999/{id}")
HR = "2014-icpc-north-central-regional-north-america-practice"
# (set, judge or None, source string on the judge, "id~title ; ...", {judge title: existing name})
LISTS = [
 ("south-russia-2002", "sgu", "5th Southern Subregional Contest. Saratov 2002",
  "123~The sum ; 124~Broken line ; 125~Shtirlits ; 126~Boxes ; 127~Telephone directory ; 128~Snake ; 129~Inheritance ; 130~Circle ; 131~Hardwood floor", {}),
 ("south-russia-2003", "sgu", "ACM International Collegiate Programming Contest 2003-2004 North-Eastern European Region, Southern Subregion",
  "183~Painting the balls ; 184~Patties ; 185~Two shortest ; 186~The Chain ; 187~Twist and whirl - want to cheat ; 188~Factory guard ; 190~Dominoes ; 191~Exhibition ; 192~RGB", {}),
 ("south-russia-2004", "sgu", "ACM ICPC 2004-2005, NEERC, Southern Subregional Contest",
  "266~Berlion ; 267~Optimist vs. Pessimist ; 268~Hyper Almost Permutative String ; 269~Rooks ; 270~Thimbles ; 271~Book Pile ; 272~Evacuation plan ; 273~Game Po ; 274~Spam-filter ; 275~To xor or not to xor ; 276~Andrew's Troubles", {}),
 ("north-russia-2002", "sgu", "ACM ICPC 2002-2003 NEERC, Northern Subregion",
  "155~Cartesian Tree ; 156~Strange Graph ; 157~Patience ; 158~Commuter Train ; 159~Self-Replicating Numbers ; 160~Magic Multiplying Machine ; 161~Intuitionistic Logic ; 162~Pyramids ; 163~Wise King",
  {"Wise King": "The King"}),
 ("kyrgyzstan-2005", None, "KRSU (olymp.krsu.kg): ACM ICPC Kyrgyzstan Subregional 2005",
  "34~Alcatel ; 35~Вечеринка ; 36~Турнир ; 37~Опять Фибоначчи ; 38~Сдача ; 39~Архиватор ; 40~Сегменты ; 41~Размер стека", {}),
 ("wf-1995", "bailian", "World Finals 1995",
  "1878~Jill's Bike ; 1879~Tempus et mobilius Time and motion ; 1880~Variable Radix Huffman Encoding ; 1881~Sail Race ; 1882~Stamps ; 1883~Theseus and the Minotaur ; 1884~Train Time ; 1885~Uncompress",
  {"Tempus et mobilius Time and motion": "Tempus et Mobilius"}),
 ("beijing-2004", None, "FZU (closed): 2004 ACM/ICPC Beijing",
  "1180~Finding Nemo ; 1181~Searching the Web ; 1182~Argus ; 1183~Fun Game ; 1184~Square ; 1185~Color a Tree ; 1186~Kid's Problem ; 1187~The Separator in Grid ; 1188~The Lost House", {}),
 ("gny-2010", None, "CSU (closed): 2010 ACM ICPC Greater New York Region",
  "1130~Penney Game ; 1131~Nim-B Sum ; 1132~Just The Simple Fax ; 1133~Show Me The Fax ; 1134~Non-Decreasing Digits ; 1135~I^2C ; 1136~Old Fashioned Typesetting ; 1137~Scanning UPC Barcodes ; 1138~Cutting the Cake",
  {"I^2C": "I²C"}),
 ("gny-2003", None, "HIT (closed): ACM ICPC Greater New York 2003",
  "1273~Peg Game ; 1274~Taxation With Representation Overdone ; 1275~It's Logical ; 1276~Obstructed Rook Circuits ; 1277~Rhyme Schemes ; 1278~Fully Diversified Sequences of Sets ; 1279~Exocenter of a Triangle", {}),
 ("mausa-2003", None, "HIT (closed): ACM ICPC Mid-Atlantic USA 2003",
  "1307~Choose Your Words Carefully ; 1308~A Round Peg in a Ground Hole ; 1309~Helping Florida ; 1310~Three Sides Make a Triangle ; 1312~Reverse Roman Notation", {}),
 ("gny-2007", None, "HUST (hustoj.org): Greater New York Regional",
  "A~Mispelling4 ; B~Conversions ; C~Encoding ; E~Flipping Burned Pancakes ; F~Monkey Vines ; G~Model Rocket Height ; H~Tiling a Grid With Dominoes ; I~Spatial Concepts Test", {}),
 ("cerc-2003", "bailian", "Central Europe 2003", "1769~Minimizing maximizer ; 1768~Hang or not to hang ; 1766~Football", {}),
 ("taiwan-2003", "bailian", "Asia Kaohsiung 2003",
  "1613~Cave Raider ; 1612~The Geodetic Set Problem ; 1614~Space AI Bombs ; 1616~Harmonic Periods ; 1615~Merging Sequences Problem", {}),
 ("cerc-2000", "bailian", "Central Europe 2000", "1401~Factorial", {}),
 ("nordic-2005", "bailian", "Nordic 2005 (NCPC 2005)", "2638~Kingdom", {}),
 ("ctuo-2008", None, "HUST (hustoj.org): CTU Open 2008",
  "1290~On-Line Banking ; 1291~International Collegiate Programming Contest ; 1293~Stock Exchange ; 1295~Safe Gambling", {}),
 ("mcpc-2011", None, "CSU (closed): 2011 Mid-Central USA Regional Contest", "1853~Su-domino-ku ; 1856~Sokoban", {}),
 ("pacnw-2013", None, "CSU (closed): 2013 Pacific Northwest Region Programming Contest",
  "1815~Enterprising Escape ; 1816~Assignments ; 1820~Federation Favorites", {}),
 ("rmc-2011", None, "HRBUST (closed): The 2011 Rocky Mountain Regional Contest", "1298~Pills", {}),
 ("cerc-2007", None, "HUST (hustoj.org): Central Europe Regional Contest 2007", "1108~Rectangular Polygons", {}),
 ("shanghai-2011", None, "HRBUST (closed): 2011 Asia Shanghai Regional Contest", "1202~Yummy Triangular Pizza ; 1209~Revenge of Fibonacci", {}),
 ("ncna-2014", "hackerrank", HR, f"{HR}/challenges/server~Server ; {HR}/challenges/continued-fractions~Continued Fractions",
  {"Continued Fractions": "\\(\\text{Con}+\\cfrac{\\text{tin}}{\\text{ued}+\\cfrac{\\text{Frac}}{\\text{tions}}}\\)"}),
]


def norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s or "") if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9а-я]+", "", s)


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); touched = set(); changed = set(); made = linked = 0
    where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    hunt = ROOT.parent / "_hunt" / "problems-2026-11-13" / "vjudge-harvest-2026-11-13.json"
    poj = json.loads(hunt.read_text())["POJ"] if hunt.exists() else {}
    for sid, judge, src, rows, same in LISTS:
        s = sets.get(sid)
        if s is None:
            ser, c = where[sid]
            s = sets[sid] = {"id": sid, "complete": False, "letters": "unknown", "contests": [{"contest": sid}], "problems": [], "provenance": []}
            c["problems"] = {"set": sid}; touched.add(ser)
        probs = s.setdefault("problems", []); have = {norm(p["name"]): p for p in probs}; n0 = len(probs)
        for row in rows.split(" ; "):
            key, title = row.split("~", 1); letter = key if re.fullmatch(r"[A-Z]", key) else None
            p = have.get(norm(same.get(title, title)))
            if p is None:
                p = {"id": pid(None, sid, letter, title), "name": title}
                assert p["id"] not in {q["id"] for q in probs}
                probs.append(p); have[norm(title)] = p; made += 1
            if letter:
                e = next(e for e in s["contests"] if e["contest"] == sid)
                if isinstance(e.get("letters"), dict) or "letters" not in e:
                    e.setdefault("letters", {}).setdefault(letter, p["id"])
                    if s.get("letters") == "unknown": del s["letters"]
            links = [(judge, key)] if judge else []
            if judge == "bailian" and key in poj and norm(poj[key][0]) == norm(title):
                links.append(("poj", key))
            for j, k in links:
                if not any(x["judge"] == j for x in p.get("judges") or []):
                    p.setdefault("judges", []).append({"judge": j, "url": URL[j].format(id=k), "id": k.rsplit("/", 1)[-1]}); linked += 1
        if s.get("count") and len(probs) > s["count"]:
            print(f"!! {sid}: {len(probs)} problems, count says {s['count']}"); return 1
        if s.get("count") and len(probs) == s["count"] and s.get("complete") is False and all(len(p) for p in probs):
            pass   # `complete` is about holdings, left alone
        s.setdefault("provenance", []).append(
            f"problem names from the judge source '{src}' as listed by vjudge.net, read 2026-11-14 (tools/add_problem_lists_2026_11_14.py)")
        changed.add(sid); print(f"{sid}: {n0} -> {len(probs)} problems")
    if not dry:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for ser in touched: dump_series(ser, series[ser], "add_problem_lists_2026_11_14.py (2026-11-14)")
    print(f"{made} problems created, {linked} judge links added, {len(touched)} series touched" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
