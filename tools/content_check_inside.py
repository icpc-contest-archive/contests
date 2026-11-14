#!/usr/bin/env python3
"""Add the documents the content check found inside crawled sites as sources of their own.

  python3 tools/content_check_inside.py --name run-2026-11-15 --packs ../_content-check/run1 [--write]

An agent reading a crawled site lists the pages in it that are documents in their own right
(`facts.inside`: address, what it is). A page becomes a source of the contest when the site was
confirmed (or re-filed) with high confidence as being about this contest, the address is not a
source of any contest yet, and it is not a page of the ICPC CMS. Pages inside a site that turned
out to be about another edition go to that edition when the catalogue has it. Everything else is
listed in data/content-check/<run>/lists/inside-skipped.json.
"""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path
import catalogue as cat

ROOT = Path(__file__).resolve().parent.parent


ARCHIVE = ROOT.parent / "archive"
_manifests = {}


def crawl_pages(copy: dict) -> dict:
    """{address: page record} of the crawl a held copy belongs to (empty when it is no crawl)."""
    d = ARCHIVE / (copy.get("path") or "x")
    for up in (d, *d.parents):
        if up == ARCHIVE:
            break
        m = up / "site-manifest.json"
        if m.exists():
            if m not in _manifests:
                _manifests[m] = json.loads(m.read_text()).get("pages") or {}
            return _manifests[m]
    return {}


def resolve(addr: str, pages: dict):
    """The full address of a page an agent named by its path inside the crawl, or None."""
    rel = re.sub(r"\s+\(.*\)$", "", addr).lstrip("./")
    if not rel or " " in rel:
        return None
    hits = [u for u in pages if u.endswith("/" + rel) or u.endswith(rel) and rel.startswith("?")]
    hits = sorted(set(hits), key=len)
    return hits[0] if len(hits) == 1 or hits and all(h.split("://", 1)[1].replace(":80/", "/") ==
                                                     hits[0].split("://", 1)[1].replace(":80/", "/") for h in hits) else None


def other_year(url: str, cid: str, c: dict) -> bool:
    """The address names a year, and it is not this contest's."""
    own = {cid.rsplit("-", 1)[-1], str(c.get("season") or ""), str(c.get("date") or "")[:4]}
    own |= {y[2:] for y in own if len(y) == 4}
    years = set(re.findall(r"(?<!\d)((?:19[7-9]|20[0-3])\d)(?!\d)", url))
    return bool(years) and not (years & own)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--packs", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    run = ROOT / "data" / "content-check" / a.name
    verdicts = {}
    for f in sorted(run.glob("w*.json")):
        verdicts.update(json.loads(f.read_text()))
    series = cat.load_series()
    contests, everywhere = {}, {}
    for sid, doc in series.items():
        for c in doc["contests"]:
            contests[c["id"]] = (sid, c)
            for s in cat.sources(c):
                everywhere.setdefault(cat.norm_key(s["url"]), c["id"])
    added, skipped, touched = [], [], set()
    for cid, ver in sorted(verdicts.items()):
        if cid not in contests:
            continue
        pack = {s["n"]: s for s in json.loads((Path(a.packs) / cid / "pack.json").read_text())["sources"]}
        for v in ver["sources"]:
            inside = (v.get("facts") or {}).get("inside") or []
            if not inside:
                continue
            parent = pack[v["n"]]["url"]
            pages = crawl_pages(pack[v["n"]].get("copy") or {})
            to = cid
            if v["verdict"] == "wrong-contest":
                to = (v.get("facts") or {}).get("belongs_to")
            for i in inside:
                url, role = (i.get("address") or "").strip(), i.get("is")
                if not url.startswith(("http://", "https://")):
                    url = resolve(url, pages) or url
                row = {"contest": cid, "inside": parent, "url": url, "is": role, "verdict": v["verdict"],
                       "confidence": v.get("confidence")}
                why = None
                if not url.startswith(("http://", "https://")) or " " in url:
                    why = "not an address"
                elif role not in cat.RANK or role == "web":
                    why = "no role"
                elif v["verdict"] not in ("confirm", "correct", "wrong-contest") or v.get("confidence") != "high":
                    why = "site not confirmed with high confidence"
                elif to not in contests:
                    why = "site is about a contest the catalogue does not have"
                elif other_year(url, to, contests[to][1]):
                    why = "address names another year"
                elif cat.is_cms({"url": url}) or "icpc.global" in url:
                    why = "ICPC CMS page"
                elif cat.norm_key(url) in everywhere:
                    held = everywhere[cat.norm_key(url)]
                    if held == to:
                        continue  # already a source here: nothing to say
                    why = f"already a source of {held}"
                if why:
                    skipped.append(dict(row, why=why))
                    continue
                sid, c = contests[to]
                ts = (pages.get(url) or {}).get("wayback_timestamp")
                s, changed = cat.add_source(c, url, role, as_of=ts, note=f"found inside {parent} by the content check")
                everywhere[cat.norm_key(url)] = to
                touched.add(sid)
                added.append(dict(row, to=to))
    out = run / "lists"
    out.mkdir(exist_ok=True)
    (out / "inside-added.json").write_text(json.dumps(added, indent=1, ensure_ascii=False) + "\n")
    (out / "inside-skipped.json").write_text(json.dumps(skipped, indent=1, ensure_ascii=False) + "\n")
    print("added", len(added), dict(Counter(r["is"] for r in added).most_common()))
    print("contests gaining a source:", len({r["to"] for r in added}))
    print("skipped", len(skipped), dict(Counter(r["why"].split(" of ")[0] for r in skipped).most_common()))
    if a.write:
        for sid in sorted(touched):
            cat.dump_series(sid, series[sid], "content_check_inside.py")
        print("written", len(touched), "series files")


if __name__ == "__main__":
    sys.exit(main())
