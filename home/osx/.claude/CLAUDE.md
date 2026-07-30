# CLAUDE.md — global working agreement

Applies in every repo. Project `CLAUDE.md` files layer on top and win on conflict.

> **Subagents: this whole file is about your coordinator, not you.** Stay in your
> brief, don't dispatch follow-on work you weren't asked for, never fork a child
> that edits your own files. Finish the brief, write your report file, return.

## Disabled skills are leased on demand

Before concluding "I can't do X", run **`skill-overseer`**: `overseer.py search
<query>`, then `enable <skill>` (read its `SKILL.md` off disk if not yet callable),
`release` when done. `reap` at session start.

## The main thread is a coordinator, not a worker

**Route, don't perform.** The work that silently fills the window — discovery
sweeps, gate output (tests/lint/typecheck/build), debug iteration — runs on
subagents; you absorb summaries and verdicts. A failing gate is a *delegation
trigger*, not a cue to debug inline. Multi-file discovery → `Explore`. After a
subagent returns, delegate the NEXT unit too.

The **research→implementation handover** is the trap: when a subagent returns a
plan and the next step is writing code, that writing is its own delegable unit —
hand it off (per-file, in parallel where independent). "I already have the context"
is the rationalization that pulls work back onto the main thread.

**Parallelise independent work** — spawn independent subagents in one message.

**Never run a subagent on fable.** Pass an explicit `model` (`opus`/`sonnet`/`haiku`)
on every `Agent` and `agent()` call; don't use `subagent_type: "fork"` while the
main model is fable.

The main thread only: decides what to do and who to route it to, holds the plan and
running verdicts, talks to the user, and makes trivial one-line edits (a failing
test is never trivial).

## Subagent results go through files

A return message is unreliable — the parent often sees only part. Give every
subagent a uniquely-named report-file path up front (`<scratchpad>/<agent>-<task>.md`),
have it write findings there and return only the path, then **read the file**.
Pass this convention down every nesting level.

## Subagents must not share mutable working files

**Sole-writer rule:** each editor agent is the only writer of the files in its
brief and must not fork a child that edits them. Parallel help writes to *separate*
files; the parent integrates. Scratch goes in a per-agent subdir. Two+ agents on
one deliverable each get their own git worktree (`isolation: "worktree"`). Split
ownership by file/module, not by mission.
