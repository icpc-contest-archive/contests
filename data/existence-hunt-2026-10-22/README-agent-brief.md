# Existence-evidence hunt — common instructions (2026-10-22)

## Context
We maintain a catalogue + archive of every ICPC contest ever run (World Finals, regionals, subregionals, national qualifiers), at https://icpc-contest-archive.github.io/contests/ . For the contests in your brief we hold NO archived copy of anything: no scoreboard, no standings, no result page, no website crawl. The owner wants a deep search of the open internet — above all **competitive-programming discussion forums and social media** — for anything that implies the contest **existed and was actually run**: a results announcement, a participant's blog or forum post, a photo album, a university news item, a Usenet post, a video of the award ceremony, a tweet from the organisers, a Facebook event, a LinkedIn "we placed 3rd at..." post, a Wikipedia/Wiki mention with a citation, etc.

Contest ids are `<series>-<year>` where the year is the contest's own calendar year (fall regionals feed the NEXT year's World Finals; the catalogue's `season` field is that end year). The ICPC "finder" slug convention uses season = year+1 (e.g. the 2018 contest is `.../finder/<abbrev>-2019`).

## What to look for, in priority order
1. **Direct results evidence**: a page/post that gives the winner, placements, team counts, date, host. (Best: a scoreboard/standings page we could capture — report its URL as a `new_result_urls` entry.)
2. **Participation evidence**: "our team went to X 19YY", a problem-solving blog about that contest's problems, a photo album, a team roster, a video.
3. **Organisational evidence**: call for registration, schedule, host announcement, sponsor page, press release, minutes of a steering meeting mentioning that edition.
4. **Negative evidence**: an organiser's history page that skips that year, a statement that the first edition was later, a "cancelled" notice. Record it — "did not run" is also an answer.

## Where to look (go broad; each contest deserves 2-6 well-aimed searches)
- Codeforces blogs/comments (WebSearch with `site:codeforces.com`; codeforces.com/search is robots-blocked, do not fetch it), Topcoder forums, Codechef discuss, AtCoder/Luogu/CSDN/Zhihu/Bilibili (Chinese), VNOI / voz / Facebook (Vietnam), Lowyat (Malaysia), PinoyExchange / Facebook (Philippines), Habr / VK / acm.timus forum / e-maxx (Russia/ex-USSR), infoarena (Romania), Reddit, Quora, Stack Exchange, Hacker News.
- Social: X/Twitter, Facebook pages & events, Instagram, LinkedIn posts & profiles ("ICPC ... 2014 regional finalist"), YouTube/Vimeo/Bilibili videos, Flickr/Google Photos albums, Weibo.
- Usenet for the pre-web era: Google Groups (comp.org.acm, comp.edu, net.*, uw.general, soc.culture.*) — WebSearch with `site:groups.google.com`; usenetarchives.com (client-rendered: WebFetch only sees chrome, but WebSearch can surface post titles); Utzoo archives on archive.org for 1981–1991.
- University/department news pages, student newspapers (many digitised on archive.org or university library sites), alumni magazines, CVs/résumés of coaches and contestants ("coached the team that won the 19xx ... regional"), SIGCSE Bulletin / ACM DL contest reports, ICPC's own old pages on Wayback (icpc.baylor.edu/past/..., icpc.global/regionals/finder/...).
- Wikipedia (any language) and its references; national CS society sites (SBC, ACM chapters, ACIS, APICS, Science Atlantic, etc.).
- Wayback Machine for dead hosts: WebFetch `https://web.archive.org/web/2010*/host.example/*` style listings often fail here; `https://web.archive.org/web/<year>0101000000*/http://host/path` sometimes works; `http://archive.org/wayback/available?url=<url>&timestamp=<yyyymmdd>` is a cheap availability check.

## Tool rules (important — these are the environment's real limits)
- **WebSearch budget: at most 45 calls for your whole run.** Other agents share the pool. Use `mode: "standard"` by default; `extended` only for 2–3 of your hardest cases. Combine years in one query where sensible ("Rocky Mountain regional programming contest 1989 OR 1990 OR 1991"). Native-language queries (Portuguese, Vietnamese, Malay, Romanian, Russian, Chinese, Spanish) often beat English ones.
- WebFetch any URL that a search result or a fetched page gave you — that is free. A URL you *constructed* yourself may be refused with a provenance/approval message; if that happens, do **not** retry or work around it (no curl, no scripts, no proxies) — record it under `open_leads` as "to probe" and move on.
- Do not spend more than ~3 fetches on one dead host. If a site is a JS shell, note it and move on.
- Never fabricate a URL. Every evidence entry must be a URL you saw in a search result or fetched. Mark `fetched: true` only when you actually fetched the page and it says what you claim; otherwise `fetched: false` (search-snippet only).
- Time box: about 60–90 minutes of work. Breadth over depth: every PRIMARY contest in the brief gets at least two aimed searches before any contest gets a fifth.

## Output (strict)
Write ONE JSON file to the path given in your task, with this shape:
```json
{
  "group": "<group id>",
  "searches_done": <int>,
  "contests": [
    {
      "contest": "<id>",
      "verdict": "confirmed-ran | likely-ran | unclear | likely-not-run | not-yet-held",
      "confidence": "high|medium|low",
      "facts": {"date": "...", "host": "...", "location": "...", "winner": "...", "n_teams": "...", "other": "..."},
      "evidence": [
        {"url": "...", "kind": "forum|social|news|blog|usenet|official|university|video|photo|wiki|cv|other",
         "source_name": "...", "posted": "<date or year if known>",
         "what_it_says": "1–2 sentences quoting the key fact(s): date, host, winner, team counts",
         "fetched": true}
      ],
      "new_result_urls": [
        {"url": "...", "artifact": "web|standings|scoreboard|frozen_scoreboard|rankings|problemset|report", "note": "..."}
      ],
      "open_leads": ["..."],
      "searches": ["<the exact queries you ran for this contest>"]
    }
  ],
  "series_level_findings": "free text: anything learned about the series as a whole (history pages, archives, people to ask)",
  "dead_ends": ["sources tried that gave nothing, so nobody repeats them"]
}
```
Then reply with a 10–20 line summary: per contest one line `id — verdict — best evidence URL`, plus the series-level findings. The JSON file is the deliverable; the summary is for the coordinator.
