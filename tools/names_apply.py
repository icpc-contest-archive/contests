#!/usr/bin/env python3
"""Apply the problem names read from held problem-set documents (tools/names_pack.py, names_rubric.md).

  python3 tools/names_apply.py --run ../_names/run1 [--date YYYY-MM-DD] [--report NAME] [--write]

Each <run>/<contest>/result.json is a reader's list of the contest's problems (letter, name), whether
it is complete, and how sure the reader is. A result is applied when nothing about it needs a
ruling:

  - it is high or medium confidence (medium: the names come from a judge's list, not the organisers'
    document), and the reader did tie the document to this contest (HOLD lists the ones that did not);
  - where the catalogue already lists a problem under a letter, the document's name is the same
    (spelling aside); every problem the catalogue lists is in a complete result; a set that lists
    problems shares at least one with the document.

A set shared by several contests takes each member's result in turn, the surest first (high before
medium, complete before partial), so a second reading that disagrees with the first is held. A medium
result is taken as the whole list only when the catalogue has the same count or its letters run
A, B, C … without a gap; otherwise its names are added and the list stays partial.

Rulings of 2026-11-15 (Fredrik), carried by the tables below:

  1. the statement's title replaces a judge's short one; the old title is kept in `other_names`
     (RENAME). Where the catalogue's name is the archive package's (the problem has a uuid) or the
     fuller one, it stays and the document's title goes to `other_names` (ALSO);
  2. a problem the complete document does not have is dropped from the set (DROP) — only problems
     known from a judge alone; one with a uuid is in the problem archive and is held for a look;
  3. the document's count wins for a high-confidence reading (and the COUNT_OK ones, checked by hand);
  4. `count` is the number of distinct problems; a contest with divisions keeps its letters per
     division (`divisions:` on the set's contest entry).

Applying: a problem the set does not list is added (id p-sha1(set|letter|name)[:8]); a listed
problem gets its letter when it had none; a complete result sets `count` and clears
`complete: false`; a partial one adds what it has and leaves the set marked incomplete. Apart from
RENAME, names the catalogue already has are never rewritten. A contest with no set gets one of its
own id. Everything else is listed in the report with what was read, for ruling.
Without --write nothing is changed and the report goes to <run>/report-dry-run.md; with --write it
goes to reports/<NAME or names-from-documents-<date>.md>.
"""
from __future__ import annotations
import argparse, collections, datetime, difflib, json, re, sys, unicodedata
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from catalogue import ROOT, Dumper, dump_series, load_series, load_sets  # noqa: E402
from mine_judge_links import LETTER, dump_set, pid  # noqa: E402

DIV_LETTER = re.compile(r"^[A-Z]{1,2}[0-9]?$|^[0-9]{1,2}$")   # a division may run past Z (PacNW 2020: R … AH)

# The reader could not tie the document to the contest, or the reading needs a look first.
HOLD = {
    # hungary-2012, -2014 and -2016 were held here until the organisers' own pages settled it (2026-11-15):
    # people.inf.elte.hu/bzsr/acm/ lists acmYYYY.pdf as each year's "feladatsor" (problem set) and says the
    # problems are on the UVa judge; the 2011 scoreboard names eight problems, all in acm2011.pdf; ELTE's
    # 2016 results post links acm2016.pdf as that year's problems. The national contest reused other
    # regionals' problems, so a PDF of them is the contest's set.
    "brazil-first-phase-1997": "the document is headed South American Regional, 13 December 1997, not First Phase",
    "ecna-1985": "the names are file names from an index (erno, lemon …), not titles",
    "ecna-1987": "the names are file names from an index (anagram, darts …), not titles",
    "shanghai-2022": "the page is the East Continent Final 2022 = aec-2022 (CMS 5537, 298 teams); shanghai-2022 is CMS 6160, an empty entry of the same date",
    "nerc-2020": "two problem sets on two dates (online 2020-12-13, onsite 2021-04-04): one contest with two rounds, or two contests?",
    "pacnw-2019": "seven Division 1 titles in the organisers' PDF differ from the catalogue's, which are the titles the same problems carry at SE USA 2019",
    "bapc-prelims-2015": "ten of the eleven titles in the PDF (Board Game 1, Video Game …) differ from the judge's (Cheating Knight, Chess Tournament …)",
    "central-america-1998": "the document's six problems are none of them the one a judge files under this contest (Visible Squares)",
    "central-america-2002": "the document's five problems are none of them the one a judge files under this contest (This Sentence is False)",
}
# Contests without a set that sat one set together: the set to open for them, as in earlier years.
NEW_SHARED = {"brazil-2026": "latam-2026", "caribbean-2026": "latam-2026", "central-america-2026": "latam-2026"}
NEW_NAME = {"latam-2026": "Latin America regional 2026"}
# Ruling 1 — set: {the catalogue's title: the statement's title}. The old title goes to other_names.
RENAME = {
    "bapc-prelims-2013": {"MI6": "Identification Codes"},
    "latam-2010": {"Tautogram": "Flowers Flourish from France"},
    "korea-2006": {"DNA": "DNA Consensus String"},
    "neerc-2007": {"DFA": "Language Recognition"},
    "neerc-2008": {"MEGACITY": "Drive through MegaCity"},
    "pacnw-2012": {"ROT13": "Tongues"},
    "thailand-2013": {"SSD": "Seven Segment Display"},
    "latam-2008": {"DNA Sequences": "DNA Subsequences"},
    "north-russia-2011": {"Galaxy": "Galaxy Interconnection"},
    "north-russia-2012": {"Final": "Final Standings"},
}
# Ruling 1 where the set lists the problem twice, once under each title — set: [(the statement's title, the judge's)].
# One row is kept under the statement's title; the other's judge links and id (as an alias) are folded into it.
MERGE = {
    "seusa-2017": [("Exciting Finish!", "Enlarging Enthusiasm"), ("Security Badges", "Security Badge")],
    "seusa-2018": [("Troop Mobilization", "Mobilization")],
}
# The same problem under two titles where the catalogue's stays — set: {the catalogue's title: the document's}.
ALSO = {
    "ecna-1997": {"Word Search Wonder": "Word Search"},              # archive package name; the document is an index
    "ncna-1995": {"HTML": "HTML Syntax Checking"},                   # archive package name
    "nena-2013": {"Palindromes in crosswords": "Palindrome", "Robot in a Maze": "Maze"},   # archive package names
    "socal-2019": {"ReMorse": "Morse Redux"},                        # archive package name
    "scusa-2001": {"Frogger's For Dinner": "Frogger"},               # the organisers' page is a list of short titles
}
# Ruling 2 — set: problems a complete document does not have (known from a judge alone).
DROP = {
    "latam-2011": ["Gates", "Game"],
    "latam-2015": ["Competition"],
    "thailand-2011": ["Line of Best Fit", "Software Licenses"],
}
# Ruling 3 — medium readings whose count was checked against the organisers' own files by hand.
COUNT_OK = {
    "pacnw-2007": "the organisers' zip holds statements a–k",
    "pacnw-2010": "the organisers' zip holds statements a–k and a practice problem",
    "nzpc-2010": "the organisers' PDF has problems A–P",
    "hungary-2014": "the organisers' problem-set PDF has nine statements",
    "hungary-2016": "the organisers' problem-set PDF has ten statements",
}
# The document numbers its problems where the catalogue has a judge's letters: the document's numbering is taken.
RELETTER = {"xian-2002"}
RANK = {"high": 0, "medium": 1}


def norm(name: str) -> str:
    """A name for comparing: case, accents, quotes, dashes and spacing aside."""
    t = unicodedata.normalize("NFKD", name or "").casefold()
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"[\W_]+", "", t.replace("×", "x"))


def same(a: str, b: str) -> bool:
    x, y = norm(a), norm(b)
    return bool(x) and (x == y or difflib.SequenceMatcher(None, x, y).ratio() >= 0.9)


def titles(row: dict) -> list[str]:
    return [row["name"], *(row.get("other_names") or [])]


def in_a_row(letters: list) -> bool:
    """A, B, C … or 1, 2, 3 … with none missing."""
    ls = [str(x) for x in letters]
    if not ls or any(x == "None" for x in ls):
        return False
    return sorted(ls) == [chr(65 + i) for i in range(len(ls))] or sorted(ls, key=lambda x: (len(x), x)) == [str(i + 1) for i in range(len(ls))]


def div_name(d) -> str:
    t = str(d).strip()
    m = re.match(r"(?i)^div(?:ision)?\.?\s*(I{1,3}|[0-9])$", t)
    if m:
        v = m.group(1).upper()
        return "Division " + {"I": "1", "II": "2", "III": "3"}.get(v, v)
    m = re.match(r"^([0-9])\.\s*krug$", t)   # Croatian: round
    return "Round " + m.group(1) if m else t


def write_set(f: Path, before: str | None, doc: dict) -> None:
    """Write a set file in the form it was in: the writer's (dump_set) or a plain dump in the file's own key order."""
    if before is not None:
        head, _, rest = before.partition("\n")
        old = yaml.safe_load(before)
        if head.startswith("#") and rest == yaml.dump(old, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100) and before != dump_set(old):
            f.write_text(head + "\n" + yaml.dump(doc, Dumper=Dumper, sort_keys=False, allow_unicode=True, width=100))
            return
    f.write_text(dump_set(doc))


def judge_urls(row: dict) -> str:
    return ", ".join(j["url"] for j in row.get("judges") or []) or "no judge link"


def rulings(sid: str, doc: dict, date: str) -> list[str]:
    """RENAME, ALSO and DROP on a working copy of the set; what was done, in words."""
    done, rows = [], doc.get("problems") or []
    for title, other in MERGE.get(sid) or []:
        a = next((x for x in rows if x["name"] == title), None)
        b = next((x for x in rows if x["name"] == other), None)
        if a is None or b is None:
            continue
        bare = lambda x: not (x.get("uuid") or x.get("judges") or x.get("have") or x.get("aliases"))  # noqa: E731
        keep, fold = (b, a) if bare(a) and not bare(b) else (a, b)
        keep["name"] = title
        keep["other_names"] = [t for t in dict.fromkeys([*(keep.get("other_names") or []), *(fold.get("other_names") or []), other]) if t != title]
        if fold.get("judges"):
            keep["judges"] = [*(keep.get("judges") or []), *fold["judges"]]
        if not bare(fold):
            keep["aliases"] = [*(keep.get("aliases") or []), fold["id"], *(fold.get("aliases") or [])]
        rows.remove(fold)
        for e in doc.get("contests") or []:
            for lm in [e.get("letters") or {}, *(e.get("divisions") or {}).values()]:
                for L in [L for L, p in lm.items() if p == fold["id"]]:
                    if keep["id"] in lm.values():
                        del lm[L]
                    else:
                        lm[L] = keep["id"]
        done.append(f"“{other}” and “{title}” were one problem listed twice: now one, under the statement's title")
    for old, new in (RENAME.get(sid) or {}).items():
        for x in rows:
            if x["name"] == old:
                x["name"] = new
                x["other_names"] = [*(x.get("other_names") or []), old]
                done.append(f"“{old}” renamed “{new}”, the statement's title")
    for name, other in (ALSO.get(sid) or {}).items():
        for x in rows:
            if x["name"] == name and other not in (x.get("other_names") or []):
                x["other_names"] = [*(x.get("other_names") or []), other]
                done.append(f"“{name}” is also “{other}” in the document")
    gone = [x for x in rows if x["name"] in (DROP.get(sid) or []) and not x.get("uuid")]
    if gone:
        ids = {x["id"] for x in gone}
        doc["problems"] = [x for x in rows if x["id"] not in ids]
        for e in doc.get("contests") or []:
            for lm in [e.get("letters") or {}, *(e.get("divisions") or {}).values()]:
                for L in [L for L, p in lm.items() if p in ids]:
                    del lm[L]
            if "letters" in e and not e["letters"]:
                del e["letters"]
        what = "; ".join(f"{x['name']} ({judge_urls(x)})" for x in gone)
        done.append(f"dropped, not in the organisers' problem set: {what}")
        doc.setdefault("provenance", []).append(f"dropped as not part of the set (ruling {date}; on a judge only, not in the organisers' document): {what}")
    return done


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--report", help="file name under reports/ for the written run")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    run = Path(a.run)
    series, sets = load_series(), load_sets()
    where = {c["id"]: (sid, c) for sid, doc in series.items() for c in doc["contests"]}
    rep = collections.defaultdict(list)
    changed, touched_series, stats = {}, set(), collections.Counter()
    results = sorted(run.glob("*/result.json"))
    loaded = []
    for rf in results:
        try:
            loaded.append((rf.parent.name, json.loads(rf.read_text()), json.loads((rf.parent / "pack.json").read_text())))
        except Exception as e:  # noqa: BLE001
            rep["result could not be read"].append(f"{rf.parent.name}: {e}")
    loaded.sort(key=lambda t: (RANK.get(t[1].get("confidence"), 2), not t[1].get("complete"), t[0]))
    for cid, r, pack in loaded:
        probs = [p for p in r.get("problems") or [] if (p.get("name") or "").strip()]
        read = " | ".join(f"{p.get('letter') or '?'} {p['name'].strip()}" for p in probs)
        line = f"{cid}: {len(probs)} read" + (", complete" if r.get("complete") else ", partial") + f", {r.get('confidence')}"
        note = (" — " + r["notes"].strip()) if (r.get("notes") or "").strip() else ""

        def hold(why: str, more: str = "") -> None:
            rep[f"for ruling: {why}"].append(f"{line}{(' [' + more + ']') if more else ''}{note}\n  read: {read}")
        if not probs:
            rep["nothing read (the document has no names, is broken, or is another contest's)"].append(f"{line}{note}")
            continue
        if cid not in where or where[cid][1].get("status") == "upcoming":
            hold("contest not in the catalogue, or it has not run")
            continue
        ser, c = where[cid]
        div = any(p.get("division") for p in probs)
        if div and not all(p.get("division") for p in probs):
            hold("some problems have a division and some have none")
            continue
        letters_read = [p.get("letter") for p in probs]
        if not div and (any(L is not None and not LETTER.match(str(L)) for L in letters_read)
                        or len({L for L in letters_read if L}) != len([L for L in letters_read if L])):
            hold("letters are not plain or repeat")
            continue
        sid = (c.get("problems") or {}).get("set")
        doc = sets.get(sid) if sid else None
        shared = doc is not None and len(doc.get("contests") or []) > 1
        conf, complete = r.get("confidence"), bool(r.get("complete"))
        if cid in HOLD:
            hold("the document may not be this contest's, or the reading needs a look", HOLD[cid])
            continue
        if conf == "low":
            hold("low confidence")
            continue
        if conf not in ("high", "medium"):
            hold("no confidence given")
            continue
        sure = conf == "high" or cid in COUNT_OK
        if not div and conf == "medium" and complete and not (cid in COUNT_OK or (doc or {}).get("count") == len(probs) or in_a_row(letters_read)):
            complete = False   # a judge's list without letters in a row: its names, not its count
        new_set = doc is None
        if new_set:
            sid = NEW_SHARED.get(cid, cid)
            if sid in sets and cid not in NEW_SHARED:
                hold("the contest has no set and its id is taken by another set")
                continue
            doc = sets.get(sid) or {"id": sid, **({"name": NEW_NAME[sid]} if sid in NEW_NAME else {}),
                                    "contests": [{"contest": cid}], "problems": [], "provenance": []}
            shared = cid in NEW_SHARED
        before = json.dumps(doc, sort_keys=True, ensure_ascii=False)
        doc = json.loads(json.dumps(doc))   # work on a copy: nothing is kept unless the whole result applies
        was_whole = doc.get("complete") is not False and bool(doc.get("count")) and doc["count"] == len(doc.get("problems") or [])
        ruled = rulings(sid, doc, a.date)
        entry = next((e for e in doc["contests"] if e["contest"] == cid), None)
        if entry is None and new_set and cid in NEW_SHARED:
            entry = {"contest": cid}
            doc["contests"].append(entry)
        if entry is None:
            hold("the set does not list this contest")
            continue
        rows = doc.setdefault("problems", [])
        was = {p["id"] for p in rows}
        by_id = {p["id"]: p for p in rows}
        matched, added, lettered, spelled, clash = set(), 0, 0, [], None

        def find(name: str) -> list:
            return ([x for x in rows if x["id"] not in matched and any(norm(t) == norm(name) for t in titles(x))]
                    or [x for x in rows if x["id"] not in matched and any(same(t, name) for t in titles(x))])

        def add(name: str, L):
            i = pid(None, sid, L, name)
            if i in by_id:
                return None
            e = {"id": i, "name": name}
            rows.append(e); by_id[i] = e   # noqa: E702
            return e

        if div:
            # distinct problems in the order read; each division's own letters
            keys, dmaps, maps = collections.OrderedDict(), collections.OrderedDict(), collections.OrderedDict()
            for p in probs:
                k = norm(p["name"])
                keys.setdefault(k, p["name"].strip())
                m = dmaps.setdefault(div_name(p["division"]), {})
                if p.get("letter") is not None:
                    L = str(p["letter"])
                    if not DIV_LETTER.match(L) or L in m:
                        clash = f"letter {L} of {div_name(p['division'])} is not plain or repeats"
                        break
                    m[L] = k
            pid_of = {}
            for k, name in keys.items():
                if clash:
                    break
                cands = find(name)
                e = cands[0] if cands else None
                if e is None:
                    e = add(name, None)
                    if e is None:
                        clash = f"“{name}” would get an id the set already uses"
                        break
                    added += 1
                elif e["name"] != name and name not in (e.get("other_names") or []):
                    spelled.append(f"{e['name']} / {name}")
                matched.add(e["id"])
                pid_of[k] = e["id"]
            if not clash:
                maps = collections.OrderedDict((d, {L: pid_of[k] for L, k in m.items()}) for d, m in dmaps.items() if m)
                for L, p_ in (entry.get("letters") or {}).items():
                    if maps and p_ in by_id and not any(lm.get(L) == p_ for lm in maps.values()):
                        clash = f"the catalogue has {L} for “{by_id[p_]['name']}”, no division of the document does"
                        break
            if clash:
                hold("the document disagrees with the catalogue", clash)
                continue
            extra = [x["name"] for x in rows if x["id"] not in matched]
            n = len(rows)
            if len(was) >= 3 and not (was & matched):
                hold("the document shares no problem with the catalogue's list", "; ".join(x["name"] for x in rows if x["id"] in was)[:300])
                continue
            if complete:
                if extra:
                    hold("the catalogue lists problems a complete document does not have", "; ".join(extra))
                    continue
                if doc.get("count") != n:
                    ruled.append(f"count {doc.get('count')} → {n}: distinct problems, not the sum over the divisions")
                doc["count"] = n
                doc.pop("complete", None)
            elif not was_whole:
                rc = r.get("count")
                if rc and rc > n:
                    if doc.get("count") != rc:
                        ruled.append(f"count {doc.get('count')} → {rc}: distinct problems, as the reader worked it out")
                    doc["count"] = rc
                elif doc.get("count"):
                    ruled.append(f"count {doc['count']} removed: it summed the divisions, and the number of distinct problems is not known")
                    doc.pop("count")
                doc["complete"] = False
            if maps:
                old_letters = entry.pop("letters", None)
                new_div = {d: dict(sorted(m.items(), key=lambda kv: (len(kv[0]), kv[0]))) for d, m in maps.items()}
                if entry.get("divisions") != new_div:
                    lettered += max(sum(len(m) for m in maps.values()) - len(old_letters or {}) - sum(len(m) for m in (entry.get("divisions") or {}).values()), 0)
                entry["divisions"] = new_div
                silent = [d for d, m in dmaps.items() if not m]
                if silent:
                    entry["note"] = "letters not known for " + ", ".join(silent)
                if doc.get("letters") == "unknown":
                    del doc["letters"]
            elif rows and not any(e2.get("letters") or e2.get("divisions") for e2 in doc["contests"]):
                doc["letters"] = "unknown"
        else:
            if entry.get("divisions"):
                hold("the catalogue has divisions for this contest, the reading has none")
                continue
            lmap = {} if cid in RELETTER else dict(entry.get("letters") or {})
            inv = {v: k for k, v in lmap.items()}
            for p in probs:
                name, L = p["name"].strip(), (str(p["letter"]) if p.get("letter") is not None else None)
                e = by_id.get(lmap[L]) if L and L in lmap else None
                if e is not None and not any(same(t, name) for t in titles(e)):
                    clash = f"letter {L}: the catalogue has “{e['name']}”, the document “{name}”"
                    break
                if e is None:
                    cands = find(name)
                    e = cands[0] if len(cands) == 1 else None
                    if len(cands) > 1:
                        clash = f"“{name}” matches several listed problems"
                        break
                    if e is not None and L:
                        if e["id"] in inv and inv[e["id"]] != L:
                            clash = f"“{name}”: the catalogue has it as {inv[e['id']]}, the document as {L}"
                            break
                        if e["id"] not in inv:
                            lmap[L] = e["id"]; inv[e["id"]] = L; lettered += 1   # noqa: E702
                if e is None:
                    e = add(name, L)
                    if e is None:
                        clash = f"“{name}” would get an id the set already uses"
                        break
                    added += 1
                    if L:
                        lmap[L] = e["id"]; inv[e["id"]] = L   # noqa: E702
                elif e["name"] != name and name not in (e.get("other_names") or []):
                    spelled.append(f"{e['name']} / {name}")
                matched.add(e["id"])
            if clash:
                hold("the document disagrees with the catalogue", clash)
                continue
            extra = [x for x in rows if x["id"] not in matched]
            n = len(rows)
            if len(was) >= 3 and not (was & matched):
                hold("the document shares no problem with the catalogue's list", "; ".join(x["name"] for x in rows if x["id"] in was)[:300])
                continue
            if complete:
                if extra:
                    hold("the catalogue lists problems a complete document does not have",
                         "; ".join(x["name"] + (" (in the problem archive: has a uuid)" if x.get("uuid") else "") for x in extra))
                    continue
                if doc.get("count") and doc["count"] != n and not sure:
                    if n > doc["count"]:
                        hold("count", f"the catalogue says {doc['count']} problems, the document {n}")
                        continue
                    doc["complete"] = False   # the names go in; which count is right is a ruling
                    rep["for ruling: count"].append(f"{line} [the catalogue says {doc['count']} problems, the complete document {n}; count left as it was]{note}")
                else:
                    if doc.get("count") and doc["count"] != n:
                        ruled.append(f"count {doc['count']} → {n}, the document's" + (f" ({COUNT_OK[cid]})" if cid in COUNT_OK else ""))
                    doc["count"] = n
                    doc.pop("complete", None)
            else:
                rc = r.get("count")
                if rc and doc.get("count") and rc != doc["count"]:
                    if sure and rc >= n:
                        ruled.append(f"count {doc['count']} → {rc}, the document's")
                        doc["count"] = rc
                    else:
                        rep["for ruling: count"].append(f"{line} [the catalogue says {doc['count']} problems, the document {rc}; count left as it was]{note}")
                if doc.get("count") and n > doc["count"]:
                    hold("count", f"the catalogue says {doc['count']} problems, with the document's there would be {n}")
                    continue
                if doc.get("count") == n and rc in (None, n):
                    doc.pop("complete", None)
                else:
                    doc["complete"] = False
            if lmap:
                entry["letters"] = dict(sorted(lmap.items(), key=lambda kv: (len(kv[0]), kv[0])))
                if doc.get("letters") == "unknown":
                    del doc["letters"]
            elif rows and not any(e2.get("letters") or e2.get("divisions") for e2 in doc["contests"]):
                doc["letters"] = "unknown"
        if json.dumps(doc, sort_keys=True, ensure_ascii=False) == before and not new_set:
            rep["nothing new: the catalogue already has what the document gives"].append(f"{line}{note}")
            continue
        srcs = {s["n"]: s["url"] for s in pack.get("sources") or []}
        used = sorted({p.get("from") for p in probs if p.get("from") in srcs})
        if added or lettered or new_set:
            doc.setdefault("provenance", []).append(
                "problem names read from our copy of " + (", ".join(srcs[k] for k in used) or "the contest's problem set sources")
                + f" (tools/names_apply.py, {a.date})")
        for x in ruled:
            if not x.startswith("dropped"):
                doc.setdefault("provenance", []).append(f"{x} (ruling {a.date}, tools/names_apply.py)")
        if new_set:
            c["problems"] = {"set": sid}
            touched_series.add(ser)
        stats["sets opened"] += int(new_set and sid not in sets)
        sets[sid] = doc
        changed[sid] = None
        stats["problems added"] += added
        stats["letters added"] += lettered
        whole = "complete" not in doc and bool(doc.get("count")) and len(rows) == doc["count"]
        stats["lists now complete"] += int(whole and '"complete": false' in before)
        stats["rulings applied"] += len(ruled)
        rep["applied"].append(f"{line}: {added} names added, {lettered} letters added" + (", the list is complete" if whole else ", still partial")
                              + (f"; set {sid}, shared" if shared else "") + ("; divisions" if div else "")
                              + ("; " + "; ".join(ruled) if ruled else "")
                              + ("; spelling differs, catalogue kept: " + "; ".join(spelled[:6]) if spelled else ""))
    if a.write:
        for sid in changed:
            f = ROOT / "problemsets" / f"{sid}.yaml"
            write_set(f, f.read_text() if f.exists() else None, sets[sid])
        for ser in sorted(touched_series):
            dump_series(ser, series[ser], f"names_apply.py ({a.date})")
    lines = [f"# Problem names read from the documents we hold — {a.date}", "",
             f"Generated by `tools/names_apply.py --run {a.run}`" + (" --write" if a.write else " (dry run: nothing was changed)") + ".", "",
             f"- results read: {len(results)}", f"- sets changed: {len(changed)}"] + [f"- {k}: {v}" for k, v in stats.items()] + [""]
    for k in sorted(rep, key=lambda k: (not k.startswith("applied"), not k.startswith("for ruling"), k)):
        lines += [f"## {k[0].upper() + k[1:]} ({len(rep[k])})", ""] + [f"- {x}" for x in rep[k]] + [""]
    out = ROOT / "reports" / (a.report or f"names-from-documents-{a.date}.md") if a.write else run / "report-dry-run.md"
    if a.write and out.exists():
        print(f"{out} exists: the report of an earlier run is the record; give --report NAME", file=sys.stderr)
        out = run / "report-not-saved.md"
    out.write_text("\n".join(lines))
    print("report:", out)
    print(f"{len(results)} results; sets changed: {len(changed)};", dict(stats))
    for k in sorted(rep):
        print(f"  {len(rep[k]):4}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
