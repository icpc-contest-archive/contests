# Problem sets merged — 2026-11-12

`tools/merge_problemsets.py`: 87 sets replaced by 20 shared sets; 87 contests relinked; 706 problem ids kept as aliases, so old problem and set pages redirect.

## Shared sets

| set | problems | used by | remarks |
| --- | --- | --- | --- |
| `latam-2007` | 10 | central-america-2007, south-america-2007 |  |
| `latam-2008` | 5 | central-america-2008, south-america-north-2008, south-america-south-2008 |  |
| `latam-2009` | 10 | caribbean-2009, central-america-2009, south-america-north-2009, south-america-south-2009 |  |
| `latam-2010` | 8 | caribbean-2010, central-america-2010, south-america-north-2010, south-america-south-2010 |  |
| `latam-2011` | 13 | caribbean-2011, central-america-2011, south-america-north-2011, south-america-south-2011 |  |
| `latam-2012` | 7 | caribbean-2012, central-america-2012, south-america-north-2012, south-america-south-2012 |  |
| `latam-2013` | 7 | caribbean-2013, central-america-2013, south-america-north-2013, south-america-south-2013 |  |
| `latam-2015` | 12 | caribbean-2015, central-america-2015, south-america-north-2015, south-america-south-2015 |  |
| `latam-2016` | 10 | caribbean-2016, central-america-2016, south-america-north-2016, south-america-south-2016 |  |
| `latam-2017` | 13 | caribbean-2017, central-america-2017, south-america-north-2017, south-america-south-2017 |  |
| `latam-2018` | 13 | caribbean-2018, central-america-2018, south-america-north-2018, south-america-south-2018 |  |
| `latam-2019` | 13 | caribbean-2019, central-america-2019, mexico-2019, south-america-north-2019, south-america-south-2019 |  |
| `latam-2020` | 14 | brazil-2020, caribbean-2020, central-america-2020, mexico-2020, south-america-north-2020, south-america-south-2020 |  |
| `latam-2021` | 13 | brazil-2021, caribbean-2021, central-america-2021, mexico-2021, south-america-north-2021, south-america-south-2021 |  |
| `latam-2022` | 13 | brazil-2022, caribbean-2022, central-america-2022, mexico-2022, south-america-north-2022, south-america-south-2022 |  |
| `latam-2023` | 13 | caribbean-2023, central-america-2023, mexico-2023, south-america-north-2023, south-america-south-2023 |  |
| `latam-2024` | 12 | brazil-2024, caribbean-2024, central-america-2024, mexico-2024, south-america-north-2024, south-america-south-2024 |  |
| `latam-2025` | 12 | brazil-2025, caribbean-2025, central-america-2025, mexico-2025, south-america-north-2025, south-america-south-2025 |  |
| `east-na-ecna-2025` | 12 | east-na-2025, ecna-2025 |  |
| `scusa-seusa-2020` | 16 | scusa-2020, seusa-2020 | 16 problems have different kattis links per member, all kept |

## Refiled

- `brazil-2019` held the list of `brazil-first-phase-2019`; its rows moved there, and brazil-2019 now uses `latam-2019` (26 judge links that belong to the regional's problems (paired to these rows by letter) dropped)
- `brazil-2023` held the list of `brazil-first-phase-2023`; its rows moved there, and brazil-2023 now uses `latam-2023`

## How this differs from the review's count

The site review counted 82 sets in 22 groups by identical lists. What was done is 87 sets into 20:

- 2011's two groups are one set (one list is contained in the other, same letters), and
  `central-america-2007` + `south-america-2007` join by the same rule;
- five sites of the regional that had no list of their own (2023, 2024) joined the year's set;
- the two Brazil pairs (2019, 2023) were not a shared set but a misfiling, see Refiled.

## Not merged: the Brazil finals 2005-2018

The Brazil final is a site of the Latin America regional, so it should use the year's `latam` set.
For these 14 years its set is something else: a letter-by-letter mix of two Baekjoon categories that
both sit on the final as judge pages, the regional ("Latin America Regional Contests <year>") and
Brazil's first phase ("A Primeira Fase da Maratona de Programação <year>"). `mine_judge_links.py`
joined the two lists by letter, so a row carries one contest's name and a link to each contest's
problem. (2013 and 2015 have the regional's names with first-phase links attached, the rest the
first phase's names with regional links attached.)

| year | problems listed | rows with two Baekjoon links | first row | first-phase contest in the catalogue | its set |
| --- | --- | --- | --- | --- | --- |
| 2005 | 8 | 3 | Jogo do Bicho | no | — |
| 2006 | 8 | 0 | Circuito Bioquímico Digital | no | — |
| 2007 | 10 | 10 | Vôlei Marciano | no | — |
| 2008 | 10 | 10 | Apagando e Ganhando | yes | — |
| 2009 | 11 | 8 | Ataque Fulminante | yes | — |
| 2010 | 11 | 11 | Revisão de Contrato | yes | — |
| 2011 | 13 | 9 | Ácido Ribonucléico Alienígena | yes | — |
| 2012 | 12 | 10 | Concurso de Contos | yes | — |
| 2013 | 10 | 10 | Blogger language | yes | brazil-first-phase-2013 (10) |
| 2014 | 11 | 0 | Volta | yes | — |
| 2015 | 13 | 11 | At most twice | yes | — |
| 2016 | 12 | 11 | Andando no tempo | yes | — |
| 2017 | 13 | 13 | Acordes intergaláticos | yes | — |
| 2018 | 13 | 13 | Aventurando-se no Slackline | yes | brazil-first-phase-2018 (13) |

Proposed repair, not done because it changes which problems a contest claims:

1. move the first-phase Baekjoon page from `brazil-<year>` to `brazil-first-phase-<year>`
   (2008-2018; the catalogue has no first-phase contest for 2005-2007);
2. rebuild the first-phase set from that page alone;
3. put `brazil-<year>` on `latam-<year>` and retire the mixed set.

2019 and 2023 were the same error, with a list identical to the first phase's own set; they are
repaired above. The first-phase Baekjoon page of 2019 (category 2065) is still listed under
`brazil-2019` as a judge page.
