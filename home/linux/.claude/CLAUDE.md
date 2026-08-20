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

## Subagent handoff goes through files

Give each spawned subagent a report path
`.scratch/<branch-shelf>/<agent>-<task>-<agent_id>.md`, where `<branch-shelf>` is
the current branch's shelf under the repo root (see the `dewey-decimal` skill);
it writes findings there, returns only the path. Read the file, not the return
message — nested subagents too; ensure the shelf exists before spawning.

## Subagents must not share mutable working files

Sole-writer rule: an agent owns its brief's files alone; children mustn't touch
them. Scratch work: a per-agent subdir, never shared. Parallel editors on one
deliverable: separate git worktrees (`isolation: "worktree"`). Split ownership by
file/module, not mission. Handoffs point to code on disk, not a restated summary.
Backstopped by `subagent-file-handoff.py` and `same-file-write-audit.py`.

## Browser automation goes through browser_batch

Never make a lone `mcp__claude-in-chrome__*` call — it nags on exactly one per
turn. Include `browser_batch` in the *first* ToolSearch select list; batch
navigate/resize/click/type/screenshot into one call, or pair an unbatchable step
with another browser call in the same message.
