#!/usr/bin/env python3
"""Packs for reading problem names out of the problem-set documents we hold.

  python3 tools/names_pack.py --out ../_names/run1 [--batches 20] [--only <contest> ...]

A contest is on the worklist when its problems are not all listed by name (coverage: names is not
`all`) and we hold a copy of one of its `problemset` / `problem` sources. For each, a pack:

  <out>/<contest>/pack.json   what the catalogue lists (count, letters, names) and the sources we hold
  <out>/<contest>/s<n>.txt    the text of source n: for a PDF the top of every page (titles sit there)
                              and the whole first two pages; for a web page its text and its links;
                              for an archive or folder its file names
  <out>/batches/b<k>.json     the worklist cut into batches, one per reader

A reader (an agent) writes <out>/<contest>/result.json; tools/names_apply.py turns the results
into catalogue changes. Nothing here changes the catalogue.
"""
import argparse, gzip, html, json, re, subprocess, sys, tarfile, tempfile, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, load_contests, load_series, load_sets, set_id_of, set_letters, sources  # noqa: E402
from resources import norm_key  # noqa: E402
import coverage as CV  # noqa: E402

ARCHIVE = ROOT.parent / "archive"
PAGE_TOP, FIRST_PAGES, TEXT_MAX, OCR_PAGES = 700, 2, 24000, 30


def body(p: Path) -> bytes:
    b = p.read_bytes()
    return gzip.decompress(b) if b[:2] == b"\x1f\x8b" else b


def pdf_text(p: Path) -> str:
    try:
        txt = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True, timeout=120).stdout
    except Exception as e:  # noqa: BLE001
        return f"pdf: could not be read ({e})"
    pages = txt.split("\f")
    how = "text layer"
    if len(re.sub(r"\s", "", txt)) < 40 * max(1, len(pages)) // 4:   # no text layer to speak of: a scan
        try:
            with tempfile.TemporaryDirectory() as td:
                subprocess.run(["pdftoppm", "-r", "110", "-l", str(OCR_PAGES), "-gray", "-png", str(p), td + "/p"], capture_output=True, timeout=300)
                pages = [subprocess.run(["tesseract", str(img), "-"], capture_output=True, text=True, timeout=90).stdout for img in sorted(Path(td).glob("p*.png"))]
            how = f"a scan, read by OCR (first {OCR_PAGES} pages at most; expect misreadings)"
        except Exception as e:  # noqa: BLE001
            return f"pdf: a scan with no text layer; OCR failed ({e})"
    pages = [re.sub(r"[ \t]+", " ", x).strip() for x in pages]
    pages = [x for x in pages if x]
    out = [f"PDF, {len(pages)} pages with text, {how}. The first {FIRST_PAGES} pages in full, then the top of every page."]
    for i, pg in enumerate(pages, 1):
        out.append(f"=== page {i} ===\n" + (pg[:6000] if i <= FIRST_PAGES else re.sub(r"\n\s*\n+", "\n", pg)[:PAGE_TOP]))
    return "\n".join(out)[:120000]


def html_text(raw: bytes) -> str:
    t = raw.decode("utf-8", "replace")
    if "�" in t[:4000]:
        for enc in ("cp1251", "gb18030", "latin-1"):
            try:
                t = raw.decode(enc)
                break
            except Exception:  # noqa: BLE001
                continue
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", t)
    links = re.findall(r'(?is)<a\b[^>]*href=["\']?([^"\' >]+)[^>]*>(.*?)</a>', t)
    t2 = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", t)
    t2 = re.sub(r"(?i)<(br|/p|/div|/tr|/li|/h[1-6]|/td|/th)\b[^>]*>", "\n", t2)
    t2 = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t2))
    t2 = re.sub(r"[ \t\r]+", " ", t2)
    t2 = re.sub(r"\n\s*\n+", "\n", t2).strip()
    ln = [f"  {html.unescape(re.sub(r'(?s)<[^>]+>', ' ', a)).strip()[:90]} -> {h[:140]}" for h, a in links if re.sub(r"(?s)<[^>]+>", "", a).strip()]
    return (f"web page, title: {html.unescape(title.group(1)).strip()[:200] if title else '(none)'}\n--- text ---\n" + t2[:TEXT_MAX]
            + f"\n--- links ({len(ln)}) ---\n" + "\n".join(ln[:250]))


def names_of(p: Path) -> str:
    try:
        if zipfile.is_zipfile(p):
            return "zip archive, members:\n" + "\n".join("  " + n for n in zipfile.ZipFile(p).namelist()[:400])
        if tarfile.is_tarfile(p):
            return "tar archive, members:\n" + "\n".join("  " + n for n in tarfile.open(p).getnames()[:400])
    except Exception as e:  # noqa: BLE001
        return f"archive could not be listed ({e})"
    return ""


def text_of(p: Path) -> str:
    if not p.exists():
        return "copy file is missing on disk"
    if p.is_dir():
        files = sorted(x for x in p.rglob("*") if x.is_file())
        out = [f"folder of {len(files)} files:"] + [f"  {x.relative_to(p)} ({x.stat().st_size} bytes)" for x in files[:300]]
        docs = [x for x in files if x.suffix.lower() in (".pdf", ".html", ".htm", ".txt", ".tex", ".ps") or x.name in ("page.html", "index.html")][:12]
        for x in docs:
            out.append(f"\n##### {x.relative_to(p)} #####\n" + text_of(x)[:9000])
        return "\n".join(out)[:120000]
    raw = body(p)[:8_000_000]
    if raw[:5] == b"%PDF-" or p.suffix.lower() == ".pdf":
        return pdf_text(p)
    arch = names_of(p)
    if arch:
        return arch
    if p.suffix.lower() in (".txt", ".tex", ".csv", ".json", ".md"):
        return f"text file, {len(raw)} bytes:\n" + raw.decode("utf-8", "replace")[:TEXT_MAX]
    return html_text(raw)


def copies_of(c: dict, s: dict, by_key: dict) -> list[dict]:
    """The copies we hold of one source of a contest, best first (as tools/content_check_pack.py picks them)."""
    L = by_key.get(norm_key(s["url"])) or {}
    caps = [cap for r in (L.get("resources") or {}).values() for cap in r.get("captures") or []]
    cited = {r["contest"] for r in L.get("refs") or []}
    own = [x for x in caps if x.get("contest") == c["id"] or x["path"] in (s.get("archived") or [])]
    caps = own or (caps if len(cited) <= 1 else [])
    caps = [x for x in caps if not x.get("caveat")]
    caps.sort(key=lambda x: (x.get("source") == "live", x.get("fetched") or ""), reverse=True)
    return caps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--batches", type=int, default=20)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--list", action="store_true", help="print the worklist and stop")
    a = ap.parse_args()
    out = Path(a.out)
    contests, series, sets = load_contests(), load_series(), load_sets()
    by_key = {norm_key(L["url"]): L for L in json.loads((ROOT / "data" / "resources.json").read_text())["locators"].values()}
    held = {}

    def is_held(c, s):
        k = (c["id"], s["url"])
        if k not in held:
            held[k] = copies_of(c, s, by_key)
        return bool(held[k])
    cov = CV.Coverage(series, sets, held=is_held)
    work = []
    for cid, c in sorted(contests.items()):
        if c.get("status") == "upcoming" or (a.only and cid not in a.only):
            continue
        r = cov.record(c)
        if r["pmeta"]["names"] == "all":
            continue
        src = [(n, s) for n, s in enumerate(sources(c), 1) if {"problemset", "problem"} & set(s["roles"]) and is_held(c, s)]
        if src:
            work.append((cid, c, r, src))
    kinds = {"statement (not on a judge)": 0, "other held problem set source only": 0}
    for cid, c, r, src in work:
        st = any(not s.get("judge") and {"statement", "package"} & set(s.get("contains") or []) for _n, s in src)
        kinds["statement (not on a judge)" if st else "other held problem set source only"] += 1
    print(f"{len(work)} contests whose names are not all listed and of which we hold a problem set source:", kinds)
    if a.list:
        return 0
    for cid, c, r, src in work:
        d = out / cid
        if (d / "pack.json").exists():   # built by an earlier run: packs take a while (OCR), so a run can be resumed
            continue
        d.mkdir(parents=True, exist_ok=True)
        sid = set_id_of(c)
        st = sets.get(sid) if sid else None
        letters = {pid: L for L, pid in (set_letters(st, cid) or {}).items()} if st else {}
        pack = {"contest": cid, "name": c.get("name"), "date": str(c.get("date") or ""), "season": c.get("season"),
                "set": sid, "set_shared_with": [m["contest"] for m in (st or {}).get("contests") or [] if m["contest"] != cid],
                "count": (st or {}).get("count"), "names_listed": r["pmeta"]["names"],
                "problems_listed": [{"letter": letters.get(p["id"]), "name": p.get("name")} for p in (st or {}).get("problems") or []],
                "sources": []}
        for n, s in src:
            cap = held[(cid, s["url"])][0]
            p = ARCHIVE / cap["path"]
            try:
                text = text_of(p)
            except Exception as ex:  # noqa: BLE001
                text = f"could not be read: {type(ex).__name__}: {ex}"
            (d / f"s{n}.txt").write_text(text)
            pack["sources"].append({"n": n, "url": s["url"], "roles": s["roles"], "contains": s.get("contains"), "judge": s.get("judge"),
                                    "scope": s.get("scope"), "text": f"s{n}.txt", "text_chars": len(text), "file": str(p)})
        (d / "pack.json").write_text(json.dumps(pack, indent=1, ensure_ascii=False))
    (out / "batches").mkdir(parents=True, exist_ok=True)
    ids = [w[0] for w in work]
    k = max(1, min(a.batches, len(ids)))
    for i in range(k):
        (out / "batches" / f"b{i + 1:02d}.json").write_text(json.dumps(ids[i::k]))
    print(f"packs for {len(ids)} contests in {out}, {k} batches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
