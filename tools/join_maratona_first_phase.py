#!/usr/bin/env python3
"""Contests that sat the Maratona SBC first-phase problem set join that year's set.

The first-phase set is used at the same time by other Latin American contests; the set itself
says which. Evidence per year (read 2026-11-14):
  2021  Codeforces gym 103388: "used in simultaneous online contests: Maratona de Programação da SBC
        2021, Tercera Fecha Gran Premio de México 2021, Tercera Fecha Gran Premio de Centroamérica
        2021, Torneo Argentino de Programación 2021"
  2022  https://maratona.sbc.org.br/hist/2022/primfase22/reports/problems/maratona_es.pdf, cover:
        Maratona 2022, Tercera Fecha Gran Premio de México 2022, Gran Premio de Centroamérica 2022,
        Torneo Argentino de Programación 2022, The 2022 ICPC Bolivia Preliminary Contest
  2023  Codeforces gym 104555: Maratona 2023, Gran Premio de México 2023, Gran Premio de Centroamérica
        2023, The 2023 ICPC Bolivia Preliminary Contest, Torneo Chileno de Programación 2023
  2024  https://maratona.sbc.org.br/primfase24/contest-pf2024/info_maratona_en.pdf, cover: Maratona
        2024, Competencia Boliviana de Programación, Gran Premio de Centroamerica, Gran Premio de Mexico
  2025  Codeforces gym 106073: Maratona 2025, Competencia Boliviana de Programación, Gran Premio de
        Centroamerica 2025, Gran Premio de Mexico 2025

Joined here: Bolivia 2022-2025, TAP 2021-2022, Torneo Chileno 2023 (same date as the first phase, or
the same gym already recorded as their source). NOT joined: Gran Premio de México and de Centroamérica —
the shared set is one date of a multi-date Gran Premio (the last), while the catalogue's one contest per
year carries an earlier date and, for México 2023, the first date's problems; which date the catalogue
contest is has to be decided first.

bolivia-national-2024 held the list of Codeforces gym 105230, "ICPC Bolivia Pre-National Contest", a
different contest: that set and source are removed.

    python3 tools/join_maratona_first_phase.py [--dry-run]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from catalogue import ROOT, dump_series, load_series, load_sets  # noqa: E402
from import_judge_links import dump  # noqa: E402

PLAN = {2021: ["tap-2021"], 2022: ["tap-2022", "bolivia-national-2022"], 2023: ["bolivia-national-2023", "torneo-chileno-2023"],
        2024: ["bolivia-national-2024"], 2025: ["bolivia-national-2025"]}
EVID = {2021: "Codeforces gym 103388", 2022: "the cover of maratona_es.pdf (maratona.sbc.org.br/hist/2022/primfase22/reports/problems/)",
        2023: "Codeforces gym 104555", 2024: "the cover of info_maratona_en.pdf (maratona.sbc.org.br/primfase24/contest-pf2024/)", 2025: "Codeforces gym 106073"}


def main() -> int:
    dry = "--dry-run" in sys.argv
    series = load_series(); sets = load_sets(); where = {c["id"]: (ser, c) for ser, d in series.items() for c in d["contests"]}
    touched = set(); changed = set(); gone = []
    for y, cids in PLAN.items():
        s = sets[f"brazil-first-phase-{y}"]; own = next(e for e in s["contests"] if e["contest"] == f"brazil-first-phase-{y}")
        for cid in cids:
            ser, c = where[cid]
            if any(e["contest"] == cid for e in s["contests"]): continue
            old = (c.get("problems") or {}).get("set")
            if old and old in sets:
                if cid != "bolivia-national-2024": print("has a set already, left alone:", cid); continue
                gone.append(old); del sets[old]
                c["sources"] = [x for x in c.get("sources") or [] if "codeforces.com/gym/105230" not in x["url"]]
            e = {"contest": cid}
            if isinstance(own.get("letters"), dict): e["letters"] = dict(own["letters"])
            s["contests"].append(e); c["problems"] = {"set": s["id"]}
            s.setdefault("provenance", []).append(f"{cid} sat this set at the same time: named among the simultaneous contests on {EVID[y]} (tools/join_maratona_first_phase.py, 2026-11-14)")
            touched.add(ser); changed.add(s["id"]); print(f"{cid} -> {s['id']}")
    if not dry:
        for sid in changed: (ROOT / "problemsets" / f"{sid}.yaml").write_text(dump(sets[sid]))
        for sid in gone: (ROOT / "problemsets" / f"{sid}.yaml").unlink()
        for ser in touched: dump_series(ser, series[ser], "join_maratona_first_phase.py (2026-11-14)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
