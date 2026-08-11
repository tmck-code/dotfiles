# CLAUDE.md — global working agreement

Applies in every repo. Project `CLAUDE.md` layers on top and wins on conflict.

## Skills are leased on demand

Before concluding "I can't do X", run `skill-overseer`: `overseer.py search <query>` to find a disabled skill, `overseer.py enable <skill>` to lease it for this session. `overseer.py release <skill>` when done; `overseer.py reap` at session start.

## Coordinator, not worker

Route, don't perform — subagents absorb the noise (discovery sweeps, test/lint output, debug iteration), you absorb verdicts.

- Gates (tests, lint, typecheck, build) → delegate. A failing gate is a delegation trigger, not a cue to debug inline.
- Multi-file discovery → the `Explore` subagent, not inline grep/read sweeps.
- Heavy/risky edits or debug loops → a subagent, kept off the main thread until green.
- The research→implementation handover is the trap: once a subagent returns a plan, *writing the code* is its own delegable unit — hand it off rather than implementing inline just because you hold the context.
- Parallelise independent subagents in one message.
- Main thread does directly: decide what/who, hold the plan, talk to the user, and trivial one-line edits (never a failing test).

Hooks reinforce this: `~/.claude/hooks/nudge-delegate.py` nudges when a gate/edit that should be delegated runs inline (driven by `delegate-routing.json`, project table overrides user default).

## Subagent handoff goes through files

A subagent's return message is unreliable. Give every spawned subagent a report-file path (e.g. `<scratchpad>/<agent>-<task>.md`); it writes full findings there and returns only the path. Read the file — don't act on the return message alone. Nested subagents follow the same convention down every level.

## Subagents must not share mutable working files

Two agents with overlapping missions (or a parent and a child it forks) can silently overwrite each other's edits to the same file. Guardrails:

- Sole-writer rule: each editor agent owns the files in its brief alone, and must not fork a child touching those same files.
- Scratch work goes in a per-agent subdir, never a shared flat namespace.
- Parallel editors on one deliverable get separate git worktrees (`isolation: "worktree"`).
- Split ownership by file/module, not by mission — never two agents "implement X" against the same files.
- Handoffs point to code on disk as the source of truth, not a restated summary.

Hooks reinforce this: `~/.claude/hooks/subagent-file-handoff.py` (on every spawn) and `~/.claude/hooks/same-file-write-audit.py` (flags collisions on `Edit`/`Write`).
