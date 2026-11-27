#!/usr/bin/env python3
"""Coverage: what we hold of each contest, one record per contest, worked out in one place.

Every page of the site, the validator and any report read coverage through `Coverage.record()`,
so a number means the same thing wherever it is shown (DEFINITIONS.md, Coverage).

    cov = Coverage(series_docs, sets, held=..., web_held=..., placed=...)
    r = cov.record(contest)

A record:

    results        the level we HOLD a copy of: scoreboard > standings > rankings > teams > none
    results_known  the level any source gives, held or not
    fetch          results_known when it is better than `results` (a copy is wanted), else ""
    frozen         "held" | "link only" | ""   a frozen scoreboard, beside the ladder, not on it
    partial        the held level is reached only through sources that cover a part of the contest
    set            the problem list: "listed" | "partly listed" | "count only" | "source only" | "missing"
    problems       {statement, data, solutions, package, editorial: all | some | link only | not held | not recorded}
    pmeta          {names, letters, short_names, uuids: all | some | missing}
    website        "held" | "no copy" | "no address" | "none"
    meta           {name, date, location, cms: have | missing | none}

"Held" always means we hold a copy (ruling of 2026-11-15): a source we only know the address of
is `link only` / `no copy` / `fetch`, never counted as held. The words of the answers (ruling of
2026-11-24): "none" always means there is none to have (grey, not wanted); a hole is "not held" for
material and "missing" for metadata (white, wanted); "wanted" is everything short of the best answer.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import RESULT_LADDER, archived, by_role, set_id_of, set_letters, sources  # noqa: E402
from resources import norm_key  # noqa: E402

LEVELS = RESULT_LADDER + ("none",)
LEVEL_LABEL = {"scoreboard": "scoreboard", "standings": "standings", "rankings": "rankings", "teams": "team list", "none": "not held"}
# (key, mark, plural label): the kinds of problem material. They are independent, except that a
# complete package implies statement, data and solutions.
COMPONENTS = (("statement", "St", "statements"), ("data", "D", "test data"), ("solutions", "So", "solutions"),
              ("package", "P", "packages"), ("editorial", "E", "editorial"))
IN_PACKAGE = ("statement", "data", "solutions")
STATES = ("all", "some", "link only", "not held", "not recorded")
PMETA = (("names", "names"), ("letters", "letters"), ("short_names", "short names"), ("uuids", "UUIDs"))
# Contest metadata that can be missing. What a contest advances to and the editions before and after it
# are not here (ruling of 2026-11-15): "none" is a valid answer for them, so they are never missing,
# only possibly wrong, and that is for fact-checking (review mode), not for coverage.
META = (("name", "name"), ("date", "full date"), ("location", "location"), ("cms", "CMS id"))
WEBSITE = ("held", "no copy", "no address", "none")
SET_STATES = ("listed", "partly listed", "count only", "source only", "missing")
DIVISION = re.compile(r"(?i)^\s*div(ision)?\.?\s*\w+\s*$")


def set_counts(doc: dict) -> tuple[int | None, int]:
    """(how many problems the contest had, when known; how many are listed by name)."""
    listed = len(doc.get("problems") or [])
    return doc.get("count") or (listed if listed and doc.get("complete") is not False else None), listed


def set_list_state(doc: dict) -> str:
    """'complete' | 'partial' | 'none' — is the set's problem list there?"""
    total, listed = set_counts(doc)
    if not listed:
        return "none"
    if doc.get("count") and listed >= doc["count"]:
        return "complete"   # as many listed as the contest had: complete, whatever a stale `complete: false` says
    return "partial" if doc.get("complete") is False or (total and listed < total) else "complete"


def contains(s: dict) -> set[str] | None:
    """What a problemset/problem source holds, with a package spelled out; None = not recorded."""
    if "contains" not in s:
        return None
    out = set(s["contains"] or [])
    if "package" in out:
        out.update(IN_PACKAGE)
    return out


def level_of(srcs: list[dict]) -> str:
    """The highest level of the results ladder among these sources."""
    for r in RESULT_LADDER:
        if any(r in s["roles"] for s in srcs):
            return r
    return "none"


def is_partial(srcs: list[dict], level: str) -> bool:
    """Do the sources at `level` cover only a part of the contest? Yes when every one carries a
    `scope`, unless the scopes are the divisions of the contest (two or more of them: together they
    are the whole)."""
    at = [s for s in srcs if level in s["roles"]]
    if not at or any(not s.get("scope") for s in at):
        return False
    scopes = {s["scope"] for s in at}
    return not (len(scopes) >= 2 and all(DIVISION.match(x) for x in scopes))


def _share(n: int, total: int) -> str:
    return "missing" if not n else "all" if n >= total else "some"


class Coverage:
    def __init__(self, series_docs: dict, sets: dict, held=None, web_held=None, placed=None):
        """`held(contest, source)`: do we hold a copy that is the document (default: any capture reference);
        `web_held(contest)`: do we hold the website (default: a held `web` source);
        `placed(contest)`: is it in the location tree (default: it has `sites`)."""
        self.sets = sets
        self.held = held or (lambda c, s: bool(archived(s)))
        self.web_held = web_held or (lambda c: any(self.held(c, s) for s in by_role(c, "web")))
        self.placed = placed or (lambda c: bool(c.get("sites")))
        self.contests: dict = {c["id"]: c for doc in series_docs.values() for c in doc["contests"]}
        self._rec: dict = {}
        self._set: dict = {}
        self._per: dict = {}
        self._addr: dict = {}

    # ---- results ----
    def results(self, c: dict) -> dict:
        srcs = sources(c)
        mine = [s for s in srcs if self.held(c, s)]
        held, known = level_of(mine), level_of(srcs)
        frozen = by_role(c, "frozen_scoreboard")
        return {"results": held, "results_known": known,
                "fetch": known if LEVELS.index(known) < LEVELS.index(held) else "",
                "frozen": "held" if any(self.held(c, s) for s in frozen) else "link only" if frozen else "",
                "partial": held != "none" and is_partial(mine, held)}

    # ---- problems ----
    @staticmethod
    def _counts(s: dict) -> bool:
        """Does a held copy of this source give its material? Not when it is a problem set on an online
        judge: that copy is the judge's list page. A problem's own page or statement file on a judge
        does (ruled 2026-11-22/23: where the material comes from does not matter), and so does the set's
        statement file kept there."""
        if not s.get("judge") or "problemset" not in s["roles"]:
            return True
        # the set's statement file kept on a judge (a Codeforces gym's attached PDF) is the material itself (2026-11-27)
        return bool(re.search(r"\.(pdf|ps|zip|docx?|tgz|tar\.gz)$", urlsplit(s["url"]).path, re.I))

    def _problem_of(self, doc: dict, c: dict, s: dict):
        """The problem a per-problem source is about: by its address (one of the problem's judge links),
        else by its letter in that contest, else the source itself."""
        k = id(doc)
        if k not in self._addr:
            self._addr[k] = {norm_key(u): p["id"] for p in doc.get("problems") or [] for j in p.get("judges") or []
                             for u in (j.get("statement_url"), j.get("url")) if u}
        return (self._addr[k].get(norm_key(s["url"])) or set_letters(doc, c["id"]).get(str(s.get("problem")))
                or (c["id"], s.get("problem") or s["url"]))

    def statements_held(self, doc: dict) -> set:
        """The problems of a set whose statement we hold as a file or page of its own."""
        k = id(doc)
        if k not in self._per:
            members = [self.contests[m["contest"]] for m in doc.get("contests") or [] if m["contest"] in self.contests]
            self._per[k] = {self._problem_of(doc, c, s) for c in members for s in sources(c)
                            if "problem" in s["roles"] and "problemset" not in s["roles"] and "statement" in (contains(s) or ())
                            and self.held(c, s)}
        return self._per[k]

    def _material(self, doc: dict, members: list[dict]) -> dict:
        """{component: state} for a set (or, with doc {}, for one contest that has no set)."""
        srcs = [(c, s) for c in members for s in sources(c)]
        psrc = [(c, s) for c, s in srcs if {"problemset", "problem"} & set(s["roles"])]
        unknown = any(contains(s) is None for _c, s in psrc)
        total = set_counts(doc)[0]
        out = {}
        for key in ("statement", "data", "solutions", "package"):
            arch = doc.get(key)
            if key in IN_PACKAGE and doc.get("package") in ("full", "partial") and arch != "full":
                arch = doc["package"]   # a complete package holds its statement, data and solutions
            giving = [(c, s) for c, s in psrc if key in (contains(s) or ())]
            mine = [(c, s) for c, s in giving if self._counts(s) and self.held(c, s)]
            singles = [(c, s) for c, s in mine if "problemset" not in s["roles"]]
            # per problem: files or pages of their own; the set is complete when every problem has one
            per = len({self._problem_of(doc, c, s) for c, s in singles})
            if arch == "full" or len(mine) > len(singles) or (total and per >= total):
                out[key] = "all"
            elif arch == "partial" or mine:
                out[key] = "some"
            elif giving:
                out[key] = "link only"
            else:
                out[key] = "not recorded" if unknown else "not held"
        eds = [(c, s) for c, s in srcs if "editorial" in s["roles"]]
        out["editorial"] = "all" if any(self.held(c, s) for c, s in eds) else "link only" if eds else "not held"
        return out

    def set_record(self, sid: str) -> dict:
        """{component: state} for a problem set: what the problem archive holds, or what a source
        of any contest that used the set holds."""
        if sid not in self._set:
            doc = self.sets.get(sid) or {}
            members = [self.contests[m["contest"]] for m in doc.get("contests") or [] if m["contest"] in self.contests]
            self._set[sid] = self._material(doc, members)
        return self._set[sid]

    def problems(self, c: dict) -> dict:
        sid = set_id_of(c)
        doc = self.sets.get(sid) if sid else None
        if doc is None:
            has = any({"problemset", "problem"} & set(s["roles"]) for s in sources(c))
            return {"set": "source only" if has else "missing", "problems": self._material({}, [c]),
                    "pmeta": {k: "missing" for k, _l in PMETA}}
        probs = doc.get("problems") or []
        n = len(probs)
        letters = set(set_letters(doc, c["id"]).values())
        labels = next((m.get("labels") for m in doc.get("contests") or [] if m.get("contest") == c["id"]), None) or []
        state = set_list_state(doc)
        pmeta = {"names": {"complete": "all", "partial": "some", "none": "missing"}[state],
                 # the letters alone (`labels`, read off a scoreboard) count when the problems are not listed
                 "letters": ("all" if state == "complete" and all(p["id"] in letters for p in probs) else "some") if letters
                 else ("all" if not probs and len(labels) == (doc.get("count") or len(labels)) else "some") if labels else "missing",
                 "short_names": _share(sum(1 for p in probs if p.get("short_name")), n) if state == "complete" or not n
                 else ("some" if any(p.get("short_name") for p in probs) else "missing"),
                 "uuids": _share(sum(1 for p in probs if p.get("uuid")), n) if state == "complete" or not n
                 else ("some" if any(p.get("uuid") for p in probs) else "missing")}
        return {"set": {"complete": "listed", "partial": "partly listed", "none": "count only"}[state],
                "problems": self.set_record(sid), "pmeta": pmeta}

    # ---- website, metadata ----
    def website(self, c: dict) -> str:
        if self.web_held(c):
            return "held"
        if by_role(c, "web"):
            return "no copy"
        return "none" if "web" in (c.get("none") or []) else "no address"

    def meta(self, c: dict) -> dict:
        return {"name": "have" if c.get("name") else "missing",
                "date": "have" if len(str(c.get("date") or "")) == 10 else "missing",
                "location": "have" if self.placed(c) else "missing",
                # a value = have; [] = looked, the CMS has no entry for it; absent = not researched
                "cms": "have" if c.get("cms_ids") else "none" if "cms_ids" in c else "missing"}

    def record(self, c: dict) -> dict:
        cid = c["id"]
        if cid not in self._rec:
            self._rec[cid] = {**self.results(c), **self.problems(c), "website": self.website(c), "meta": self.meta(c)}
        return self._rec[cid]


# ---- facets: every coverage question in one list ----
# A FACET is one question about a contest with a few answers, best first. Every view (the bars, the
# matrices, the grid) is drawn from this list, so they all mean the same thing.
#   key      the facet's name in page addresses
#   label    what it is called on a page
#   group    the kind of content it belongs to
#   states   its answers, best first
#   good     how many of the first answers count as held (the headline share of the facet)
THREE = ("all", "some", "missing")
HAVE = ("have", "missing", "none")
# Four kinds of content: results, problems, website, contest metadata. Problems come in two groups:
# what the catalogue records about them (problem metadata) and the material we hold.
FACETS = (
    ("results", "results", "Results", tuple(LEVEL_LABEL[k] for k in LEVELS), 1),
    ("list", "problem list", "Problem metadata", SET_STATES, 1),
    *((k, lab, "Problem metadata", THREE, 1) for k, lab in PMETA),
    *((k, lab, "Problems", STATES, 1) for k, _m, lab in COMPONENTS),
    ("website", "website", "Website", WEBSITE, 1),
    *((k, lab, "Contest metadata", HAVE, 1) for k, lab in META),
)
FACET = {f[0]: f for f in FACETS}
_COMP = {k for k, *_ in COMPONENTS}
_PMETA = {k for k, _l in PMETA}
_META = {k for k, _l in META}


def state(r: dict, key: str) -> str:
    """The answer of a coverage record to one facet."""
    if key == "results":
        return LEVEL_LABEL[r["results"]]
    if key == "list":
        return r["set"]
    if key == "website":
        return r["website"]
    if key in _COMP:
        return r["problems"][key]
    if key in _PMETA:
        return r["pmeta"][key]
    return r["meta"][key]


def states(r: dict) -> dict:
    """{facet key: answer} for every facet of a record."""
    return {f[0]: state(r, f[0]) for f in FACETS}


def encode(r: dict) -> str:
    """A record as one digit per facet (the index of its answer), in FACETS order."""
    return "".join(str(f[3].index(state(r, f[0]))) for f in FACETS)


def main() -> int:
    """Print the coverage of the catalogue as it stands (captures as the catalogue points at them;
    the site adds what the archive index knows about each copy)."""
    from collections import Counter
    from catalogue import load_series, load_sets
    series = load_series()
    cov = Coverage(series, load_sets())
    ran = [c for d in series.values() for c in d["contests"] if c.get("status") != "upcoming"]
    recs = [cov.record(c) for c in ran]
    print(f"{len(ran)} contests ran — counted as the catalogue points at copies (`archived:`); the site counts what the archive index "
          "says of each copy, so its numbers differ (build_site.py is the reference)")
    print("results held  ", dict(Counter(r["results"] for r in recs)))
    print("results known ", dict(Counter(r["results_known"] for r in recs)))
    print("frozen        ", dict(Counter(r["frozen"] or "-" for r in recs)), " partial", sum(r["partial"] for r in recs))
    for k, _m, lab in COMPONENTS:
        print(f"{lab:14}", dict(Counter(r["problems"][k] for r in recs)))
    for k, lab in PMETA:
        print(f"{lab:14}", dict(Counter(r["pmeta"][k] for r in recs)))
    print("website       ", dict(Counter(r["website"] for r in recs)))
    for k, lab in META:
        print(f"{lab:14}", dict(Counter(r["meta"][k] for r in recs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
