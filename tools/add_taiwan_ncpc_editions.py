#!/usr/bin/env python3
"""One-off (2026-11-25): the editions of Taiwan's NCPC that the organisers' past-problem bank lists.

    python3 tools/add_taiwan_ncpc_editions.py FILES_HTML            # print the plan
    python3 tools/add_taiwan_ncpc_editions.py FILES_HTML --write

FILES_HTML is a copy of https://ncpc.ntnu.edu.tw/files.html (歷年題庫, the past-problem bank). The page
lists problem files by ROC year (Gregorian year = ROC year + 1911). From ROC 103 (2014) on it gives
a preliminary round (初賽) and a final round (決賽); a round is a contest (ruling 2026-11-24), so the
final is taiwan-ncpc-YYYY and the preliminary is taiwan-ncpc-preliminary-YYYY. The groups of a year
(甲/乙/丙, 大學/專科, 程式設計組/應用軟體設計組) sat the same day and stay scopes of one contest, as
taiwan-ncpc-2012 already has them.
"""
from __future__ import annotations

import html
import re
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import add_source, dump_series, load_series, normalise_contest  # noqa: E402

BASE = "https://ncpc.ntnu.edu.tw/"
BANK = BASE + "files.html"
TODAY = "2026-11-25"
GROUPS = {"甲組": "Group A (甲組)", "乙組": "Group B (乙組)", "丙組": "Group C (丙組)", "丙": "Group C (丙)",
          "大學甲": "university Group A (大學甲)", "大學乙": "university Group B (大學乙)",
          "專科甲": "junior college Group A (專科甲)", "專科乙": "junior college Group B (專科乙)"}


def classify(label: str, href: str):
    """-> (round, role, scope, contains)"""
    pdf = href.lower().endswith(".pdf")
    pre, fin = "初賽" in label, "決賽" in label
    rnd = "preliminary" if pre and not fin else "final"
    if "解法" in label:
        return rnd, "editorial", f"solutions of the {rnd} round ({label})", None
    if "測" in label or "testcase" in href.lower():
        which = f"{rnd} round, " if (pre or fin) else ""
        return rnd, "problemset", f"{which}test data ({label})", ["data"]
    if "參考資料" in label:
        return rnd, "problemset", f"reference material for the tasks ({label})", ["data"]
    if "資料檔" in label or href.lower().endswith(".sql"):
        return rnd, "problemset", f"application software design group, data files ({label})", ["data"]
    if "應用軟體設計組" in label:
        return rnd, "problemset", "application software design group (應用軟體設計組)", ["statement"] if pdf else None
    if "程式設計組" in label:
        tail = f", {rnd} round" if (pre or fin) else ""
        return rnd, "problemset", f"programming group{tail} ({label})", ["statement"] if pdf else None
    if pre or fin:
        return rnd, "problemset", f"{rnd} round ({label})", ["statement"] if pdf else None
    if label in GROUPS:
        return rnd, "problemset", GROUPS[label], ["statement"] if pdf else None
    return None, None, label, None


def plan(page: str):
    out, unknown = defaultdict(list), []
    for h, l in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', page, re.S):
        m = re.match(r"(?:\./)?(file/(\d+)/.+)", h)
        if not m:
            continue
        label = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", l))).strip()
        year = int(m.group(2)) + 1911
        rnd, role, scope, contains = classify(label, h)
        if rnd is None:
            unknown.append((h, label))
            continue
        url = BASE + urllib.parse.quote(m.group(1), safe="/()-_.~")
        out[(year, rnd)].append((url, role, scope, contains, label))
    return out, unknown


# what the organisers' site of the 2026 edition says (pages read 2026-11-25)
Y2026 = {
    "final": {
        "date": "2026-10-18",
        "sites": [{"location": "tw-taipei-ntnu", "name": "North site (北區試場), National Taiwan Normal University"},
                  {"location": "tw-kaohsiung-nsysu", "name": "South site (南區試場), National Sun Yat-sen University"}],
        "sources": [
            (BASE + "ncpc2026php/NCPC_scorboard/ncpc2026_scoreboard_final.html", "scoreboard", {"scope": "final round (決賽)"}),
            (BASE + "file/115/" + urllib.parse.quote("115年度NCPC獎勵名單(定).pdf", safe="()."), "rankings",
             {"scope": "prize winners (得獎名單)"}),
            (BASE + "file/115/" + urllib.parse.quote("115ncpc_決賽隊伍名單.pdf"), "teams", {"scope": "teams of the final round (決賽隊伍名單)"}),
            (BASE + "index/1150810-1.html", "report", {"scope": "organisers' notice: schedule of both rounds"}),
            (BASE + "index/1151008.html", "report", {"scope": "organisers' notice: sites and timetable of the final round"}),
        ],
    },
    "preliminary": {
        "date": "2026-10-03",
        "sources": [
            (BASE + "ncpc2026php/NCPC_scorboard/ncpc2026_scoreboard_pre.html", "scoreboard",
             {"scope": "preliminary round (初賽)",
              "note": "the page still carries DOMjudge's banner 'preliminary results - not final' (read 2026-11-25)"}),
            (BASE + "index/1150810-1.html", "report", {"scope": "organisers' notice: schedule of both rounds"}),
        ],
    },
}
# other result documents on the organisers' site (read 2026-11-25)
EXTRA = {
    2019: [(BASE + "file/Scoreboard(official).pdf", "scoreboard",
            {"scope": "final round (決賽)", "note": "a DOMjudge scoreboard printed to PDF, headed 108 年度全國大專電腦軟體設計競賽決賽 (final round of ROC year 108)"})],
    2023: [(BASE + "file/112/" + urllib.parse.quote("112年度NCPC獎勵名單(定).pdf", safe="()."), "rankings", {"scope": "prize winners (得獎名單)"})],
    2024: [(BASE + "file/113/" + urllib.parse.quote("113年度NCPC獎勵名單(定).pdf", safe="()."), "rankings", {"scope": "prize winners (得獎名單)"})],
    2025: [(BASE + "file/114/" + urllib.parse.quote("114年度NCPC獎勵名單(定).pdf", safe="()."), "rankings", {"scope": "prize winners (得獎名單)"})],
}
NAME = "Taiwan National Collegiate Programming Contest"


def main() -> int:
    page = Path(sys.argv[1]).read_text(errors="replace")
    write = "--write" in sys.argv
    pl, unknown = plan(page)
    if unknown:
        print("unclassified links:", unknown)
        return 1
    S = load_series()
    C = {c["id"]: c for d in S.values() for c in d["contests"]}
    ncpc = S["taiwan-ncpc"]
    pre = {"series": {"id": "taiwan-ncpc-preliminary", "name": NAME + ", preliminary round",
                      "tier": "subregional", "region": ncpc["series"]["region"], "naming": "season-start"},
           "contests": []}
    finals = sorted({y for y, r in pl if r == "final"})
    prelims = sorted({y for y, r in pl if r == "preliminary"})
    new = []
    for y in finals:
        cid = f"taiwan-ncpc-{y}"
        c = C.get(cid)
        if c is None:
            c = {"id": cid, "season": y + 1, "name": NAME, "cms_ids": []}
            if f"taiwan-{y}" in C:
                c["parent"] = f"taiwan-{y}"
            c["provenance"] = [f"ran: the organisers' past-problem bank (歷年題庫) lists the problem files of ROC year {y - 1911} "
                               f"({y}) — {BANK} (read {TODAY})"]
            c["notes"] = (f"added 2026-11-25 from the organisers' past-problem bank; no CMS record. "
                          + ("Date and sites from the organisers' notices of the year." if y == 2026 else "Date and host not researched yet."))
            ncpc["contests"].append(c)
            C[cid] = c
            new.append(cid)
        if y == 2026:
            c["date"] = Y2026["final"]["date"]
            c["sites"] = Y2026["final"]["sites"]
            for url, role, f in Y2026["final"]["sources"]:
                add_source(c, url, role, **f)
        for url, role, f in EXTRA.get(y, []):
            add_source(c, url, role, **f)
        for url, role, scope, contains, _ in pl[(y, "final")]:
            add_source(c, url, role, scope=scope, contains=contains)
    ncpc["contests"].sort(key=lambda c: c["id"])
    ids = [c["id"] for c in ncpc["contests"]]
    for a, b in zip(ids, ids[1:]):
        C[a]["next"] = b
    for y in prelims:
        cid = f"taiwan-ncpc-preliminary-{y}"
        c = {"id": cid, "season": y + 1, "name": NAME + ", preliminary round", "cms_ids": [], "parent": f"taiwan-ncpc-{y}"}
        if y == 2026:
            c["date"] = Y2026["preliminary"]["date"]
            for url, role, f in Y2026["preliminary"]["sources"]:
                add_source(c, url, role, **f)
        for url, role, scope, contains, _ in pl[(y, "preliminary")]:
            add_source(c, url, role, scope=scope, contains=contains)
        c["provenance"] = [f"ran: the organisers' past-problem bank (歷年題庫) lists the files of the preliminary round (初賽) of ROC year "
                           f"{y - 1911} ({y}) — {BANK} (read {TODAY})",
                           "a round is a contest (ruling 2026-11-24): its problems are not those of the final round"]
        c["notes"] = "added 2026-11-25 from the organisers' past-problem bank; no CMS record." + ("" if y == 2026 else " Date not researched yet.")
        pre["contests"].append(c)
        new.append(cid)
    for a, b in zip(pre["contests"], pre["contests"][1:]):
        a["next"] = b["id"]
    for (y, r), items in sorted(pl.items()):
        print(y, r)
        for url, role, scope, contains, label in items:
            print("    ", role, "|", scope, "|", contains, "|", urllib.parse.unquote(url[len(BASE):]))
    print(len(new), "new contests:", new[0], "…", new[-1])
    if write:
        for d in (ncpc, pre):
            d["contests"] = [normalise_contest(c) for c in d["contests"]]
        dump_series("taiwan-ncpc", ncpc, "add_taiwan_ncpc_editions.py")
        dump_series("taiwan-ncpc-preliminary", pre, "add_taiwan_ncpc_editions.py")
        print("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
