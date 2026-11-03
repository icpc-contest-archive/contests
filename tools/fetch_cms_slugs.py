#!/usr/bin/env python3
"""Fill data/cms-shortnames.json for CMS ids that lack a finder slug.

The finder page is https://icpc.global/regionals/finder/<abbr>-<icpcYear>; the
public API GET /api/contest/public/<abbr>-<icpcYear> returns the contest record
including its CMS `id`. For every cms_id without a slug we guess candidates
(every abbr the same series uses elsewhere x season / season-1 / date year),
query the API, and accept a slug only when the returned id equals the cms_id.
Extra fields the API returns for the matched contests (homepage, problemsUrl,
resultsUrl, reportUrl) are written to data/import/cms-api-extras-<date>.json
for a separate review - they are NOT applied to the catalogue here.
"""
import json, re, sys, time, datetime, collections, urllib.request, urllib.error
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
API = "https://icpc.global/api/contest/public/"
SLUGS = ROOT / "data" / "cms-shortnames.json"


def get(slug):
    req = urllib.request.Request(API + slug, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def main():
    slugs = {int(k): v for k, v in json.loads(SLUGS.read_text()).items()}
    contests = []
    for f in sorted((ROOT / "series").glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        for e in (doc.get("contests") if isinstance(doc, dict) else doc) or []:
            e["_series"] = f.stem
            contests.append(e)
    prefixes = collections.defaultdict(collections.Counter)
    for e in contests:
        for i in e.get("cms_ids") or []:
            if i in slugs:
                prefixes[e["_series"]][re.sub(r"-\d{4}$", "", slugs[i])] += 1
    todo = [(e, i) for e in contests for i in (e.get("cms_ids") or []) if i not in slugs]
    print(f"{len(todo)} cms ids without a finder slug")
    today = datetime.date.today().isoformat()
    out = ROOT / "data" / "import" / f"cms-api-extras-{today}.json"
    prev = json.loads(out.read_text()) if out.exists() else {"matched": {}, "unresolved": []}
    extras, unresolved, found = prev["matched"], [], 0
    done_ids = {u["cms_id"] for u in prev["unresolved"]}
    todo = [(e, i) for e, i in todo if i not in done_ids]   # re-run = skip known misses
    unresolved = prev["unresolved"]
    for e, cid in todo:
        years = []
        for y in (e.get("season"), (e.get("season") or 0) - 1,
                  int(str(e.get("date", ""))[:4] or 0)):
            if y and y not in years:
                years.append(y)
        cands = [f"{p}-{y}" for p, _ in prefixes[e["_series"]].most_common() for y in years]
        hit = None
        for s in cands:
            d = get(s)
            time.sleep(0.4)
            if d and d.get("id") == cid:
                hit = s
                break
            if d:  # exists but is another contest - keep looking
                continue
        if hit:
            found += 1
            slugs[cid] = hit
            extras[e["id"]] = {"cms_id": cid, "slug": hit, "api_name": d.get("name"),
                               "homepage": d.get("homepage"), "problemsUrl": d.get("problemsUrl"),
                               "resultsUrl": d.get("resultsUrl"), "reportUrl": d.get("reportUrl"),
                               "endDate": d.get("endDate")}
            print(f"  ok   {e['id']:<28} {cid:>5} -> {hit}", flush=True)
            SLUGS.write_text(json.dumps({str(k): v for k, v in sorted(slugs.items())}, indent=0) + "\n")
        else:
            unresolved.append({"contest": e["id"], "cms_id": cid, "tried": cands})
            print(f"  ??   {e['id']:<28} {cid:>5} tried {len(cands)}: {', '.join(cands[:4])}...", flush=True)
        out.write_text(json.dumps({"matched": extras, "unresolved": unresolved}, indent=1, ensure_ascii=False))
    print(f"found {found}, unresolved {len(unresolved)}; slugs now {len(slugs)}; extras -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
