#!/usr/bin/env python3
"""Build the packs for the description round: per contest, what the catalogue says, a text digest
of the copy we hold of each of its sources, and what the content check of 2026-11-14 concluded
about each, for a reader (an agent) to check and describe against tools/describe_rubric.md.

  python3 tools/describe_pack.py --out ../_describe/pilot --sample 100 [--seed 2]
  python3 tools/describe_pack.py --out ../_describe/run1 --all [--budget 150]
  python3 tools/describe_pack.py --out ../_describe/run1 --contests nwerc-2018,wf-2009

Writes <out>/<contest>/pack.json and s<N>.txt (as tools/content_check_pack.py does; each source
also carries `earlier`, the earlier reader's verdict, when there is one), <out>/index.json and,
once every pack exists, <out>/batches/bNNN.txt of about --batch-sources held sources each.
Nothing in the catalogue is changed. With --all, a contest whose every held source already has a
description of the copy we hold now (data/source-descriptions/) is left out. With --unread-only a pack
holds only the sources not read yet (`other_sources` counts the rest of the contest's sources).
"""
import argparse
import json
import random
import sys
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import content_check_pack as P  # noqa: E402
from catalogue import ROOT, sources  # noqa: E402
from resources import norm_key  # noqa: E402

EARLIER: dict = {}   # norm_key(url) -> [(contest, verdict entry)]
EARLIER_RUN = "run-2026-11-15"
EARLIER_DATE = "2026-11-14"


def load_earlier() -> None:
    for f in sorted((ROOT / "data" / "content-check" / EARLIER_RUN).glob("w*.json")):
        for cid, v in json.loads(f.read_text()).items():
            for s in v.get("sources") or []:
                if s.get("url"):
                    EARLIER.setdefault(norm_key(s["url"]), []).append((cid, s))


def earlier_for(cid: str, src: dict) -> dict | None:
    hits = EARLIER.get(norm_key(src["url"])) or []
    hit = next(((c, s) for c, s in hits if c == cid), None) \
        or next(((c, s) for c, s in hits if (s.get("facts") or {}).get("belongs_to") == cid), None)
    if not hit:
        return None
    c, s = hit
    if s.get("verdict") == "no-copy":
        return None
    sha = ((src.get("copy") or {}).get("sha256") or "")
    return {"read_on": EARLIER_DATE, "under": c if c != cid else None, "verdict": s.get("verdict"), "roles_then": s.get("was"),
            "roles": s.get("roles"), "scope": s.get("scope"), "confidence": s.get("confidence"), "evidence": s.get("evidence"),
            "flags": s.get("flags") or [], "facts": s.get("facts") or {},
            "same_copy": (bool(sha) and s.get("copy") == sha) if s.get("copy") else None}


def build(job: tuple) -> dict:
    cid, out = job
    r = P.build_one(job)
    p = Path(out) / cid / "pack.json"
    pack = json.loads(p.read_text())
    for s in pack["sources"]:
        s["earlier"] = earlier_for(cid, s) if s.get("copy") else None
    p.write_text(json.dumps(pack, indent=1, ensure_ascii=False))
    return r


def load_read() -> dict:
    """{(contest, norm_key(address)): copy path} for every source a description round has read
    (data/describe/<run>/verdicts/<series>.json), described or not."""
    out = {}
    for f in sorted((ROOT / "data" / "describe").glob("*/verdicts/*.json")):
        for cid, v in json.loads(f.read_text()).items():
            for s in v.get("sources") or []:
                out[(cid, norm_key(s["url"]))] = s.get("copy")
    return out


def described(cid: str, c: dict) -> set:
    """Addresses of this contest that have a description (norm keys)."""
    f = ROOT / "data" / "source-descriptions" / c["_series"] / f"{cid}.yaml"
    if not f.exists():
        return set()
    import yaml
    return {norm_key(s["url"]) for s in (yaml.safe_load(f.read_text()) or {}).get("sources") or [] if s.get("description")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample", type=int)
    ap.add_argument("--seed", type=int, default=2)
    ap.add_argument("--contests")
    ap.add_argument("--all", action="store_true", help="every contest that ran and has a source without a description")
    ap.add_argument("--budget", type=int, default=0, help="stop starting new work after this many seconds (rerun to resume)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--batch-sources", type=int, default=18)
    ap.add_argument("--unread-only", action="store_true",
                    help="keep in each pack only the held sources no description round has read in the copy we hold now "
                         "(a later round after new captures: the other sources keep the descriptions they have)")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    P.load_globals()
    load_earlier()
    contests, series = P.G["contests"], P.G["series"]
    ran = {cid: c for cid, c in contests.items() if c.get("status") != "upcoming" and sources(c)}
    if args.contests:
        pick = [x for x in args.contests.split(",") if x in ran]
    elif args.all:
        pick = []
        for cid in sorted(ran):
            have = described(cid, ran[cid])
            if any(norm_key(s["url"]) not in have for s in sources(ran[cid])):
                pick.append(cid)
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
    todo = [cid for cid in pick if not (out / cid / "pack.json").exists()]
    t0, done = time.time(), 0
    with Pool(args.jobs) as pool:
        for _ in pool.imap_unordered(build, [(cid, str(out)) for cid in todo]):
            done += 1
            if args.budget and time.time() - t0 > args.budget:
                pool.terminate()
                break
    left = [cid for cid in pick if not (out / cid / "pack.json").exists()]
    index, read = [], load_read()
    for cid in pick:
        p = out / cid / "pack.json"
        if p.exists():
            pack = json.loads(p.read_text())
            srcs = pack["sources"]
            if args.unread_only:
                keep = [x for x in srcs if x["copy"] and read.get((cid, norm_key(x["url"]))) != x["copy"]["path"]]
                if len(keep) != len(srcs):
                    for x in srcs:   # (the mount may refuse deletes) an emptied digest is a dropped one
                        if x not in keep and x.get("copy") and x["copy"].get("digest") and (out / cid / x["copy"]["digest"]).exists():
                            (out / cid / x["copy"]["digest"]).write_text("")
                    pack["sources"], pack["other_sources"] = keep, len(srcs) - len(keep)
                    p.write_text(json.dumps(pack, indent=1, ensure_ascii=False))
                    srcs = keep
            index.append({"contest": cid, "sources": len(srcs), "with_copy": sum(1 for x in srcs if x["copy"]),
                          "first_reading": sum(1 for x in srcs if x["copy"] and not x.get("earlier")),
                          # held sources no description round has read in the copy we hold now
                          "unread": sum(1 for x in srcs if x["copy"] and read.get((cid, norm_key(x["url"]))) != x["copy"]["path"])})
    (out / "index.json").write_text(json.dumps(index, indent=1))
    print(f"built {done} now; {len(index)} of {len(pick)} packs exist, {len(left)} left; {sum(x['sources'] for x in index)} sources, "
          f"{sum(x['with_copy'] for x in index)} with a copy ({sum(x['first_reading'] for x in index)} not in the content check, "
          f"{sum(x['unread'] for x in index)} not read by a description round) -> {out}")
    if not left:
        bd = out / "batches"
        bd.mkdir(exist_ok=True)
        batches, cur, n = [], [], 0.0
        for x in sorted(index, key=lambda x: x["contest"]):
            if not x["unread"]:
                continue   # nothing new to read: the applier needs no result for it
            w = x["with_copy"] + 0.1 * (x["sources"] - x["with_copy"])
            if cur and (n + w > args.batch_sources or len(cur) >= 8):
                batches.append(cur)
                cur, n = [], 0.0
            cur.append(x["contest"])
            n += w
        if cur:
            batches.append(cur)
        for old in bd.glob("b*.txt"):
            old.write_text("")   # (the mount refuses deletes) an emptied batch file is a finished batch
        for i, b in enumerate(batches, 1):
            (bd / f"b{i:03d}.txt").write_text("\n".join(b) + "\n")
        print(f"{len(batches)} batches -> {bd}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
