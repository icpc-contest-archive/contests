#!/usr/bin/env python3
"""Import the "ICPC contest list / Main list" sheet export into the catalogue tree.

One-shot migration tool, kept for provenance and re-runnable (it regenerates
series/, registry/ and CONVERSION-FIXES.md from data/import/*.csv).

Model implemented (see DEFINITIONS.md):
  - series/<series>.yaml  : mainline contests only (ran or upcoming)
  - registry/cms-triage.yaml    : every excluded CMS DB id -> reason
  - registry/non-mainline.yaml  : real contests outside the advancement hierarchy
  - sentinel mapping: absent = not researched, null = confirmed none
  - next/parent multi-valued; cancelled editions are not chain members
  - subset_of derived from CMS-id containment (NA division double-layer)
"""
from __future__ import annotations

import csv
import datetime
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

CHAMPIONSHIPS = {"nac", "awc", "euc", "apc", "lac", "aec", "nadc"}
SERIES_RENAMES = {"ghuangzhou": "guangzhou", "gwailor-pune": "gwalior-pune"}
URL_COLS = {
    "Scoreboard": "scoreboard",
    "Frozen SB": "frozen_scoreboard",
    "Standings": "standings",
    "Rankings": "rankings",
}

fixes: list[str] = []


def log_fix(msg: str) -> None:
    fixes.append(msg)


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(
    type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null")
)


def read_sheet(path: Path) -> list[dict]:
    rows = list(csv.reader(path.open(newline="", encoding="utf-8-sig")))
    header, data = rows[0], rows[3:]  # rows 1-2 are spreadsheet count/percent rows
    col = {name: i for i, name in enumerate(header)}
    out = []
    for idx, r in enumerate(data):
        if not any(x.strip() for x in r):
            continue
        rec = {name: r[i].strip() for name, i in col.items()}
        rec["_line"] = idx + 4
        out.append(rec)
    return out


def split_short(short: str) -> tuple[str, int] | None:
    m = re.fullmatch(r"(.+)-(\d{4})", short)
    return (m.group(1), int(m.group(2))) if m else None


def rename_series_in(value: str) -> str:
    for old, new in SERIES_RENAMES.items():
        if value.startswith(old + "-"):
            return new + value[len(old):]
    return value


def apply_fixes(rows: list[dict]) -> None:
    n = 0
    for rec in rows:
        for field in ("Next", "Parent"):
            parts = [p.strip() for p in rec[field].split(",")]
            if "neerc-2017" in parts:
                rec[field] = ", ".join("nerc-2017" if p == "neerc-2017" else p for p in parts)
                n += 1
    log_fix(f"neerc renamed nerc in 2017: rewrote {n} pointers neerc-2017 -> nerc-2017")

    for rec in rows:
        if rec["Short name"] == "syria-2017" and rec["Date"] == "2017-17-23":
            rec["Date"] = ""
            rec["_note"] = (
                "date '2017-17-23' in source sheet is invalid; the SCPC-2018 finder "
                "link suggests Nov/Dec 2017"
            )
            log_fix("syria-2017: dropped invalid date 2017-17-23 (kept as note)")

    for rec in rows:
        old_short = rec["Short name"]
        for field in ("Short name", "Next", "Parent"):
            parts = [p.strip() for p in rec[field].split(",")]
            rec[field] = ", ".join(rename_series_in(p) for p in parts)
        if rec["Short name"] != old_short:
            log_fix(f"series-id typo: {old_short} -> {rec['Short name']}")


def clean_urls(value: str, where: str) -> list[str]:
    out = []
    for part in (p.strip() for p in value.split(",")):
        if not part:
            continue
        if re.match(r"^https?://", part):
            out.append(part)
        else:
            log_fix(f"dropped non-URL segment {part[:40]!r} from {where}")
    return out


def parse_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in re.split(r"[,; ]+", raw):
        if re.fullmatch(r"\d+", part):
            ids.append(int(part))
        elif re.fullmatch(r"\d+-\d+", part):
            a, b = map(int, part.split("-"))
            ids.extend(range(a, b + 1))
    return ids


def ref_value(raw: str, upcoming: bool):
    """absent (None returned as sentinel 'OMIT'), null, str or list."""
    if raw == "":
        return "OMIT"
    if raw == "-":
        return "OMIT" if upcoming else None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts[0] if len(parts) == 1 else parts


def build():
    src = sorted((ROOT / "data" / "import").glob("*.csv"))[-1]
    rows = read_sheet(src)
    apply_fixes(rows)

    mainline, outside, triage_rows, dropped = [], [], [], defaultdict(int)
    for rec in rows:
        st = rec["status"]
        if st in ("", "future") and split_short(rec["Short name"]):
            (outside if rec["Parent"] == "n/a" else mainline).append(rec)
        elif st in ("", "future"):
            dropped[f"status={st or 'real'} without short name"] += 1
        else:
            triage_rows.append(rec)

    index = {r["Short name"]: r for r in mainline}

    def season_of(rec) -> int | None:
        cur, hops = rec, 0
        while hops < 12:
            short = cur["Short name"]
            if short.startswith("wf-"):
                return int(short.split("-")[1])
            parent = cur["Parent"]
            first = parent.split(",")[0].strip()
            if first in ("", "-", "n/a") or first not in index:
                return None
            cur, hops = index[first], hops + 1
        return None

    # subset_of: proper CMS-id containment between mainline contests
    ids_of = {r["Short name"]: set(parse_ids(r["Contest ID"])) for r in mainline}
    subset_of: dict[str, str] = {}
    with_ids = [(s, ids) for s, ids in ids_of.items() if ids]
    for s, ids in with_ids:
        for t, tids in with_ids:
            if s != t and ids < tids:
                subset_of[s] = t
                log_fix(f"subset_of: {s} (cms {sorted(ids)}) < {t} (cms {sorted(tids)})")

    def contest_entry(rec, *, include_reason=None) -> dict:
        upcoming = rec["status"] == "future"
        c: dict = {"id": rec["Short name"]}
        if upcoming:
            c["status"] = "upcoming"
        ssn = season_of(rec)
        if ssn:
            c["season"] = ssn
        if rec["Full name"]:
            c["name"] = rec["Full name"]
        if rec["Date"] and rec["Date"] != "-":
            c["date"] = rec["Date"]
        if rec["Location"]:
            c["location"] = rec["Location"]
        if rec["Venue"]:
            c["venue"] = rec["Venue"]
        raw_id = rec["Contest ID"]
        if raw_id == "pre-cms":
            c["cms_ids"], c["cms_status"] = [], "pre-cms"
        elif raw_id == "n/a":
            c["cms_ids"] = []
        elif raw_id:
            c["cms_ids"] = parse_ids(raw_id)
        parent = ref_value(rec["Parent"], upcoming)
        if parent != "OMIT" and include_reason is None:
            c["parent"] = parent
        nxt = ref_value(rec["Next"], upcoming)
        if nxt != "OMIT":
            c["next"] = nxt
        if rec["Short name"] in subset_of:
            c["subset_of"] = subset_of[rec["Short name"]]
        web = clean_urls(rec["Web"], f"{rec['Short name']}/web")
        if web:
            c["web"] = web[0] if len(web) == 1 else web
        results = {}
        for col, key in URL_COLS.items():
            urls = clean_urls(rec[col], f"{rec['Short name']}/{key}")
            if urls:
                results[key] = [{"url": u} for u in urls]
        if results:
            c["results"] = results
        if rec["ICPC standings"]:
            c["icpc_standings"] = rec["ICPC standings"]
        if include_reason:
            c["reason"] = include_reason
        if rec.get("_note"):
            c["notes"] = rec["_note"]
        return c

    # ---- lineage: derived from cross-series next edges ----
    lineage_out = defaultdict(list)  # series -> events
    for rec in mainline:
        s_from = split_short(rec["Short name"])[0]
        nxt = rec["Next"]
        if nxt in ("", "-"):
            continue
        for target in (p.strip() for p in nxt.split(",")):
            tgt = split_short(target)
            if not tgt or target not in index:
                continue
            s_to, y_to = tgt
            if s_to != s_from:
                ev_a = {"type": "continues-as", "series": s_to, "year": y_to}
                ev_b = {"type": "continues-from", "series": s_from, "year": y_to}
                if ev_a not in lineage_out[s_from]:
                    lineage_out[s_from].append(ev_a)
                if ev_b not in lineage_out[s_to]:
                    lineage_out[s_to].append(ev_b)

    aliases = defaultdict(list)
    for old, new in SERIES_RENAMES.items():
        aliases[new].append(old)

    def series_name(contests_rows) -> str | None:
        for rec in reversed(contests_rows):  # newest with a full name
            name = rec["Full name"]
            if name:
                stripped = re.sub(r"^(The\s+)?(19|20)\d\d(-(\d\d){1,2})?\s+", "", name)
                if stripped and stripped != name:
                    return stripped
        return None

    # ---- emit series files ----
    by_series = defaultdict(list)
    for rec in mainline:
        by_series[split_short(rec["Short name"])[0]].append(rec)

    (ROOT / "series").mkdir(exist_ok=True)
    for old in (ROOT / "series").glob("*.yaml"):
        old.unlink()
    for sid, srows in sorted(by_series.items()):
        srows.sort(key=lambda r: split_short(r["Short name"])[1])
        header: dict = {"id": sid}
        nm = series_name(srows)
        if nm:
            header["name"] = nm
        if sid in CHAMPIONSHIPS:
            header["tier"] = "championship"
        if aliases.get(sid):
            header["aliases"] = aliases[sid]
        if lineage_out.get(sid):
            header["lineage"] = sorted(
                lineage_out[sid], key=lambda e: (e["year"], e["type"], e["series"])
            )
        doc = {"series": header, "contests": [contest_entry(r) for r in srows]}
        text = yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)
        (ROOT / "series" / f"{sid}.yaml").write_text(
            f"# Generated from {src.name} by tools/import_sheet.py — edit freely; the\n"
            f"# importer is one-shot and this file is now the source of truth.\n{text}"
        )

    # ---- non-mainline registry ----
    outside.sort(key=lambda r: r["Short name"])
    nm_doc = {
        "non_mainline_contests": [
            contest_entry(r, include_reason="outside-hierarchy (parent recorded as n/a)")
            for r in outside
        ]
    }
    (ROOT / "registry" / "non-mainline.yaml").write_text(
        "# Real contests that exist but are not part of the mainline ICPC advancement\n"
        "# hierarchy (decision 2026-08-31). Kept for reference; not part of the catalogue.\n"
        + yaml.dump(nm_doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)
    )

    # ---- cms triage registry ----
    mainline_ids = {n for ids in ids_of.values() for n in ids}
    triage, seen_triage = [], set()
    for rec in triage_rows:
        ids = parse_ids(rec["Contest ID"])
        if not ids:
            dropped[f"status={rec['status']} without CMS id"] += 1
            continue
        for cid in ids:
            if cid in mainline_ids:
                claimant = next(s for s, i in ids_of.items() if cid in i)
                log_fix(
                    f"triage row (status={rec['status']}, {rec['Full name'][:40]!r}) claims "
                    f"cms id {cid}, already part of mainline {claimant} — kept in {claimant}, "
                    f"dropped from triage"
                )
                continue
            if cid in seen_triage:
                dropped[f"duplicate triage id {cid}"] += 1
                continue
            seen_triage.add(cid)
            entry: dict = {"cms_id": cid, "reason": rec["status"]}
            if rec["Short name"] not in ("", "-"):
                entry["short_name"] = rec["Short name"]
            if rec["Full name"]:
                entry["name"] = rec["Full name"]
            if rec["Date"] and rec["Date"] != "-":
                entry["date"] = rec["Date"]
            triage.append(entry)
    triage.sort(key=lambda e: e["cms_id"])
    (ROOT / "registry" / "cms-triage.yaml").write_text(
        "# Every CMS DB contest id that is NOT a mainline contest, with the reason.\n"
        "# reasons: cancelled | camp | challenge | junk | minor | structural\n"
        "# Together with the cms_ids in series/, this is the 'considered every DB entry'\n"
        "# ledger the reconciliation job checks against the live CMS API.\n"
        + yaml.dump({"excluded": triage}, Dumper=Dumper, sort_keys=False, allow_unicode=True)
    )

    # ---- fixes log ----
    lines = [
        "# Conversion fixes and notes",
        "",
        f"Source: `{src.name}`, imported {datetime.date.today().isoformat()} by tools/import_sheet.py.",
        "",
        f"- mainline contests: {len(mainline)} in {len(by_series)} series files",
        f"- non-mainline (outside hierarchy): {len(outside)}",
        f"- CMS triage entries: {len(triage)}",
        "- rows not carried over (no CMS id to track, or duplicate):",
    ]
    for k, v in sorted(dropped.items()):
        lines.append(f"  - {k}: {v}")
    lines += ["", "## Mechanical fixes applied", ""]
    lines += [f"- {f}" for f in fixes]
    lines += [
        "",
        "## Not auto-fixed (left as open validator warnings)",
        "",
        "- tehran-2023 and kanpur-2022 dated after the AWC they advance to",
        "- nena-2026 has blank status (reads as 'ran') while sharing CMS id 9775 with future east-na-2026",
        "- south-america-south-2021 dated 2023-03-17 (looks like the 2022 edition's date)",
        "- germany-2026 still marked upcoming though dated 2026-06-13",
        "- 'Any' column dropped entirely (derived data; 11 stale cells in source became moot)",
    ]
    (ROOT / "CONVERSION-FIXES.md").write_text("\n".join(lines) + "\n")

    print(f"mainline: {len(mainline)} contests, {len(by_series)} series files")
    print(f"non-mainline: {len(outside)}; triage ids: {len(triage)}")
    print(f"dropped: {dict(dropped)}")
    print(f"fixes logged: {len(fixes)}")


if __name__ == "__main__":
    sys.exit(build())
