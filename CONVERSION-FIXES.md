# Conversion fixes and notes

Source: `icpc-contest-list-main-list-2026-08-31.csv`, imported 2026-08-31 by tools/import_sheet.py.

- mainline contests: 2400 in 171 series files
- non-mainline (outside hierarchy): 24
- CMS triage entries: 1100
- rows not carried over (no CMS id to track, or duplicate):
  - duplicate triage id 5: 1
  - status=challenge without CMS id: 2
  - status=minor without CMS id: 2

## Mechanical fixes applied

- neerc renamed nerc in 2017: rewrote 17 pointers neerc-2017 -> nerc-2017
- syria-2017: dropped invalid date 2017-17-23 (kept as note)
- series-id typo: gwailor-pune-2021 -> gwalior-pune-2021
- series-id typo: gwailor-pune-2020 -> gwalior-pune-2020
- series-id typo: gwailor-pune-2019 -> gwalior-pune-2019
- series-id typo: gwailor-pune-2018 -> gwalior-pune-2018
- series-id typo: ghuangzhou-2014 -> guangzhou-2014
- series-id typo: ghuangzhou-2003 -> guangzhou-2003
- subset_of: ecna-2026 (cms [9776]) < east-na-2026 (cms [9768, 9775, 9776])
- subset_of: ecna-2025 (cms [9335]) < east-na-2025 (cms [9335, 9340])
- subset_of: ecna-2024 (cms [8928]) < east-na-2024 (cms [8922, 8928])
- subset_of: ecna-2023 (cms [7464]) < east-na-2023 (cms [7449, 7464])
- subset_of: gny-2026 (cms [9768]) < east-na-2026 (cms [9768, 9775, 9776])
- subset_of: mausa-2026 (cms [9777]) < south-na-2026 (cms [9767, 9769, 9777])
- subset_of: mausa-2025 (cms [9332]) < south-na-2025 (cms [9328, 9331, 9332])
- subset_of: mausa-2024 (cms [8937]) < south-na-2024 (cms [8918, 8933, 8937])
- subset_of: mausa-2023 (cms [7465]) < south-na-2023 (cms [7450, 7462, 7465])
- subset_of: mausa-2022 (cms [5373]) < south-na-2022 (cms [5373, 5377, 5386])
- subset_of: nena-2026 (cms [9775]) < east-na-2026 (cms [9768, 9775, 9776])
- subset_of: nena-2025 (cms [9340]) < east-na-2025 (cms [9335, 9340])
- subset_of: nena-2024 (cms [8922]) < east-na-2024 (cms [8922, 8928])
- subset_of: nena-2023 (cms [7449]) < east-na-2023 (cms [7449, 7464])
- subset_of: scusa-2026 (cms [9769]) < south-na-2026 (cms [9767, 9769, 9777])
- subset_of: scusa-2025 (cms [9331]) < south-na-2025 (cms [9328, 9331, 9332])
- subset_of: scusa-2024 (cms [8933]) < south-na-2024 (cms [8918, 8933, 8937])
- subset_of: scusa-2023 (cms [7462]) < south-na-2023 (cms [7450, 7462, 7465])
- subset_of: scusa-2022 (cms [5386]) < south-na-2022 (cms [5373, 5377, 5386])
- subset_of: seusa-2026 (cms [9767]) < south-na-2026 (cms [9767, 9769, 9777])
- subset_of: seusa-2025 (cms [9328]) < south-na-2025 (cms [9328, 9331, 9332])
- subset_of: seusa-2024 (cms [8918]) < south-na-2024 (cms [8918, 8933, 8937])
- subset_of: seusa-2023 (cms [7450]) < south-na-2023 (cms [7450, 7462, 7465])
- subset_of: seusa-2022 (cms [5377]) < south-na-2022 (cms [5373, 5377, 5386])
- dropped non-URL segment "'" from wf-2015/scoreboard
- triage row (status=minor, 'Greater NY Qualifier') claims cms id 1538, already part of mainline naq-2012 — kept in naq-2012, dropped from triage

## Not auto-fixed (left as open validator warnings)

- tehran-2023 and kanpur-2022 dated after the AWC they advance to
- nena-2026 has blank status (reads as 'ran') while sharing CMS id 9775 with future east-na-2026
- south-america-south-2021 dated 2023-03-17 (looks like the 2022 edition's date)
- germany-2026 still marked upcoming though dated 2026-06-13
- 'Any' column dropped entirely (derived data; 11 stale cells in source became moot)
