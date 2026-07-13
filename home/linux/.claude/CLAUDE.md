# CLAUDE.md — global working agreement

Applies in every repo. Project-level `CLAUDE.md` files layer on top and win on conflict.

## Disabled skills are leased on demand — search before giving up

Many skills are disabled to keep context lean. Before concluding "I can't do X" or
working around a missing capability, run the **`skill-overseer`** skill:
`overseer.py search <query>` to find a disabled skill, `overseer.py enable <skill>`
to lease it for the session (if not yet callable, read its `SKILL.md` off disk and
follow it), `overseer.py release <skill>` when done. Run `overseer.py reap` at
session start to reclaim skills left enabled by dead sessions.

## The main thread is a coordinator, not a worker

**Route, don't perform.** The things that silently fill context — discovery sweeps,
test/lint output, debug iteration — run on subagents. You absorb summaries and
verdicts; subagents absorb the noise.

- **Gates** (tests, lint, typecheck, build) → delegate. A failing gate is a
  *delegation trigger*, not a cue to debug inline.
- **Multi-file discovery** → the `Explore` subagent. Inline `Read` is for a single
  known file you're about to quote or edit.
- **Heavy/risky edits & debugging loops** → a subagent (project editor agent if one
  exists, else `general-purpose`). Keep the edit↔verify loop off the main thread
  until green.
- **After a subagent returns, delegate the NEXT unit too** — including the
  research→implementation handover. Having just absorbed the research is *not* a
  license to write the code inline; that writing is its own delegable unit (per-file
  / per-component, parallel where independent). You review the diff; the subagent
  produces it. Any language, not just scaffolding.
- **Parallelise independent work** — spawn independent subagents in one message.

Reinforced by `~/.claude/hooks/nudge-delegate.py` (driven by `delegate-routing.json`,
project table overrides user default).

## Subagent results go through files, not return messages

A subagent's return message is unreliable — the parent often sees only part, or none.
So **the result is handed back through a file:**

- Give each forked subagent a **report-file path** up front — a uniquely named
  scratchpad markdown named after the task/subagent so siblings never collide
  (`<scratchpad>/<agent>-<task>.md`). It writes its full report there before
  returning, and returns only that path.
- **Read the file** after it returns; don't act on the return message alone.
- Pass the convention down every nesting level.

Reinforced by `~/.claude/hooks/subagent-file-handoff.py` (on `Agent`/`Task`).

## Subagents must not share mutable working files

The report-file convention scopes *reports*, not the *working* files agents edit.
Two agents with overlapping missions — or an agent and a child it forks — will
happily edit the **same file** unaware of each other, causing a lost-update race or
silent overwrite that's invisible from the coordinator. So every editor agent gets an
**ownership boundary:**

- **Sole-writer rule.** Each editor agent is the *only* writer of the files in its
  brief, and must not fork a child that edits those same files. Parallel helpers write
  to *separate* files; the parent integrates.
- **Scope scratch per agent** — per-agent subdir (`<scratchpad>/<agent>-<task>/…`),
  never a shared flat namespace.
- **Isolate parallel editors** touching one deliverable in their own **git worktree**
  (`isolation: "worktree"`, or a `Workflow` with per-item worktrees); review/merge diffs.
- **Split by file, not by mission** — one agent owns a file end-to-end, or split
  ownership by module so writes never overlap.
- **Hand off the file, not a summary** — the code on disk is the source of truth; the
  report says only what isn't obvious from it.

Reinforced by `subagent-file-handoff.py` (sole-writer reminder on spawn) and
`~/.claude/hooks/same-file-write-audit.py` (surfaces two agent writes to one path).

## What the main thread does directly

- Decide *what* to do and *which* agent to route it to.
- Hold the plan and the running summary of verdicts.
- Talk to the user; make judgement calls.
- Trivial one-line edits where spinning up an agent costs more than it saves — but a
  *failing test* is never trivial.
