#!/usr/bin/env python3
"""Catalogue access helpers: the `sources:` model (DEFINITIONS.md, Resources).

A contest's addresses live in one list, `sources:`, each entry one URL with the
roles it serves:

    sources:
    - url: http://www.cs.colorado.edu/users/kena/acmpc/results.html
      roles: [scoreboard, problemset]
      as_of: '20040117'            # optional: the content meant is what the address served then
      also_at: [http://mirror/..., {url: ..., as_of: ...}]  # other addresses serving the same content
      judge: baekjoon              # judge_page only
      archived: [rmc/rmc-2000/scoreboard/2026-09-07-.../page.html]   # every capture of this address
      url_state: dead              # health of the address at url_checked
      url_checked: '2026-11-02'
      note: ...
    none: [teams]                  # roles confirmed to have no source

Absence of a role in both `sources` and `none` means "not yet researched".
Every tool reads the catalogue through these helpers so the shape lives in one place.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from resources import norm_key  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

ROLES = ("web", "scoreboard", "frozen_scoreboard", "standings", "rankings",
         "icpc_standings", "teams", "problemset", "problem", "judge_page")
RESULT_ROLES = ("scoreboard", "frozen_scoreboard", "standings", "rankings", "icpc_standings")
RANK = {r: i for i, r in enumerate(ROLES)}
HEADER = "# Maintained in-repo; last bulk edit: tools/{tool}.\n"


class Dumper(yaml.SafeDumper):
    pass


Dumper.add_representer(type(None), lambda d, v: d.represent_scalar("tag:yaml.org,2002:null", "null"))


def load_series() -> dict[str, dict]:
    """{series id: document} for every series/*.yaml, sorted by id."""
    return {f.stem: yaml.safe_load(f.read_text()) for f in sorted((ROOT / "series").glob("*.yaml"))}


def load_contests() -> dict[str, dict]:
    """{contest id: entry}; each entry gets `_series` set to its series id."""
    out = {}
    for sid, doc in load_series().items():
        for c in doc["contests"]:
            c["_series"] = sid
            out[c["id"]] = c
    return out


def load_sets() -> dict[str, dict]:
    """{set id: document} for every problemsets/<set-id>.yaml (DEFINITIONS.md, Problems)."""
    pdir = ROOT / "problemsets"
    if not pdir.exists():
        return {}
    return {f.stem: yaml.safe_load(f.read_text()) for f in sorted(pdir.glob("*.yaml"))}


def load_judges() -> dict[str, dict]:
    """{judge id: entry} from judges.yaml, the registry of online judges."""
    p = ROOT / "judges.yaml"
    if not p.exists():
        return {}
    return {j["id"]: j for j in (yaml.safe_load(p.read_text()) or {}).get("judges") or []}


def load_locations() -> dict[str, dict]:
    """{node id: node} from locations.yaml, the one location tree (DEFINITIONS.md, Locations)."""
    p = ROOT / "locations.yaml"
    if not p.exists():
        return {}
    return {n["id"]: n for n in (yaml.safe_load(p.read_text()) or {}).get("locations") or []}


def location_chain(nodes: dict[str, dict], lid: str) -> list[dict]:
    """[node, its parent, ..., country] for a location id; [] when the id is unknown."""
    out, seen = [], set()
    while lid and lid in nodes and lid not in seen:
        seen.add(lid)
        out.append(nodes[lid])
        lid = nodes[lid].get("parent")
    return out


def load_non_mainline() -> list[dict]:
    """The registry of real contests outside the hierarchy (registry/non-mainline.yaml)."""
    p = ROOT / "registry" / "non-mainline.yaml"
    if not p.exists():
        return []
    return (yaml.safe_load(p.read_text()) or {}).get("non_mainline_contests") or []


def set_kind_count(doc: dict, kind: str) -> int:
    """How many problems of a set have material of `kind` (statement/data/solutions/package):
    the set's count for `full`, the recorded number for `partial`, 0 otherwise."""
    st = doc.get(kind)
    cnt = doc.get("count") or len(doc.get("problems") or [])
    if st == "full":
        return cnt
    if st == "partial":
        return (doc.get("counts") or {}).get(kind) or 0
    return 0


def set_id_of(c: dict) -> str | None:
    """The id of the problem set a contest used (`problems: {set: ...}`), or None."""
    return (c.get("problems") or {}).get("set")


def set_of(c: dict, sets: dict[str, dict]) -> dict | None:
    """The problem-set document a contest used, looked up in `sets` (load_sets())."""
    sid = set_id_of(c)
    return sets.get(sid) if sid else None


def set_letters(doc: dict, cid: str) -> dict[str, str]:
    """{letter: problem id} as used by contest `cid` in set `doc` ({} when unknown)."""
    for m in doc.get("contests") or []:
        if m.get("contest") == cid:
            return m.get("letters") or {}
    return {}


def dump_series(sid: str, doc: dict, tool: str) -> None:
    body = yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100)
    (ROOT / "series" / f"{sid}.yaml").write_text(HEADER.format(tool=tool) + body)


def sources(c: dict) -> list[dict]:
    return c.get("sources") or []


def by_role(c: dict, role: str) -> list[dict]:
    return [s for s in sources(c) if role in s["roles"]]


def has_role(c: dict, role: str) -> bool:
    return any(role in s["roles"] for s in sources(c))


def researched(c: dict, role: str) -> bool:
    """A role is researched when it has a source or is listed under `none`."""
    return has_role(c, role) or role in (c.get("none") or [])


def primary_role(s: dict) -> str:
    return min(s["roles"], key=lambda r: RANK[r])


def best_result(c: dict) -> tuple[str, list[dict]] | None:
    """(role, sources) for the most informative result role present, else None."""
    for role in RESULT_ROLES:
        lst = by_role(c, role)
        if lst:
            return role, lst
    return None


def find_source(c: dict, url: str) -> dict | None:
    k = norm_key(url)
    for s in sources(c):
        if norm_key(s["url"]) == k:
            return s
    return None


def add_source(c: dict, url: str, role: str, **fields) -> tuple[dict, bool]:
    """Add `role` at `url`, merging into an existing source of the same address.
    Returns (source, changed). Extra fields (as_of, note, judge, ...) are set only
    when the source does not already carry them."""
    s = find_source(c, url)
    changed = False
    if s is None:
        s = {"url": url, "roles": [role]}
        for k, v in fields.items():
            if v not in (None, "", []):
                s[k] = v
        c.setdefault("sources", []).append(s)
        sort_sources(c)
        changed = True
    else:
        if role not in s["roles"]:
            s["roles"].append(role)
            s["roles"].sort(key=lambda r: RANK[r])
            changed = True
        for k, v in fields.items():
            if k not in s and v not in (None, "", []):
                s[k] = v
                changed = True
    none = c.get("none")
    if none and role in none:
        none.remove(role)
        if not none:
            del c["none"]
        changed = True
    return s, changed


def archived(s: dict) -> list[str]:
    """Capture references of a source (always a list; tolerates a legacy scalar)."""
    a = s.get("archived")
    return [] if not a else (a if isinstance(a, list) else [a])


def add_archived(s: dict, path: str) -> bool:
    lst = archived(s)
    if path in lst:
        return False
    s["archived"] = lst + [path]
    return True


def also_at(s: dict) -> list[dict]:
    """also_at entries normalised to dicts {url, as_of?, note?}."""
    return [a if isinstance(a, dict) else {"url": a} for a in s.get("also_at") or []]


def sort_sources(c: dict) -> None:
    """Stable order: by the primary role's rank, then by original position."""
    lst = c.get("sources")
    if lst:
        lst.sort(key=lambda s: RANK[primary_role(s)])


def normalise_source(s: dict) -> dict:
    """Canonical key order for a source mapping."""
    order = ("url", "roles", "scope", "judge", "as_of", "also_at", "archived", "fetched",
             "url_state", "url_checked", "note")
    out = {k: s[k] for k in order if k in s}
    for k in s:
        if k not in out:
            out[k] = s[k]
    return out


CONTEST_KEY_ORDER = ("id", "status", "season", "name", "date", "location", "venue", "cms_ids",
                     "sites", "parent", "next", "subset_of", "sources", "none", "problems",
                     "provenance", "notes", "reason")


def normalise_contest(c: dict) -> dict:
    out = {k: c[k] for k in CONTEST_KEY_ORDER if k in c}
    for k in c:
        if k not in out and not k.startswith("_"):
            out[k] = c[k]
    if "sources" in out:
        out["sources"] = [normalise_source(s) for s in out["sources"]]
    return out
