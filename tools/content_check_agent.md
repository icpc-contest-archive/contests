# Instructions for a content-check agent

You check the sources of ICPC contests against the copies we hold. You were given a BATCH name
(like b017). Everything is on this computer; use only this shell. No web, no git, and write
nothing except the `verdict.json` files (scratch files under /tmp are fine).

    RUN=$HOME/mnt/icpc-contests/_content-check/run1

1. Read the rubric in full, once: `cat $HOME/mnt/icpc-contests/contests/tools/content_check_rubric.md`.
   It defines roles, verdicts, flags, facts and the exact output shape. Follow it exactly.
2. `cat $RUN/batches/<BATCH>.txt` lists the contests of your batch, one id per line. The pack dir of
   contest X is `$RUN/X`.
3. Take the contests ONE AT A TIME, in order. For each:
   - if `$RUN/X/verdict.json` already exists, skip it (somebody did it already);
   - `cat $RUN/X/pack.json $RUN/X/s*.txt` (one command). Open a full copy (`copy.file`) only when a
     digest is not enough to decide;
   - write `$RUN/X/verdict.json` with a python3 heredoc (json.dump, ensure_ascii=False) and check it:
     `python3 -m json.tool $RUN/X/verdict.json > /dev/null && echo valid`;
   - then go on to the next contest. Do not read ahead: one contest's pack at a time keeps you accurate.
4. When every contest of the batch has a verdict.json, reply with ONE line and nothing else:
   `<BATCH>: <contests done> contests, <sources> sources — <k> confirm, <k> correct, <k> other`

Be efficient: two or three shell calls per contest is normal.
