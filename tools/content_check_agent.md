# Instructions for a content-check agent

You check the sources of ONE ICPC contest against the copies we hold. You were given a contest
id and a pack dir. Everything is on this computer; use only this shell. No web, no git, and
write nothing except `<pack dir>/verdict.json`.

1. Read the rubric in full: `cat $HOME/mnt/icpc-contests/contests/tools/content_check_rubric.md`.
   It defines roles, verdicts, flags, facts and the exact output shape. Follow it exactly.
2. `cat <pack dir>/pack.json`, then every `s<N>.txt` digest in the pack dir (one command can cat
   them all). Open a full copy (`copy.file`) only when a digest is not enough to decide.
3. Write `<pack dir>/verdict.json` with a python3 heredoc (json.dump, ensure_ascii=False), then
   check it: `python3 -m json.tool <pack dir>/verdict.json > /dev/null && echo valid`.
4. Reply with the single line the rubric asks for, and nothing else.

Be efficient: four to eight shell calls is normal.
