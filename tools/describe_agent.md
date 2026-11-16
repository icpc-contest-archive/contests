# Instructions for a description-round agent

You check and describe the sources of ICPC contests from the copies we hold. You were given a
RUN directory and a BATCH name (like b017). Everything is on the user's computer: use only the
`mcp__remote-devices__device_bash` tool (if it is not loaded, load it with ToolSearch, query
`select:mcp__remote-devices__device_bash`). The plain Bash, Read and Write tools run on another
machine that does not have these files: do not use them. No web, no git, and write nothing except
the `result.json` files (scratch files under $HOME/scratch are fine).

1. Read both rubrics in full, once:
   `cat $HOME/mnt/icpc-contests/contests/tools/describe_rubric.md $HOME/mnt/icpc-contests/contests/tools/content_check_rubric.md`
   The first is your job and its output shape; of the second you need the sections *Roles* and
   *Verdict per source*. Where the two differ, the first one rules.
2. `cat $RUN/batches/<BATCH>.txt` lists the contests of your batch, one id per line. The pack dir of
   contest X is `$RUN/X`.
3. Take the contests ONE AT A TIME, in order. For each:
   - if `$RUN/X/result.json` already exists, skip it (somebody did it already);
   - `cat $RUN/X/pack.json $RUN/X/s*.txt` (one command; if the output is cut off, read the rest
     file by file);
   - open full copies where the rubric says so (websites: at least two more pages; PDFs over four
     pages: the whole text) and wherever the digest is not enough to describe the document;
   - write `$RUN/X/result.json` with a python3 heredoc (build a dict, `json.dump(..., ensure_ascii=False,
     indent=1)`; use a quoted heredoc `<<'PY'` so the shell leaves the text alone) and check it:
     `python3 $HOME/mnt/icpc-contests/contests/tools/describe_apply.py --check $RUN/X`
     It prints `ok` or what is wrong with the file (shape, length, forbidden words). Fix and
     re-check until it prints `ok`;
   - then go on to the next contest. Do not read ahead: one contest at a time keeps you accurate.
4. When every contest of the batch has a result.json that checks `ok`, reply with ONE line and
   nothing else:
   `<BATCH>: <contests done> contests — <k> described, <k> not described, <k> disagree with the earlier reader`
   ("described": sources you wrote a description for; "not described": no copy, not the
   document, wrong contest, cannot tell.) If a tool error stops you before the batch is done,
   say `<BATCH>: INCOMPLETE` and which contests have no result.json; do not leave a half-written file.

The descriptions are published. Accuracy matters more than speed: state only what you saw in the
copy, and open the copy rather than guess. A device_bash call is limited to about two minutes.
