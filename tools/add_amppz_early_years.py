#!/usr/bin/env python3
"""Problem lists and sources for the early Polish championships (AMPPZ 1996-2009), read from the
organisers' own pages on 2026-11-14.

The 2005 and 2006 history pages of the Krakow site (amppz.tcs.uj.edu.pl/<year>/historia.php.html)
link every earlier edition's site. Those sites are gone from the live web; the Wayback Machine has
them (the `as_of` on each source is the capture read). 2004-2006 are still live in Krakow.

  1996  cs.put.poznan.pl/conferences/zawody1/zadania.html: problems A-G, one page each; the page
        for G was never captured, so its title is not known (6 of 7).
  1997  ci.pwr.wroc.pl/zawody/97/problems/zadN/<letter>-task.doc: eight Word files, titles from
        their "PROBLEM X: ..." headings.
  1998  zawody.mimuw.edu.pl/98/zadania.html: seven contest problems (files a-g in that order) and
        two trial-session problems (Brackets, Permutations). SPOJ carries all nine under one source
        string, so the set already listed the two trial problems; they stay, with a note.
  2001  zawody.ii.uni.wroc.pl/2001/zadania.phtml: A-H in Polish. The four SPOJ problems are English
        versions (Partition = Podzial, Election Posters = Plakatowanie, The Long and Narrow Maze =
        Labirynt, The Loner = Samotnik); the problems take their original titles.
  2002  zawody.ii.uni.wroc.pl/2002/zadania.phtml: A-H. SPOJ has five problems "based on a problem
        from the VII Polish Collegiate Team Programming Contest (AMPPZ), 2002"; matched to the
        statements by content (weights 2^i on a pan balance = G, meeting place of friends = C,
        delivering for acquaintances = E, segments with more sunny than cloudy days = H, points
        inside a star-shaped region = B).
  2003  zawody.ii.uni.wroc.pl/zadania.phtml (capture of December 2004, the page of the VIII
        championship): A-H, and a trial-day problem X (Splyw), not added.
  2004  amppz.tcs.uj.edu.pl/2004/tresci_zadan.php.html: A-J, titles from the statement PDFs.
  2005  the set had A-J already; the Krakow pages are added as sources. Trial problems X, Y, Z
        (zeB ikjab, ikjab zeB, Sudoku) are published there and not added.
  2006  amppz.tcs.uj.edu.pl/2006/tresci_zadan.php.html and AMPPZ.pdf: A-I, K, L (there is no J);
        trial problems X, Y, Z (zeB ikjaB, ikjaB zeB, Zarowki) not added.
  2008  problem I, missing from the list, is "Istnienie N" (resources/I.pdf in the website capture).
  1999, 2000, 2009: the sites are added as sources; none of them published its problems (1999's
        results table shows letters A-G; the 2009 "resources" page says they would follow).

    python3 tools/add_amppz_early_years.py [--dry-run]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import pid  # noqa: E402
from import_judge_links import dump  # noqa: E402

TOOL = "tools/add_amppz_early_years.py"
SPOJ = "https://www.spoj.com/problems/{}/"
KR = "http://amppz.tcs.uj.edu.pl/"
# contest -> [(url, roles, as_of or None, note or None)]
SOURCES = {
    "poland-1996": [("http://www.cs.put.poznan.pl/conferences/zawody1/index.html", ["web"], "20001211120100", None),
                    ("http://www.cs.put.poznan.pl/conferences/zawody1/wyniki.html", ["standings"], "20010717211627", None),
                    ("http://www.cs.put.poznan.pl/conferences/zawody1/zadania.html", ["problemset"], "20010717212001", "problems A-G with solutions; the page for G was not captured")],
    "poland-1997": [("http://www.ci.pwr.wroc.pl/zawody/97/II_ozwz.html", ["web"], "20011008133451", None),
                    ("http://www.ci.pwr.wroc.pl/zawody/97/ranking.html", ["scoreboard"], "20021230222556", None),
                    ("http://www.ci.pwr.wroc.pl/zawody/97/zadania.html", ["problemset"], "20030522025906", "eight Word files, problems/zadN/<letter>-task.doc")],
    "poland-1998": [("http://zawody.mimuw.edu.pl/98/index.html", ["web"], "20010218112156", None),
                    ("http://zawody.mimuw.edu.pl/98/wyniki.html", ["standings"], "20010308201059", None),
                    ("http://zawody.mimuw.edu.pl/98/zadania.html", ["problemset"], "20010218044604", "statements (PostScript) and test files; two trial problems")],
    "poland-1999": [("http://zawody.mimuw.edu.pl/99/index.html", ["web"], "20020330203400", None),
                    ("http://zawody.mimuw.edu.pl/99/wyniki.html", ["scoreboard"], "20010814062546", None)],
    "poland-2000": [("http://zawody.mimuw.edu.pl/index.html", ["web"], "20010221171152", None)],
    "poland-2001": [("http://zawody.ii.uni.wroc.pl/2001/", ["web"], "20020927010753", None),
                    ("http://zawody.ii.uni.wroc.pl/2001/wyniki.phtml", ["scoreboard"], "20021015223428", None),
                    ("http://zawody.ii.uni.wroc.pl/2001/zadania.phtml", ["problemset"], "20020927011733", "statements (PostScript) and test data")],
    "poland-2002": [("http://zawody.ii.uni.wroc.pl/2002/", ["web"], "20030811214305", None),
                    ("http://zawody.ii.uni.wroc.pl/2002/wyniki.phtml", ["scoreboard"], "20030830074123", None),
                    ("http://zawody.ii.uni.wroc.pl/2002/zadania.phtml", ["problemset"], "20030830074524", "statements (PDF) and test data; also five problems of the Wroclaw internal qualifier")],
    "poland-2003": [("http://zawody.ii.uni.wroc.pl/", ["web"], "20041217005532", None),
                    ("http://zawody.ii.uni.wroc.pl/wyniki.phtml", ["scoreboard"], "20041204215223", None),
                    ("http://zawody.ii.uni.wroc.pl/zadania.phtml", ["problemset"], "20041204215729", "statements (PDF); trial-day problem X")],
    "poland-2004": [(KR + "2004/index.php.html", ["web"], None, None), (KR + "2004/ranking.php.html", ["scoreboard"], None, None),
                    (KR + "2004/tresci_zadan.php.html", ["problemset"], None, "statements (PDF)")],
    "poland-2005": [(KR + "2005/index.php.html", ["web"], None, None), (KR + "2005/ranking.php.html", ["scoreboard"], None, None),
                    (KR + "2005/tresci_zadan.php.html", ["problemset"], None, "statements (PDF); trial problems X, Y, Z"),
                    (KR + "2005/wzorce_testy.php.html", ["problemset"], None, "model solutions and tests, one tar per problem")],
    "poland-2006": [(KR + "2006/index.php.html", ["web"], None, None), (KR + "2006/contest/index.html", ["scoreboard"], None, None),
                    (KR + "2006/tresci_zadan.php.html", ["problemset"], None, "statements (PDF); trial problems X, Y, Z")],
    "poland-2009": [("http://amppz.wmi.amu.edu.pl/2009/index.php", ["web"], "20111013042803", "the 2009 edition's own pages; its resources page never received the problems")],
}
# set -> (count, where, [(letter, title)])
NEW = {
    "poland-1996": (7, "cs.put.poznan.pl/conferences/zawody1/zad_a.html ... zad_f.html (Wayback, 2001)",
                    "A~Party ; B~Squares ; C~Shapes ; D~Growing trees from numbers ; E~Minimal pour out of vessels ; F~Walking the matrix"),
    "poland-1997": (8, "the headings of ci.pwr.wroc.pl/zawody/97/problems/zadN/<letter>-task.doc (Wayback, 2003)",
                    "A~Derivative ; B~Peptides ; C~3D-Chess ; D~Permutations ; E~Ladder ; F~Commuting ; G~Land Administration in PRL ; H~AND/OR Graphs"),
    "poland-2002": (8, "zawody.ii.uni.wroc.pl/2002/zadania.phtml and the statement PDFs (Wayback, 2003-2004)",
                    "A~Autostrady ; B~Gwiazdozbiór ; C~Prywatka ; D~Liście ; E~Uprzejmy ; F~UZI na Perypetiach ; G~Paweł i Gaweł ; H~Słoneczne wczasy"),
    "poland-2003": (8, "zawody.ii.uni.wroc.pl/zadania.phtml (Wayback, 2004-12-04)",
                    "A~Pseudo-Pascal ; B~ŚUKS ; C~Szpinak ; D~Twardy orzech do zgryzienia ; E~Eksperci ; F~Wodolej ; G~Gadanki ; H~Liście"),
    "poland-2004": (10, "amppz.tcs.uj.edu.pl/2004/tresci_zadan.php.html and the statement PDFs",
                    "A~Kartki ; B~Zapytania ; C~Żołnierze ; D~Gra ; E~Poligon ; F~Hiperbilard ; G~Diamenty są wieczne ; H~Echelonik ; I~Obóz Babilon ; J~Kostka"),
    "poland-2006": (11, "amppz.tcs.uj.edu.pl/2006/tresci_zadan.php.html and tresci_zadan/AMPPZ.pdf",
                    "A~Stałopunktotron ; B~Dywersja ; C~Inwazja ; D~Zapis wieżowy ; E~Licytacja ; F~Prezentacja ; G~Maszyna inkrementacyjna ; H~Szkło ; I~Baca i turyści ; K~Tramwaje ; L~Szyfrowanie"),
}
SPOJ_2002 = {"B": ("FSHEEP", "Fencing in the Sheep"), "C": ("PLONK", "Where to Drink the Plonk?"), "E": ("COURIER", "The Courier"),
             "G": ("SCALES", "Balancing the Stone"), "H": ("ROCK", "Sweet and Sour Rock")}
L1998 = "A~Ball ; B~Cross-country ; C~Cutting out ; D~Expression ; E~Moulds ; F~Relations ; G~Tree"
L2001 = [("A", "Podział", "Partition"), ("B", "Plakatowanie", "Election Posters"), ("C", "Transformacje", None), ("D", "Labirynt", "The Long and Narrow Maze"),
         ("E", "Samotnik", "The Loner"), ("F", "Środek symetrii", None), ("G", "Stabilny prostokąt", None), ("H", "Kryształ", None)]


def rows(s): return [tuple(r.split("~", 1)) for r in s.split(" ; ")]


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); ser = series["poland"]; con = {c["id"]: c for c in ser["contests"]}
    changed = set(); made = 0; nsrc = 0
    for cid, srcs in SOURCES.items():
        c = con[cid]; have = {s["url"].rstrip("/") for s in c.setdefault("sources", [])}
        for url, roles, as_of, note in srcs:
            if url.rstrip("/") in have: continue
            s = {"url": url, "roles": roles}
            if as_of: s["as_of"] = as_of
            if note: s["note"] = note
            s["url_state"] = "dead" if as_of else "live"; s["url_checked"] = "2026-11-14"
            c["sources"].append(s); nsrc += 1
    for sid, (count, where, lst) in NEW.items():
        assert sid not in sets, sid
        probs = []; letters = {}
        for letter, title in rows(lst):
            p = {"id": pid(None, sid, letter, title), "name": title}
            if sid == "poland-2002" and letter in SPOJ_2002:
                code, en = SPOJ_2002[letter]
                p["judges"] = [{"judge": "spoj", "url": SPOJ.format(code), "id": code}]
                p["notes"] = f"SPOJ's '{en}' is, in its own words, based on a problem from this contest; matched to this statement by content"
            probs.append(p); letters[letter] = p["id"]; made += 1
        s = {"id": sid, "count": count, "contests": [{"contest": sid, "letters": letters}], "problems": probs,
             "provenance": [f"letters and titles from the organisers' pages: {where}, read 2026-11-14 ({TOOL})"]}
        if len(probs) < count:
            s["complete"] = False
            s["provenance"].append("problem G's page was never captured by the Wayback Machine; its title is not known")
        sets[sid] = s; con[sid]["problems"] = {"set": sid}; changed.add(sid)
    # 1998: letters; the two trial problems keep their place with a note
    s = sets["poland-1998"]; by = {p["name"]: p for p in s["problems"]}; e = s["contests"][0]
    e["letters"] = {l: by[t]["id"] for l, t in rows(L1998)}; s.pop("letters", None); s.pop("complete", None); s["count"] = len(s["problems"])
    for t, shown in (("Square Brackets", "Brackets"), ("Permutations", "Permutations")):
        by[t]["notes"] = f"trial-session problem ('{shown}' under 'Zadania próbne' on the contest's problems page), not one of the seven contest problems"
    s["provenance"].append(f"letters from zawody.mimuw.edu.pl/98/zadania.html (Wayback, 2001-02-18): seven contest problems, files a-g in that order, "
                           f"and two trial problems; the count of 9 includes the trial problems ({TOOL})")
    changed.add(s["id"])
    # 2001: the full list, original titles
    s = sets["poland-2001"]; by = {p["name"]: p for p in s["problems"]}; letters = {}
    for letter, pl, en in L2001:
        if en:
            p = by[en]; p["name"] = pl; p["notes"] = f"SPOJ carries it in English as '{en}'"
        else:
            p = {"id": pid(None, s["id"], letter, pl), "name": pl}; s["problems"].append(p); made += 1
        letters[letter] = p["id"]
    order = list(letters.values()); s["problems"].sort(key=lambda p: order.index(p["id"]))
    s["contests"][0]["letters"] = letters; s.pop("letters", None); s.pop("complete", None); s["count"] = 8
    s["provenance"].append(f"letters and original titles from zawody.ii.uni.wroc.pl/2001/zadania.phtml (Wayback, 2002-09-27); the page spells G "
                           f"'Stabliny prostokąt' ({TOOL})")
    changed.add(s["id"])
    # 2008: problem I
    s = sets["poland-2008"]; e = s["contests"][0]
    if "I" not in e["letters"]:
        p = {"id": pid(None, s["id"], "I", "Istnienie N"), "name": "Istnienie N"}
        i = next(k for k, q in enumerate(s["problems"]) if q["id"] == e["letters"]["J"]); s["problems"].insert(i, p)
        e["letters"] = dict(sorted({**e["letters"], "I": p["id"]}.items())); made += 1
        s["provenance"].append(f"problem I from http://amppz.cs.put.poznan.pl/resources/I.pdf in the website capture of 2026-09-05 ({TOOL})")
        changed.add(s["id"])
    for sid in changed:
        s = sets[sid]; assert len({p["id"] for p in s["problems"]}) == len(s["problems"]), sid
    if not dry:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        dump_series("poland", ser, "add_amppz_early_years.py (2026-11-14)")
    print(f"{nsrc} sources added, {made} problems created, sets changed: {sorted(changed)}" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
