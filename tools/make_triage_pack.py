#!/usr/bin/env python3
"""Build the triage review pack: group the reconciliation worklist into rulable
families, keyed to the layer-policy options (reports/layer-policy-brief-2026-09-04.md).

Reads  data/reconciliation-worklist.json (CMS rows with no catalogue decision)
Writes reports/triage-review-2026-09-04.md   (the review document)
       data/triage-families.json             (machine file: family -> rows, for
                                              stub generation once ruled)

One verdict per FAMILY is the intended workflow. Verdict vocabulary:
  mainline      — becomes catalogue series/editions
  grandfather   — preliminary tier kept by explicit exception (documented list)
  registry      — tracked, excluded from mainline (minor/locals/specials)
  merge         — CMS row belongs to an EXISTING edition (cms_ids append)
  hold          — future shells / undecided
Stdlib only.
"""
from __future__ import annotations

import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIEF = "reports/layer-policy-brief-2026-09-04.md"

# (family, regex, section, tier, O1, O2, O2+UA, O3, O4, suggested, comment)
IN, OUT, GF = "in", "out", "grandfather"
RULES = [
 ("ukraine-oblasts",
  r"Ukraine (Eastern|Western|Southern|Northern|Central|Kiev|Southwestern) Contest"
  r"|(Western|Northern|Eastern|Southern|Central) Ukraine Contest",
  "structural", "preliminary", OUT, OUT, IN, OUT, IN, "mainline (the recommended third exception)",
  "richest excluded trove; 6-7/yr incl. war years; primary record of the UA community"),
 ("brazil-first-phase", r"Brazil First Phase", "structural", "sub-regional",
  IN, IN, IN, OUT, IN, "mainline under O2", "qualifying phase of brazil; med 641 teams"),
 ("gran-premio-mexico", r"Gran Premio de Mexico", "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", "national top round; med 834 teams"),
 ("gran-premio-centroamerica", r"Gran Premio de Centroamerica", "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", "national top round"),
 ("torneo-argentino", r"Torneo Argentino", "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", "TAP, standalone national tournament"),
 ("torneo-chileno", r"Torneo Chileno", "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", ""),
 ("bolivia", r"Bolivia|Competencia (Nacional|Preliminar)", "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", ""),
 ("colombia-maraton", r"Maraton|Maratón", "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", "ACIS/REDIS national maraton, 20-year series"),
 ("venezuela-finals", r"Venezuela Finals", "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", ""),
 ("caribbean", r"Caribbean (National|Local)|Competición Local de Programación",
  "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline (national); registry for the per-campus locals",
  "national round is peer of other LatAm nationals; 'Local' rows are campus-level"),
 ("japan-first-round", r"Japan Online First", "structural", "sub-regional",
  IN, IN, IN, OUT, IN, "mainline under O2", "med 355 teams"),
 ("jakarta-indonesia-national", r"Jakarta - Indonesia National|Asia Jakarta New Online",
  "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", "med 619 teams"),
 ("vietnam-national", r"Vietnam National|Nha Trang National", "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", ""),
 ("asia-nationals-misc",
  r"(Malaysia|Pakistan|Philippines|Mongolia|Myanmar|Afghanistan|Bangladesh).*(National|NCPC)"
  r"|D\.P\.R of Korea National|al-?Khawarizmi|AlKhawarizmi|Asia KL Malaysia|Yangon National"
  r"|Manila - Philippine National|Philippines Davao|Myanmar Collegiate",
  "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline (one series per country)",
  "Malaysia, Pakistan, Philippines, Mongolia, Myanmar, Afghanistan, Bangladesh, DPRK, Yangon"),
 ("taiwan-rounds",
  r"Taiwan (Online|Private University|Technology University|National)|Kaohsiung.*Taiwan"
  r"|Chia-Yi|Taiwan.*NC[TP]U|Taipei National|Hua-Lien NC[TP]U|Taipei NCPU",
  "structural", "sub-regional",
  IN, IN, IN, OUT, IN, "mainline under O2 (grouped: online / tech-univ / private-univ)",
  "several parallel national rounds; needs sub-series naming decision"),
 ("thailand-rounds", r"Thailand (National|Southern|Northeastern|Northern|Central|Eastern)",
  "structural", "sub-regional",
  IN, IN, IN, OUT, IN, "mainline national; registry for the group rounds",
  "national on-site is the top round; N/NE/S group rounds are its feeders"),
 ("tehran-online", r"Tehran - (Online|Internet)|Iran-Internet-PC", "structural", "sub-regional",
  IN, IN, IN, OUT, IN, "mainline under O2 (per-site Iran-Internet rows -> merge into year rows)",
  "med 394 teams; 2014/15 per-university rows are site views of one round"),
 ("india-area-rounds", r"Kharagpur.*North India|India Area", "structural", "sub-regional",
  IN, IN, IN, OUT, IN, "mainline under O2", ""),
 ("china-provincial",
  r"China (Dalian Metropolitan|Inner Mongolia|Shanghai Metropolitan|Shaanxi National)"
  r"|Shandong Province|Nanjing Online", "structural", "sub-regional",
  IN, IN, IN, OUT, IN, "mainline under O2 (thin CMS presence)",
  "provincial/metropolitan opens; most Chinese contests never registered in CMS"),
 ("moscow-open", r"Moscow Programming Contest", "structural", "sub-regional",
  IN, IN, IN, IN, IN, "mainline", "open Moscow contest 2018-2022, med 327"),
 ("slovenia-rounds", r"Slovenian Programming Contest", "structural", "preliminary",
  OUT, OUT, OUT, OUT, IN, "registry (rounds); UPM year results are already mainline",
  "per-round rows of UPM; wave-7 standings now cover the year level"),
 ("south-pacific-legacy", r"South Pacific", "structural", "varies",
  GF, GF, GF, GF, IN, "grandfather (existing exception)",
  "SP divisions are already catalogued; these rows likely merge/extend that family"),
 ("kazakhstan-octafinal", r"Kazakhstan Octafinal", "structural", "sub-regional",
  IN, IN, IN, OUT, IN, "mainline if it recurs (brief §5)", "single 2024 edition so far"),
 ("oman-subregions", r"Oman (Capital|Coastline|Midland|Southern|Oriental|Sub-region)",
  "structural", "preliminary",
  OUT, OUT, OUT, OUT, IN, "registry unless ruled like Ukraine oblasts",
  "new 2025+ Oman sub-region structure - same shape as UA oblasts, but 2 seasons old"),
 ("girls-special", r"GIRLS|Girls|AlgoQueen", "special", "special",
  OUT, OUT, OUT, OUT, IN, "registry now; revisit as a dedicated series group",
  "real ranked events (Africa&Arab Girls, Girls-only, AlgoQueen) - a deliberate call, not a default"),
 ("seniors-masters", r"Seniors|Masters", "special", "special",
  OUT, OUT, OUT, OUT, OUT, "registry", "veterans/masters events - not collegiate mainline"),
 ("kickoff-individual", r"Kickoff.*Individual|Individual Online|Team Formation|Problem Sampler",
  "special", "special",
  OUT, OUT, OUT, OUT, OUT, "registry", "individual-format warmups"),
 ("handled-elsewhere",
  r"Tajikistan Regional|Asia Dhaka Regional|Kuala Lumpur Onsite|2019 Uzbekistan Regional"
  r"|Peradeniya Regional|Wuhan Regional|Turkmenistan Regional",
  "merge", "-", "-", "-", "-", "-", "-", "misclass runner / cms_ids merge",
  "rows the audit already routes: tajikistan/peradeniya/wuhan/turkmenistan adds, "
  "kuala-lumpur-2014 + uzbekistan-2019 cms fixes, dhaka onsite rows -> cms_ids merge"),
 ("mexico-locals",
  r"Nuevo Leon|Michoac|Jalisco|ITESO|Occident|ITESM|ITAM|BUAP|Technologico|Guadalajara"
  r"|Mexican Open|Jesuit University|Zapopan|Batalla|ESCOM|ITESI|Monterrey"
  r"|Mexico.*(Programming|Battle|Prepar)|Tamaulipas|Guanajuato|Queretaro|Puebla"
  r"|Aguascalientes|Concurso Universitario|Mexico and Central America Finals",
  "locals", "minor",
  OUT, OUT, OUT, OUT, OUT, "registry (minor)", "state/campus layer under Gran Premio"),
 ("angola-local", r"Angolan? Local", "locals", "minor",
  OUT, OUT, OUT, OUT, OUT, "registry (minor)", ""),
 ("arab-uni-locals", r".", "locals", "minor",
  OUT, OUT, OUT, OUT, OUT, "registry (minor)",
  "university/city CPCs feeding ACPC & co (catch-all for this section)"),
]
# arab-uni-locals uses '.' as catch-all LAST; anything non-arab that reaches it is
# reviewed via the residue print, so keep genuinely-unmatched detection separate:
ARAB_HINT = re.compile(
    r"Damascus|Tishreen|Alexandria|GUC|Mansoura|AAST|Ain.?Shams|Assuit|Benha|FCI|Cairo|LAU"
    r"|Amman|Arabella|Higher Institute|Aleppo|Syrian|ENSIAS|Sousse|INSAT|ISI|TEK-UP|Sfax"
    r"|Sup'Com|Delta|AUST|Mekn|Tunis|ISET|Iset|iset|Mannouba|Epi |JU |JNJD|LU |Sa3edy|Tartous"
    r"|Menia|AUC|MUST|Upper Egypt|Idlib|AOU|Amrah|AlFursan|ISC'Com|GRCPC|Junior|Cyprus"
    r"|Esprit|Carthage|Antonine|JUST|EHTP"
    r"|Arab|Egypt|Jordan|Kuwait|Qatar|Bahrain|Oman|Saudi|Sudan|Libya|Morocco|Algeria|Lebanon"
    r"|Palestin|Iraq|Yemen|Girls|university|University|College|Institute|Academy|Test")


def parse_counts(reason: str):
    m = re.search(r"(\d+) teams?, (\d+) results?", reason or "")
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def main() -> int:
    rows = json.loads((ROOT / "data" / "reconciliation-worklist.json").read_text())
    fams, meta = defaultdict(list), {}
    residue = []
    for r in rows:
        if r.get("status") == "future":
            fams["future-shells"].append(r)
            continue
        for rule in RULES:
            fam, pat = rule[0], rule[1]
            if re.search(pat, r["Full name"]):
                if fam == "arab-uni-locals" and not ARAB_HINT.search(r["Full name"]):
                    residue.append(r)
                    fam = "unmatched"
                fams[fam].append(r)
                meta.setdefault(fam, rule)
                break
    meta["future-shells"] = ("future-shells", "", "hold", "-", "-", "-", "-", "-", "-",
                             "hold until run", "upcoming CMS shells (2026-27)")
    meta["unmatched"] = ("unmatched", "", "manual", "?", "?", "?", "?", "?", "?",
                         "manual review", "no family matched")

    def stat(rs):
        teams = [t for t, _ in (parse_counts(x.get("Reason")) for x in rs) if t]
        span = sorted(x["Date"][:4] for x in rs if x.get("Date"))
        return (len(rs), f"{span[0]}-{span[-1]}" if span else "?",
                int(statistics.median(teams)) if teams else 0,
                max(teams) if teams else 0)

    order = ["structural", "special", "merge", "locals", "hold", "manual"]
    sec_of = {f: (meta[f][2] if f in meta else "manual") for f in fams}
    sec_of["future-shells"] = "hold"

    out = [
        "# Triage review pack — the reconciliation worklist, grouped for ruling",
        "",
        f"*2026-09-04. {len(rows)} CMS rows with no catalogue decision, grouped into "
        f"{len(fams)} families so one verdict covers a family. Options and evidence: "
        f"{BRIEF}. Verdicts: **mainline** / **grandfather** / **registry** / **merge** "
        f"(cms_ids of an existing edition) / **hold**. Suggested verdicts assume O2 + "
        f"the Ukraine-oblast exception (the brief's recommendation); the O-columns show "
        f"how each family fares under the other rules.*",
        "",
        "*Scope note: several §2 families are NOT in this worklist (Korea First Round, "
        "NEERC quals, MIUP, AdaByron, Moldova, Dhaka/Amritapuri online prelims…) — they "
        "already carry sheet labels or sit outside CMS. The layer ruling still covers "
        "them; stub generation reads the CMS DB, not this worklist.*",
        "",
        "## Summary",
        "",
        "| family | section | tier | rows | span | med/max teams | O1 | O2 | O2+UA | O3 | O4 | suggested |",
        "|---|---|---|--:|---|---|---|---|---|---|---|---|",
    ]
    ordered = sorted(fams, key=lambda f: (order.index(sec_of[f]), -len(fams[f])))
    for f in ordered:
        n, span, med, mx = stat(fams[f])
        m = meta[f]
        out.append(f"| {f} | {m[2]} | {m[3]} | {n} | {span} | {med}/{mx} "
                   f"| {m[4]} | {m[5]} | {m[6]} | {m[7]} | {m[8]} | **{m[9]}** |")

    for f in ordered:
        m = meta[f]
        n, span, med, mx = stat(fams[f])
        out += ["", f"## {f}  —  {n} rows, {span}, median {med} teams",
                "", f"*Tier {m[3]}; suggested: **{m[9]}**. {m[10]}*", ""]
        out.append("| date | cms | name | teams/results | cert |")
        out.append("|---|---|---|---|---|")
        for r in sorted(fams[f], key=lambda x: (x.get("Date") or "9999")):
            t, res = parse_counts(r.get("Reason"))
            out.append(f"| {(r.get('Date') or '?')[:10]} | {r.get('Contest ID', '?')} "
                       f"| {r['Full name'][:70]} | {t or '?'}/{res or '?'} "
                       f"| {r.get('certainty', '')} |")

    md = "\n".join(out) + "\n"
    (ROOT / "reports" / "triage-review-2026-09-04.md").write_text(md)
    machine = {f: {"section": meta[f][2], "tier": meta[f][3], "suggested": meta[f][9],
                   "verdict": None,
                   "rows": [{"cms_id": r.get("Contest ID"), "name": r["Full name"],
                             "date": r.get("Date"), "parent_hint": r.get("Parent"),
                             "teams": parse_counts(r.get("Reason"))[0],
                             "results": parse_counts(r.get("Reason"))[1]}
                            for r in fams[f]]}
               for f in fams}
    (ROOT / "data" / "triage-families.json").write_text(
        json.dumps({"generated": "2026-09-04", "verdict_vocabulary":
                    ["mainline", "grandfather", "registry", "merge", "hold"],
                    "families": machine}, indent=1, ensure_ascii=False))
    print(f"{len(rows)} rows -> {len(fams)} families; "
          f"unmatched: {len(fams.get('unmatched', []))}")
    for r in fams.get("unmatched", []):
        print("  unmatched:", (r.get("Date") or "?")[:10], r["Full name"][:70])
    print("wrote reports/triage-review-2026-09-04.md + data/triage-families.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
