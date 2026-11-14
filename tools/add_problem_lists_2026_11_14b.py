#!/usr/bin/env python3
"""Second batch of problem lists from judge source strings (SPOJ and Eolymp, as listed by vjudge.net
on 2026-11-13): same rules as add_problem_lists_2026_11_14.py, which does the work.

    python3 tools/add_problem_lists_2026_11_14b.py [--dry-run]
"""
import html, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import add_problem_lists_2026_11_14 as base  # noqa: E402
from import_judge_links import URL  # noqa: E402

base.URL = dict(base.URL, **URL)
base.LISTS = [
 ("poland-1998", "spoj", "III Polish Collegiate Team Programming Contest (AMPPZ), 1998",
  "BALL1~Ball ; EXPR1~Expression ; MOULDS~Moulds ; PERMUT1~Permutations ; RELATS1~Relations ; TREE1~Tree ; CRSCNTRY~Cross-country ; CUTOUT~Cutting out ; SQRBR~Square Brackets", {}),
 ("poland-2001", "spoj", "VI Polish Collegiate Team Programming Contest (AMPPZ), 2001",
  "LONER~The Loner ; MAZE~The Long and Narrow Maze ; PARTIT~Partition ; POSTERS~Election Posters", {}),
 ("palestine-2012", "spoj", "The First Palestinian Collegiate Programming Contest (problem codes PCPC12A-J)",
  "PCPC12A~Game ; PCPC12B~Free Palestine ; PCPC12C~Tetravex ; PCPC12D~New Strategy ; PCPC12E~Snakes and Ladders ; PCPC12F~Snakes and Ladders Again ; PCPC12G~Mosque ; PCPC12H~Beggars ; PCPC12I~peaks ; PCPC12J~Amr Samir", {}),
 ("ukraine-2012", "eolymp", "ACM-ICPC Ukraine 2012, 2nd Stage Ukraine, September 6, 2012",
  "3756~Kinds of figures ; 3757~John, Bruce and beer ; 3759~Cube ; 3760~Queue ; 3761~Magic Labyrinth ; 3763~Very hard task ; 3764~Remainders sum", {}),
 ("ukraine-2013", "eolymp", "ACM-ICPC Ukraine 2013, 2nd Stage Ukraine, September 10-12, 2013",
  '6081~"Metro" ; 6082~Supernatural ; 6083~Pieces of Paper ; 6084~Nested rectangles ; 6085~Turns minimization ; 6086~Same quantity, sum and product ; 6087~A Cycle of Points ; 6089~"Desoxyribonucleic Acid" ; 6090~Easy Recurrence', {}),
 ("thailand-2011", "spoj", "ACM ICPC Regional Phuket 2011", "PK11E~Queen Game ; PK11F~Spelling Suggestion ; PK11I~Paths in a Tree", {}),
 ("thailand-2011", "eolymp", "ACM-ICPC Asia Phuket Regional Programming Contest - 4 November 2011 – PSU, Phuket Campus",
  "3098~Twin Apparent Primes!! ; 3099~Queen Game ; 3100~Spelling Suggestion ; 3101~Coalescing Continents ; 3103~Paths in a Tree", {}),
 ("latam-2008", "spoj", "South American Regional Contests 2008",
  "SAMER08A~Almost Shortest Path ; SAMER08B~Bases ; SAMER08C~Candy ; SAMER08D~DNA Sequences ; SAMER08F~Feynman ; SAMER08K~Shrinking Polygons", {}),
 ("latam-2012", "eolymp", "ACM ICPC Regional Latino America 2012", "6598~Different Digits ; 6603~Interval Product", {}),
 ("ncna-2013", "eolymp", "ACM ICPC NCNA Programming Contest - November 7, 2013",
  "6624~Four-Tower Towers of Hanoi ; 6626~Full Board ; 6628~Strings with Same Letters", {}),
 ("mongolia-national-2013", "spoj", "ACM-ICPC 2013 MGL",
  html.unescape("ACMA~&#1058;&#1101;&#1075;&#1096; &#1257;&#1085;&#1094;&#1257;&#1075;&#1090; ; ACMB~&#1061;&#1072;&#1084;&#1075;&#1072;&#1072;&#1083;&#1072;&#1083;&#1090; ; ACMC~&#1053;&#1080;&#1081;&#1083;&#1073;&#1101;&#1088; &#1086;&#1083;&#1086;&#1093; ; ACME~&#1064;&#1072;&#1075;&#1072;&#1081;"), {}),
]
if __name__ == "__main__":
    sys.exit(base.main())
