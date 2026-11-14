#!/usr/bin/env python3
"""Build the packs for the content check: per contest, what the catalogue says and a text
digest of the copy we hold of each of its sources, for a reader (an agent) to judge the
sources against tools/content_check_rubric.md.

  python3 tools/content_check_pack.py --out ../_content-check/pilot --sample 100 [--seed 1]
  python3 tools/content_check_pack.py --out ../_content-check/run1 --contests nwerc-2018,wf-2009

Writes <out>/<contest>/pack.json and <out>/<contest>/s<N>.txt (one digest per source that has a
copy), and <out>/index.json. Nothing in the catalogue is changed. Copies are read from
../archive; a source without a copy is in the pack with `copy: null`.
"""
import argparse
import gzip
import json
import random
import re
import subprocess
import sys
import tempfile
import warnings
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, is_cms, load_contests, load_series, load_sets, set_id_of, set_letters, sources  # noqa: E402
from resources import norm_key  # noqa: E402

ARCHIVE = ROOT.parent / "archive"
warnings.filterwarnings("ignore")
TEXT_MAX, ROWS_HEAD, ROWS_TAIL = 3500, 6, 3


def body(p: Path) -> bytes:
    b = p.read_bytes()
    return gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b


def html_digest(raw: bytes) -> str:
    from bs4 import BeautifulSoup
    for enc in ("utf-8", "gb18030", "cp1251", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    soup = BeautifulSoup(text, "lxml")
    out = [f"title: {(soup.title.string or '').strip() if soup.title else ''}"]
    frames = [f.get("src") for f in soup.find_all(["frame", "iframe"]) if f.get("src")]
    if frames:
        out.append(f"frames: {frames[:8]}")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    heads = [h.get_text(" ", strip=True)[:100] for h in soup.find_all(["h1", "h2", "h3"])][:12]
    if heads:
        out.append("headings: " + " | ".join(heads))
    tables = [t for t in soup.find_all("table") if not t.find("table")]
    tables.sort(key=lambda t: -len(t.find_all("tr")))
    for i, t in enumerate(tables[:3]):
        rows = t.find_all("tr")
        cells = lambda r: [c.get_text(" ", strip=True)[:40] for c in r.find_all(["th", "td"])][:30]
        width = max((len(r.find_all(["th", "td"])) for r in rows), default=0)
        out.append(f"table {i + 1}: {len(rows)} rows, up to {width} columns")
        show = rows[:ROWS_HEAD] + ([None] if len(rows) > ROWS_HEAD + ROWS_TAIL else []) + (rows[-ROWS_TAIL:] if len(rows) > ROWS_HEAD else [])
        for r in show:
            out.append("  ..." if r is None else "  " + " ¦ ".join(cells(r)))
    links = soup.find_all("a", href=True)
    out.append(f"links: {len(links)}; first: " + " | ".join(f"{a.get_text(' ', strip=True)[:30]} -> {a['href'][:60]}" for a in links[:15]))
    vis = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    out.append(f"visible text: {len(vis)} characters; start:")
    out.append(vis[:TEXT_MAX])
    if len(vis) > TEXT_MAX + 800:
        out.append("... end of text: " + vis[-800:])
    return "\n".join(out)


def pdf_digest(p: Path) -> str:
    try:
        info = subprocess.run(["pdfinfo", str(p)], capture_output=True, text=True, timeout=30).stdout
        pages = re.search(r"Pages:\s+(\d+)", info)
        txt = subprocess.run(["pdftotext", "-l", "4", "-layout", str(p), "-"], capture_output=True, text=True, timeout=60).stdout
    except Exception as e:  # noqa: BLE001
        return f"pdf: could not be read ({e})"
    txt = re.sub(r"[ \t]+", " ", txt)
    if len(txt.strip()) < 40:   # no text layer: a scan. Read the first two pages with OCR
        try:
            with tempfile.TemporaryDirectory() as td:
                subprocess.run(["pdftoppm", "-r", "150", "-l", "2", "-gray", "-png", str(p), td + "/p"], capture_output=True, timeout=120)
                ocr = "".join(subprocess.run(["tesseract", str(img), "-"], capture_output=True, text=True, timeout=120).stdout
                              for img in sorted(Path(td).glob("p*.png")))
            ocr = re.sub(r"[ \t]+", " ", ocr)
            return (f"pdf: {pages.group(1) if pages else '?'} pages, a scan with no text layer; OCR of the first 2 pages "
                    f"({len(ocr)} characters, expect misreadings):\n" + ocr[:TEXT_MAX + 1500])
        except Exception as e:  # noqa: BLE001
            return f"pdf: {pages.group(1) if pages else '?'} pages, a scan with no text layer; OCR failed ({e})"
    return f"pdf: {pages.group(1) if pages else '?'} pages; text of the first 4 pages ({len(txt)} characters" + \
        (", none: probably a scan" if len(txt.strip()) < 40 else "") + "):\n" + txt[:TEXT_MAX + 1500]


def digest(p: Path) -> str:
    if not p.exists():
        return "copy file is missing on disk"
    if p.is_dir():   # a crawled website
        man = p / "site-manifest.json"
        if man.exists():
            m = json.loads(man.read_text())
            pages = [(u, e) for u, e in m["pages"].items() if e.get("ctype", "").startswith(("text/html", "application/pdf", "text/plain"))]
            out = [f"crawled website: seed {m.get('seeds')}, {len(m['pages'])} files, {len(pages)} pages (html/pdf/text). Pages, as file <- address:"]
            out += [f"  files/{e['file']} <- {u} ({e.get('size')} bytes)" for u, e in sorted(pages, key=lambda x: x[1].get("depth", 9))[:60]]
            if len(pages) > 60:
                out.append(f"  ... and {len(pages) - 60} more (site-manifest.json has them all)")
            if m.get("unfetched_in_scope"):
                out.append("not fetched: " + "; ".join(f"{u} ({why})" for u, why in list(m["unfetched_in_scope"].items())[:8]))
            first = next((e for u, e in m["pages"].items() if e.get("from") == "seed"), None) or (pages[0][1] if pages else None)
            if first and (p / "files" / first["file"]).exists():
                out += [f"--- the seed page (files/{first['file']}):", html_digest(body(p / "files" / first["file"]))]
            return "\n".join(out)
        files = sorted(x for x in p.rglob("*") if x.is_file())
        return "\n".join([f"folder of {len(files)} files, no site manifest"] + [f"  {x.relative_to(p)} ({x.stat().st_size} bytes)" for x in files[:40]])
    raw = body(p)
    if raw[:5] == b"%PDF-" or p.suffix.lower() == ".pdf":
        return pdf_digest(p)
    if p.suffix.lower() in (".txt", ".csv", ".json"):
        return f"text file, {len(raw)} bytes:\n" + raw.decode("utf-8", "replace")[:TEXT_MAX + 1500]
    return html_digest(raw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--contests")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    contests, series, sets = load_contests(), load_series(), load_sets()
    res = json.loads((ROOT / "data" / "resources.json").read_text())["locators"]
    by_key = {norm_key(L["url"]): L for L in res.values()}
    sites = defaultdict(list)
    for e in json.loads((ROOT / "data" / "website-index.json").read_text())["sites"]:
        if not e.get("empty") and not e.get("shell"):
            sites[e["contest"]].append(e)
    ran = {cid: c for cid, c in contests.items() if c.get("status") != "upcoming" and sources(c)}
    if args.contests:
        pick = [x for x in args.contests.split(",") if x in ran]
    else:
        strata = defaultdict(list)
        for cid, c in sorted(ran.items()):
            y = int(cid.rsplit("-", 1)[1])
            era = "-1994" if y < 1995 else "1995-2004" if y < 2005 else "2005-2014" if y < 2015 else "2015-"
            strata[(era, series[c["_series"]]["series"].get("region") or "?")].append(cid)
        rnd = random.Random(args.seed)
        for v in strata.values():
            rnd.shuffle(v)
        pick, keys = [], sorted(strata)
        while len(pick) < (args.sample or 100) and any(strata.values()):
            for k in keys:
                if strata[k] and len(pick) < (args.sample or 100):
                    pick.append(strata[k].pop())
    index = []
    for cid in pick:
        c = ran[cid]
        d = out / cid
        d.mkdir(parents=True, exist_ok=True)
        hdr = series[c["_series"]]["series"]
        sid = set_id_of(c)
        st = sets.get(sid) if sid else None
        pack = {"contest": cid, "name": c.get("name"), "series_name": hdr.get("name"), "region": hdr.get("region"), "tier": hdr.get("tier"),
                "date": str(c.get("date") or ""), "season": c.get("season"), "location": c.get("location"), "cms_ids": c.get("cms_ids"),
                "notes": c.get("notes"),
                "problems_known": ({"count": st.get("count"), "letters": {k: next((p.get("name") for p in st.get("problems") or [] if p["id"] == v), None)
                                                                         for k, v in (set_letters(st, cid) or {}).items()}} if st else None),
                "sources": []}
        for n, s in enumerate(sources(c), 1):
            L = by_key.get(norm_key(s["url"])) or {}
            caps = [cap for r in (L.get("resources") or {}).values() for cap in r.get("captures") or []]
            cited = {r["contest"] for r in L.get("refs") or []}
            own = [x for x in caps if x.get("contest") == cid or x["path"] in (s.get("archived") or [])]
            caps = own or (caps if len(cited) <= 1 else [])
            caps = [x for x in caps if not x.get("caveat")] or caps
            caps.sort(key=lambda x: (x.get("source") == "live", x.get("fetched") or ""), reverse=True)
            copy = None
            if caps:
                copy = {"path": caps[0]["path"], "via": caps[0].get("source"), "fetched": (caps[0].get("fetched") or "")[:10],
                        "size": caps[0].get("size"), "caveat": caps[0].get("caveat"), "other_copies": len(caps) - 1}
            elif "web" in s["roles"] and sites.get(cid):
                key = norm_key(s["url"])
                e = next((e for e in sites[cid] if norm_key(e["seed"]) == key), None) or next((e for e in sites[cid] if e.get("primary")), None)
                if e:
                    copy = {"path": e["dir"], "via": e.get("mode"), "fetched": (e.get("fetched") or "")[:10], "pages": e.get("pages"),
                            "seed": e["seed"], "shows": e.get("wayback_timestamp")}
            if copy:
                try:
                    (d / f"s{n}.txt").write_text(digest(ARCHIVE / copy["path"]))
                except Exception as ex:  # noqa: BLE001
                    (d / f"s{n}.txt").write_text(f"digest failed: {type(ex).__name__}: {ex}")
                copy["digest"] = f"s{n}.txt"
                copy["file"] = str(ARCHIVE / copy["path"])
            pack["sources"].append({"n": n, "url": s["url"], "roles": s["roles"], "scope": s.get("scope"), "judge": s.get("judge"),
                                    "as_of": s.get("as_of"), "cms_page": is_cms(s), "also_at": s.get("also_at"), "note": s.get("note"),
                                    "live_state": s.get("url_state"), "copy": copy})
        (d / "pack.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False))
        index.append({"contest": cid, "sources": len(pack["sources"]), "with_copy": sum(1 for x in pack["sources"] if x["copy"])})
    (out / "index.json").write_text(json.dumps(index, indent=1))
    print(f"{len(index)} contests, {sum(x['sources'] for x in index)} sources, {sum(x['with_copy'] for x in index)} with a copy -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
