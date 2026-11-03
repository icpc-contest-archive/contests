#!/usr/bin/env python3
"""Mine problem-set locators for contests without a problemset source from the page lists of
this project's own website crawls (data/resources.json). A hit is a page we hold with
HTTP 200 whose URL looks like a problem set (set PDF > archive > problems index page),
year-consistent with the contest, not a per-problem file, and not another contest's set
hosted on the same site (a URL that fits several contests is dropped and reported).
Wayback-mode crawls give `as_of` = the page's snapshot, which must not predate the contest.

Writes data/problemset-candidates-sites-<date>.json for tools/apply_url_candidates.py
(--statuses verified,wayback) and a review list in reports/.
"""
import datetime, json, re, sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import by_role, has_role, load_contests  # noqa: E402

today = datetime.date.today().isoformat()
cat = load_contests()
ran = {k for k, c in cat.items() if c.get("status") != "upcoming"}
has = {k for k in ran if has_role(cat[k], "problemset")}
used = {s["url"] for c in cat.values() for s in by_role(c, "problemset")}
R = json.load(open(ROOT / "data/resources.json"))["locators"]

LOOKS = re.compile(r"problem[-_ ]?set|problems?(\.pdf|\.s?html?|/|$)|/problems|probset|tasks?\.pdf|statements?\.pdf|opgaven|uppgifter|zadania", re.I)
SKIP = re.compile(r"\.(css|js|png|jpe?g|gif|in|out|ans|dat|java|c|cpp|py|txt)$|/sample|/test|wp-json|\?C=|ProblemSetArchive|/ProblemSet/|JudgeOnline|/oj_|/problem$|/problem/"
                  r"|prac(?:tice)?|testdata|test[-_]?data|/TD\d|solution|judgedata|internet|callfor", re.I)
PER_PROBLEM = re.compile(r"/(?:p|prob|problem)?[a-z]?\d{0,3}(?:-[a-z0-9-]+)?\.(?:pdf|zip|rar|tgz)$|/[a-z](?:-[a-z0-9]+)?\.(?:pdf|zip|rar)$|/problem\d+\.pdf$|/[a-z]\.s?html?$", re.I)


# subregional folders on the NEERC/NERC archive -> catalogue series (extend as folders turn up)
NEERC_FOLDERS = {"northern": "north-russia", "ural": "urals", "south": "south-russia", "southern": "south-russia",
                 "west": "west-neerc", "western": "west-neerc", "central": "central-russia", "moscow": "moscow",
                 "siberia": "west-siberia", "nsk": "west-siberia", "far-east": "far-east-russia", "fareast": "far-east-russia",
                 "east": "east-siberia", "eastern": "east-siberia"}


def score(u: str) -> int:
    p = u.lower()
    if p.endswith(".pdf"):
        if PER_PROBLEM.search(p):
            return 0
        name = p.rsplit("/", 1)[-1]
        if "/problems/" in p and not re.search(r"problem|(?:^|[^a-z])set|^all\b|statement|task|opgaven|uppgifter|zadania|\d{4}", name):
            return 0  # one problem's PDF inside the problems folder
        return 10 if re.search(r"problem|set|tasks|statement", p) else 7
    if re.search(r"\.(zip|tgz|tar\.gz|rar)$", p):
        return 0 if PER_PROBLEM.search(p) else 6
    if re.search(r"/problems/?$|(?:^|/)problems?\.s?html?$|(?:^|/)problemset\.s?html?$|/problemset/?$|problem-statement", p):
        return 8
    return 0


per_url = defaultdict(set)
hits = defaultdict(list)
for L in R.values():
    for res in L["resources"].values():
        w = res.get("website")
        if not w:
            continue
        cid = w["contest"]
        if cid not in ran or cid in has:
            continue
        y = int(cid.rsplit("-", 1)[1])
        for pg in w.get("page_list") or []:
            u, st = pg[0], pg[1]
            ts = pg[3] if len(pg) > 3 and w.get("mode") == "wayback" else None
            if st != 200 or SKIP.search(u) or not LOOKS.search(u):
                continue
            sc = score(u)
            if not sc or u in used:
                continue
            if re.search(r"^https?://(neerc\.ifmo\.ru|nerc\.itmo\.ru)/archive/\d{4}/[^/]+$", u) \
                    and cid.rsplit("-", 1)[0] not in ("neerc", "nerc"):
                continue  # the NEERC/NERC final's own set, linked from every subregional page
            m = re.search(r"^https?://(?:neerc\.ifmo\.ru|nerc\.itmo\.ru)/archive/\d{4}/([^/]+)/", u, re.I)
            if m and NEERC_FOLDERS.get(m.group(1).lower()) != cid.rsplit("-", 1)[0]:
                continue  # a subregional's folder on the NEERC archive: only its own series may take it
            prelim_url = bool(re.search(r"prelim|qualif", u, re.I))
            if prelim_url != ("prelim" in cid or "qual" in cid):
                continue  # a preliminary's set on the finals' site, or the reverse
            yrs = [int(x) for x in re.findall(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", u)]
            held = int(cat[cid]["date"][:4]) if cat[cid].get("date") else y  # the calendar year it ran
            if yrs and y not in yrs and held not in yrs:
                continue
            if y in yrs:
                sc += 1  # the name year beats the calendar year when both are on the site
            if ts and int(ts[:4]) < y:
                continue  # snapshot older than the contest: another year's page
            hits[cid].append((sc, u, ts, w.get("mode")))
            per_url[u].add(cid)

shared = {u: cs for u, cs in per_url.items() if len(cs) > 1
          and not all(cat[c].get("subset_of") in cs or c in {cat[x].get("subset_of") for x in cs} for c in cs)}
out, review = [], []
for cid, lst in sorted(hits.items()):
    lst = [h for h in lst if h[1] not in shared]
    if not lst:
        continue
    sc, u, ts, mode = max(lst, key=lambda h: (h[0], -len(h[1])))
    out.append({"contest": cid, "artifact": "problemset", "url": u, "method": "site-crawl-mined",
                "status": "wayback" if ts else "verified", **({"as_of": ts} if ts else {}),
                "note": f"found in this project's archived crawl of the contest website ({mode} mode, HTTP 200)"})
    review.append(f"- {cid}: {u}" + (f" (snapshot {ts[:8]})" if ts else ""))
p = ROOT / "data" / f"problemset-candidates-sites-{today}.json"
p.write_text(json.dumps({"generated": today, "method": "tools/mine_problemsets_from_crawls.py", "candidates": out}, indent=1))
rep = ROOT / "reports" / f"problemset-mining-{today}.md"
rep.write_text(f"# Problem-set locators mined from our own site crawls — {today}\n\n"
               f"{len(out)} candidates for contests that had no `problemset:`; "
               f"{len(shared)} URLs dropped because they fit several contests (another contest's set on a shared host).\n\n"
               "## Applied candidates\n\n" + "\n".join(review) + "\n\n## Dropped as shared\n\n"
               + "\n".join(f"- {u} <- {sorted(cs)}" for u, cs in sorted(shared.items())) + "\n")
print(f"{len(out)} candidates -> {p.relative_to(ROOT)}; {len(shared)} shared URLs dropped; review: {rep.relative_to(ROOT)}")
print(Counter(x["status"] for x in out))
