#!/usr/bin/env python3
"""Place contest sites that were left without a location (site review 2026-11-13).

A site with a `name` but no `location` shows as "not placed". 187 did, on 121 contests, for
four different reasons; this deals with the three that need no research:

  1. A division label hid a known name: `Hendrix College Div. 1`. The label is stripped for the
     lookup only (the site keeps its name, which is how the divisions stay told apart).
  2. The name is a node of the tree already, by name or alias (`Drexel University`, `BOSPRE`).
  3. The name is an institution the tree lacked. PLACES below is the hand table (institution ->
     city); missing cities and institutions are added to locations.yaml.
  4. The "site" is a CMS group, not a place (`GGGGGG`, `zzz Site for future use`, `UPE`, a
     foreign-team registration group): it becomes {type: administrative} and is never shown.

Left unplaced on purpose, and listed by the tool: preliminary contests the CMS filed as sites,
regional groups (NAQ, NAC, World Finals), and sites named after the contest whose venue is not
recorded here. They need a ruling or research, not a guess.

Also: Garden City (Nassau Community College) hung under New Jersey; it is in New York.

Usage: python3 tools/place_sites_2026_11_13.py [--write]
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalogue import Dumper, dump_series, load_series  # noqa: E402

DIV = re.compile(r"\s*[-–(]?\s*\b(?:div(?:ision|\.)?\s*(?:[123]|i{1,3})|d[123])\b\)?\s*$", re.I)

# cities the tree lacks: id -> (name, parent)
CITIES = {
    "us-bethlehem": ("Bethlehem", "us-pa"), "us-lewisburg": ("Lewisburg", "us-pa"), "us-hempstead": ("Hempstead", "us-ny"),
    "us-new-brunswick": ("New Brunswick", "us-nj"), "us-ithaca": ("Ithaca", "us-ny"), "us-middletown-ct": ("Middletown", "us-ct"),
    "us-mahwah": ("Mahwah", "us-nj"), "us-dobbs-ferry": ("Dobbs Ferry", "us-ny"), "us-bloomfield": ("Bloomfield", "us-nj"),
    "us-cleveland": ("Cleveland", "us-oh"), "us-claremore": ("Claremore", "us-ok"), "us-camarillo": ("Camarillo", "us-ca"),
    "us-moscow": ("Moscow", "us-id"), "ca-sydney": ("Sydney", "ca-ns"), "sv-soyapango": ("Soyapango", "sv"),
    "sv-san-miguel": ("San Miguel", "sv"), "ph-pasig": ("Pasig", "ph"), "jp-matsuyama": ("Matsuyama", "jp"),
}
REGIONS = {"us-id": ("Idaho", "us", "ID")}
# institutions the tree lacks: id -> (name, city, aliases)
INSTITUTIONS = {
    "us-conway-hendrix": ("Hendrix College", "us-conway", []),
    "us-bethlehem-lehigh": ("Lehigh University", "us-bethlehem", ["Lehigh"]),
    "us-lewisburg-bucknell": ("Bucknell University", "us-lewisburg", ["Bucknell"]),
    "us-hempstead-hofstra": ("Hofstra University", "us-hempstead", ["Hofstra"]),
    "us-new-brunswick-rutgers": ("Rutgers University", "us-new-brunswick", ["Rutgers"]),
    "us-ithaca-cornell": ("Cornell University", "us-ithaca", ["Cornell"]),
    "us-new-york-city-nyu": ("New York University", "us-new-york-city", ["NYU"]),
    "us-new-york-city-nyu-tandon": ("NYU Tandon School of Engineering", "us-new-york-city", ["Polytechnic University", "Poly"]),
    "us-middletown-ct-wesleyan": ("Wesleyan University", "us-middletown-ct", ["Wesleyan"]),
    "us-new-york-city-cooper-union": ("The Cooper Union", "us-new-york-city", ["Cooper Union"]),
    "us-mahwah-ramapo": ("Ramapo College of New Jersey", "us-mahwah", ["Ramapo"]),
    "us-new-haven-scsu": ("Southern Connecticut State University", "us-new-haven", ["SCSU"]),
    "us-new-york-city-yeshiva": ("Yeshiva University", "us-new-york-city", ["Yeshiva"]),
    "us-dobbs-ferry-mercy": ("Mercy University", "us-dobbs-ferry", ["Mercy", "Mercy College"]),
    "us-new-york-city-hunter": ("Hunter College", "us-new-york-city", ["Hunter"]),
    "us-bloomfield-college": ("Bloomfield College", "us-bloomfield", ["Bloomfield Colleg"]),
    "us-cleveland-case-western": ("Case Western Reserve University", "us-cleveland", []),
    "us-washington-gwu": ("George Washington University", "us-washington", []),
    "us-claremore-rogers-state": ("Rogers State University", "us-claremore", []),
    "us-camarillo-csuci": ("California State University Channel Islands", "us-camarillo", ["CSUCI", "Proctored Site - CSUCI"]),
    "us-moscow-idaho": ("University of Idaho", "us-moscow", []),
    "ca-sydney-cape-breton": ("Cape Breton University", "ca-sydney", ["Atlantic Preliminary (Cape Breton)"]),
    "sv-san-salvador-ufg": ("Universidad Francisco Gavidia", "sv-san-salvador", []),
    "sv-soyapango-don-bosco": ("Universidad Don Bosco", "sv-soyapango", []),
    "sv-san-miguel-univo": ("Universidad de Oriente (El Salvador)", "sv-san-miguel", []),
    "gt-guatemala-city-galileo": ("Universidad Galileo", "gt-guatemala-city", []),
    "gt-guatemala-city-uvg": ("Universidad del Valle de Guatemala", "gt-guatemala-city", ["Universidad del Valle GT"]),
    "ph-pasig-ua-p": ("University of Asia and the Pacific", "ph-pasig", []),
    "jp-matsuyama-ehime": ("Ehime University", "jp-matsuyama", []),
}
# site label (division label stripped) -> node, where the label itself is not a name or alias of the node.
# A (contest, label) key wins over a bare label.
PLACES = {
    "Drexel": "us-philadelphia-drexel", "Duke": "us-durham-duke", "NCC": "us-garden-city-nassau-community",
    "Sacred Heart": "us-fairfield-sacred-heart", "Touro": "us-new-york-city-touro",
    "University of Utah at Salt Lake City": "us-salt-lake-city-utah", "PuertoRican Site": "pr",
    ("gran-premio-centroamerica-2024", "Universidad de Oriente"): "sv-san-miguel-univo",
    ("gran-premio-centroamerica-2025", "Universidad de Oriente"): "sv-san-miguel-univo",
    ("gran-premio-centroamerica-2026", "Universidad de Oriente"): "sv-san-miguel-univo",
    ("pacnw-2009", "Northeast"): "us-moscow-idaho",                    # CMS location: University of Idaho
    ("korea-2004", "Asia - Seoul - Final Round"): "kr-seoul-kim-koo-museum",   # CMS location: Kim Koo Museum & Library
    ("manila-2004", "Asia - Manila - Final Round"): "ph-pasig-ua-p",   # CMS location: Univ of Asia & the Pacific
    ("japan-2004", "Asia - Ehime - Final Round"): "jp-matsuyama-ehime",
    ("amritapuri-2007", "Asia - Amritapuri On-Site Regional Contest"): "in-amritapuri-amrita-vishwa-vidyapeetham",
    ("amritapuri-2009", "Asia Amritapuri OnSite Regional Contest"): "in-amritapuri-amrita-vishwa-vidyapeetham",
    ("amritapuri-2011", "Asia-Amritapuri Combined On-site"): "in-amritapuri-amrita-vishwa-vidyapeetham",
    ("xian-2017", "Asia XiAnn On Site Regional Contest"): "cn-xian",
}
AMBIGUOUS = {"union"}   # a name that matches a node but could be another place (GNY "Union": Kean in Union, or UCNJ)
ADMIN = re.compile(
    r"^(unofficial|z+ site (for future use|to be used later)|guest_teams|any ?site.*|no site|site closed|g{4,}|x{4,}|"
    r"delete(_\d)*|ucf volunteer|nsa|upe|.*registration site|.*foreign team registrations?)$", re.I)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    loc_path = ROOT / "locations.yaml"
    hdr = "".join(l for l in loc_path.read_text().splitlines(keepends=True)[:2] if l.startswith("#"))
    loc_doc = yaml.safe_load(loc_path.read_text())
    nodes = loc_doc["locations"]
    by_id = {n["id"]: n for n in nodes}
    stats: Counter = Counter()

    def path(n):
        return (path(by_id[n["parent"]]) if n.get("parent") else ()) + (n["id"],)

    def add(node):
        if node["id"] in by_id:
            return
        assert node["parent"] in by_id, node
        by_id[node["id"]] = node
        key = path(node)
        at = next((i for i, n in enumerate(nodes) if path(n) > key), len(nodes))
        nodes.insert(at, node)
        stats[f"{node['type']} nodes added"] += 1

    for nid, (name, parent, code) in REGIONS.items():
        add({"id": nid, "name": name, "type": "region", "parent": parent, "code": code})
    for nid, (name, parent) in CITIES.items():
        add({"id": nid, "name": name, "type": "city", "parent": parent})
    for nid, (name, city, aliases) in INSTITUTIONS.items():
        add({"id": nid, "name": name, "type": "institution", "parent": city, **({"aliases": aliases} if aliases else {})})
    if by_id["us-garden-city"].get("parent") == "us-nj":
        by_id["us-garden-city"]["parent"] = "us-ny"
        nodes.remove(by_id["us-garden-city"])
        kids = [n for n in nodes if n.get("parent") == "us-garden-city"]
        for k in kids:
            nodes.remove(k)
        for n in [by_id["us-garden-city"]] + kids:
            key = path(n)
            nodes.insert(next((i for i, x in enumerate(nodes) if path(x) > key), len(nodes)), n)
        stats["Garden City moved from New Jersey to New York"] += 1

    names: dict = {}
    for n in nodes:
        for label in [n["name"]] + (n.get("aliases") or []):
            names.setdefault(label.lower(), []).append(n["id"])

    series = load_series()
    left, touched = [], set()
    for sid, doc in series.items():
        for c in doc["contests"]:
            for s in c.get("sites") or []:
                if s.get("location") or s.get("type") or not s.get("name"):
                    continue
                label = s["name"].strip()
                base = DIV.sub("", label).strip()
                nid = PLACES.get((c["id"], base)) or PLACES.get(base)
                if not nid and base.lower() not in AMBIGUOUS:
                    hits = names.get(base.lower()) or []
                    nid = hits[0] if len(hits) == 1 else None
                if nid:
                    keep = {k: s[k] for k in ("name", "date") if k in s}
                    if keep.get("name") in (by_id[nid]["name"],):
                        keep.pop("name")
                    s.clear()
                    s.update({"location": nid, **keep})
                    stats["sites placed" + (" (division label)" if base != label else "")] += 1
                    touched.add(sid)
                elif ADMIN.match(base):
                    keep = {k: s[k] for k in ("name", "date") if k in s}
                    s.clear()
                    s.update({**keep, "type": "administrative"})
                    stats["CMS groups marked administrative"] += 1
                    touched.add(sid)
                else:
                    left.append((c["id"], label))
    for k, v in sorted(stats.items()):
        print(f"{v:4d}  {k}")
    print(f"{len(left):4d}  left unplaced")
    for cid, label in left:
        print(f"        {cid}: {label}")
    if args.write:
        loc_path.write_text(hdr + yaml.dump(loc_doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
        for sid in sorted(touched):
            dump_series(sid, series[sid], "place_sites_2026_11_13.py")
        print(f"written: locations.yaml, {len(touched)} series files")
    else:
        print("(dry run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
