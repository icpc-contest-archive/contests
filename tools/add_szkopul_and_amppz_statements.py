#!/usr/bin/env python3
"""Szkopuł as a judge, and the AMPPZ statements captured into the statement-only archive (2026-11-14).

Szkopuł (szkopul.edu.pl, the judge of the Polish Olympiad in Informatics) keeps an AMPPZ task archive,
https://szkopul.edu.pl/task_archive/amppz/, with the 2011-2014 and 2023 problems open for submission.
Its three-letter codes are the ones printed on the statements (ARY, BAJ, ...), which is how the
problems were matched; 2023 is listed by letter. Not linked: 2011 bez/mal/url and 2012 dzi, which are
on Szkopuł but not among the contest's lettered problems (trial problems, as far as the sets show),
and 2011 G, 2012 I, 2013 B, which Szkopuł does not have.

Statements, one PDF per contest in icpc-problem-archive/statement-only:
  1996  the six archived problem pages (HTML, with the organisers' solutions and listings); G missing
  1997  the eight Word files; 1998, 2001 the PostScript files; 2002-2005 the per-problem PDFs
        (2003 and 2005 with their trial problems at the end); 2006 the organisers' AMPPZ.pdf
  2011, 2012 the English problem sets; 2013, 2014 the Polish ones (no English one was published
        on the site), all four from the website captures of 2026-09-05

    python3 tools/add_szkopul_and_amppz_statements.py [--dry-run]
"""
import json, sys
from pathlib import Path
import yaml
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from import_judge_links import dump  # noqa: E402

TOOL = "tools/add_szkopul_and_amppz_statements.py"
JUDGE = {"id": "szkopul", "name": "Szkopuł", "short": "Szkopuł", "url": "https://szkopul.edu.pl/",
         "problem_url": "https://szkopul.edu.pl/problemset/problem/{id}/site/", "status": "active", "statements": True, "submissions": True,
         "notes": "Judge of the Polish Olympiad in Informatics (SIO2). Its task archive has an AMPPZ section, "
                  "https://szkopul.edu.pl/task_archive/amppz/, with the 2011-2014 and 2023 problems (Polish statements); "
                  "problem ids are opaque keys. Read 2026-11-14."}
# set -> szkopul code -> letter
MAP = {"poland-2011": dict(ary="A", baj="B", czy="C", drz="D", eks="E", fra="F", her="H", ilo="I", jas="J", krz="K"),
       "poland-2012": dict(aut="A", biu="B", cia="C", dna="D", ewa="E", **{"for": "F"}, gen="G", hyd="H", jut="J", kro="K"),
       "poland-2013": dict(aut="A", cie="C", dem="D", egz="E", fot="F", gra="G", her="H", inz="I", jan="J", koc="K", wal="P"),
       "poland-2014": dict(adw="A", ben="B", cen="C", dzi="D", euk="E", fil="F", glo="G", hit="H", ins="I", jas="J", kap="K"),
       "poland-2023": {l: l for l in "ABCDEFGHIJKLM"}}
ORDER = ["poland-2014", "poland-2013", "poland-2012", "poland-2011", "poland-2023"]; SIZE = [11, 11, 11, 13, 13]
STATEMENTS = {"poland-1996": 6, **{f"poland-{y}": None for y in (1997, 1998, 2001, 2002, 2003, 2004, 2005, 2006, 2011, 2012, 2013, 2014)}}
M = "http://amppz.mimuw.edu.pl/"
SOURCES = {
    "poland-2011": [(M + "2011/amppz2011-tresci-zadan.pdf", ["problemset"], "20170213102506", "Polish statements"),
                    (M + "2011/amppz2011-prezentacja-rozwiazan.pdf", ["editorial"], "20121018081454", "solution slides")],
    "poland-2012": [(M + "2012/amppz2012-problemset.pdf", ["problemset"], "20170822025722", "English statements"),
                    (M + "2012/amppz2012-tresci-zadan.pdf", ["problemset"], "20170822025526", "Polish statements"),
                    (M + "2012/amppz2012-prezentacja-rozwiazan.pdf", ["editorial"], "20170822025717", "solution slides")],
    "poland-2013": [(M + "amppz2013-tresci-zadan.pdf", ["problemset"], "20131030215454", "Polish statements"),
                    (M + "amppz2013-prezentacja-rozwiazan.pdf", ["editorial"], "20131030215222", "solution slides")],
    "poland-2014": [(M + "amppz2014-tresci-zadan.pdf", ["problemset"], "20141107020235", "Polish statements"),
                    (M + "amppz2014-prezentacja-rozwiazan.pdf", ["editorial"], "20141107020228", "solution slides")],
    "poland-2023": [("https://szkopul.edu.pl/task_archive/amppz/", ["problemset"], None, None)],
}


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); ser = series["poland"]; con = {c["id"]: c for c in ser["contests"]}
    rows = json.loads((ROOT / "data" / "szkopul-amppz-2026-11-14.json").read_text())
    assert len(rows) == sum(SIZE)
    links = nsrc = 0; changed = set(); i = 0
    for sid, n in zip(ORDER, SIZE):
        s = sets[sid]; letters = s["contests"][0]["letters"]; by = {p["id"]: p for p in s["problems"]}
        for key, label in rows[i:i + n]:
            code = label.rsplit("(", 1)[1].rstrip(")")
            letter = MAP[sid].get(code)
            if not letter: continue
            p = by[letters[letter]]
            if not any(j["judge"] == "szkopul" for j in p.get("judges") or []):
                p.setdefault("judges", []).append({"judge": "szkopul", "url": JUDGE["problem_url"].format(id=key), "id": key}); links += 1
        i += n; changed.add(sid)
        s.setdefault("provenance", []).append(f"Szkopuł links from https://szkopul.edu.pl/task_archive/amppz/, matched by the task codes printed on the statements, read 2026-11-14 ({TOOL})")
    for sid, part in STATEMENTS.items():
        s = sets[sid]; assert (ROOT.parent / "statement-only" / f"{sid}.pdf").exists(), sid
        s["repo"] = "icpc-problem-archive/statement-only"; s["statement"] = "partial" if part else "full"
        for k in ("data", "solutions", "package"): s.setdefault(k, "none")
        if part: s["counts"] = {"statement": part}
        s.setdefault("provenance", []).append(f"statements captured to statement-only/{sid}.pdf on 2026-11-14 ({TOOL})"); changed.add(sid)
    for cid, srcs in SOURCES.items():
        c = con[cid]; have = {x["url"].replace(":80", "").rstrip("/") for x in c["sources"]}
        for url, roles, as_of, note in srcs:
            if url.rstrip("/") in have: continue
            x = {"url": url, "roles": roles}
            if url.startswith("https://szkopul"): x["judge"] = "szkopul"
            if as_of: x["as_of"] = as_of
            if note: x["note"] = note
            x["url_state"] = "dead" if as_of else "live"; x["url_checked"] = "2026-11-14"; c["sources"].append(x); nsrc += 1
    for c in ser["contests"]:
        for x in c.get("sources") or []:
            if x["url"].startswith("https://szkopul.edu.pl/") and not x.get("judge"): x["judge"] = "szkopul"
    jf = ROOT / "judges.yaml"; text = jf.read_text()
    if "id: szkopul" not in text:
        text = text.rstrip("\n") + "\n" + yaml.safe_dump([JUDGE], allow_unicode=True, sort_keys=False, width=110)
    if not dry:
        jf.write_text(text)
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        dump_series("poland", ser, "add_szkopul_and_amppz_statements.py (2026-11-14)")
    print(f"{links} Szkopuł links, {len(STATEMENTS)} sets with statements, {nsrc} sources" + (" (dry run)" if dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
