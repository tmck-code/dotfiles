# CLAUDE.md — global working agreement

This file applies in every repo. Project-level `CLAUDE.md` files layer on top of
it and win on any conflict.

## The main thread is a coordinator, not a worker

Default posture: **route, don't perform.** The things that silently fill the
context window — discovery sweeps, test/lint output, debug iteration — should run
on subagents, not the main thread. You absorb summaries and verdicts; subagents
absorb the noise.

- **Gates** (tests, lint, typecheck, build) → delegate to a subagent. A failing
  gate is a *delegation trigger*, not a cue to start debugging inline.
- **Multi-file discovery** ("how does X work across the tree") → the `Explore`
  subagent, not inline grep/read sweeps. Inline `Read` is for a single known file
  you're about to quote or edit.
- **Heavy or risky edits / debugging loops** → a subagent (a project-specific
  editor agent if one exists, else `general-purpose`). Keep the edit↔verify loop
  off the main thread until it's green.
- **After a subagent returns, the default is to delegate the NEXT unit of work
  too** — don't absorb it just because "I'm already here."
- **The research→implementation handover is the trap.** When a subagent returns
  findings/a plan and the next step is to *write the code*, that writing is its own
  delegable unit — hand it to a subagent (per-file or per-component, in parallel
  where independent). Having just absorbed the research is **not** a license to
  implement inline; "I already have the context" is the exact rationalization that
  pulls work back onto the main thread. The coordinator reviews the returned diff;
  the subagent produces it. This holds for any language (py/js/ts/go/…), not just
  scaffolding.
- **Parallelise independent work** — spawn independent subagents in one message.

## What the main thread does directly

- Decide *what* to do and *which* agent to route it to.
- Hold the plan and the running summary of verdicts.
- Talk to the user; make judgement calls.
- Trivial one-line edits where spinning up an agent costs more than it saves — but
  a *failing test* is never trivial.

A `PreToolUse` hook (`~/.claude/hooks/nudge-delegate.py`) reinforces this by
nudging when a gate/edit that should be delegated runs on the main thread. It is
driven by `delegate-routing.json` (project table overrides the user default).
