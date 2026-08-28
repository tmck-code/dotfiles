# CLAUDE.md — global working agreement

Applies in every repo; project `CLAUDE.md` wins on conflict.

## Style

Python: use `python-style`/`pytest-style` skills. Follow a repo's
`CODING_STANDARDS.md` if present.

## Skills are leased on demand

Before "I can't do X": `overseer.py search <query>` → `enable <skill>` → use it →
`release <skill>`. Run `overseer.py reap` at session start.

## Coordinator, not worker

Route, don't perform — subagents absorb noise (discovery, gate output, debug
loops), you absorb verdicts. Delegate: gates, multi-file discovery (`Explore`),
heavy/risky edits, and — once a subagent returns a plan — writing the code too.
Parallelise independent subagents in one message. Do directly: decide what/who,
hold the plan, talk to the user, trivial one-line edits. Backstopped by
`nudge-delegate.py`.

## Scratch files go on shelves

At session start, invoke the `dewey-decimal` skill before writing any scratch,
working, or subagent-handoff file — every such file goes under
`.scratch/<branch-shelf>/`, never flat in `.scratch/`.

## Subagent handoff goes through files

Give each spawned subagent a report path
`.scratch/<branch-shelf>/<agent>-<task>-<agent_id>.md`, where `<branch-shelf>` is
the current branch's shelf under the repo root (see the `dewey-decimal` skill);
it writes findings there, returns only the path. Read the file, not the return
message — nested subagents too; ensure the shelf exists before spawning.
Filenames must not contain `research` or `report` (case-insensitive substring)
— that trips a harness write-blocking check; use `findings`/`notes`/`summary`
instead.

## Subagents must not share mutable working files

Sole-writer rule: an agent owns its brief's files alone; children mustn't touch
them. Scratch work: a per-agent subdir, never shared. Parallel editors on one
deliverable: separate git worktrees (`isolation: "worktree"`). Split ownership by
file/module, not mission. Handoffs point to code on disk, not a restated summary.
Backstopped by `subagent-file-handoff.py` and `same-file-write-audit.py`.

## Subagents own files, not the working tree

File ownership does not constrain git. `git stash`, `checkout -- .`, `restore`,
`reset`, `clean`, `switch`, `rebase`, `merge`, `cherry-pick` and `revert` mutate
the *whole tree* and will silently revert sibling agents' in-flight edits. A
subagent wanting a baseline diff uses `git diff <ref> -- <its own paths>` or
`git show <ref>:<path>`; to undo its own edit it rewrites the file. Parallel
editors that genuinely need tree-level git get `isolation: "worktree"`.
Backstopped by `subagent-git-tree-guard.py`, which denies these outright for
subagents outside a linked worktree.

## Browser automation goes through browser_batch

Never make a lone `mcp__claude-in-chrome__*` call — it nags on exactly one per
turn. Include `browser_batch` in the *first* ToolSearch select list; batch
navigate/resize/click/type/screenshot into one call, or pair an unbatchable step
with another browser call in the same message.

## Gates run once, through gate.sh, into a log

Never run a test/lint/build gate bare or piped through `tail`/`grep` — a
truncated tail hid an xdist worker crash and cost 14 min. Always:

```
~/.claude/scripts/gate.sh [-t secs] [-s secs] .scratch/<shelf>/gate-<name>.log make test
```

It captures everything, watches the process (hard timeout, stall detection
when the log stops growing), flags crash signatures (`node down`, `Error 137`,
segfault, OOM) even when the exit code is 0, and writes `exit=… reason=…` to
`<log>.status`. Rules:

- Run it with `run_in_background` and act on the completion notification — no
  `echo waiting` turns, no Monitor loops on the log.
- Need a different filter? `grep` the log. **Never rerun a gate to re-grep it.**
- After fixing a test, rerun **only that file/`-k` expr**. The full suite runs
  at most once more, at the very end, with a config already proven to complete.
- If a run crashes (non-zero, `reason=stall|timeout|crash-in-log`, or collected
  ≠ ran), report that verbatim — don't rerun with the same config.
- Pass this rule down to every subagent brief that includes a gate.
