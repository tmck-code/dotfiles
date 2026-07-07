# CLAUDE.md — global working agreement

This file applies in every repo. Project-level `CLAUDE.md` files layer on top of
it and win on any conflict.

## Disabled skills are leased on demand — don't give up, search first

Many skills are disabled by default to keep context lean. Before concluding "I
can't do X" or working around a missing capability, run the **`skill-overseer`**
skill: `overseer.py search <query>` to find a disabled skill, then
`overseer.py enable <skill>` to lease + enable it for this session (if it isn't
callable yet, read its `SKILL.md` off disk and follow it). `overseer.py release
<skill>` when done. Run `overseer.py reap` at session start to reclaim skills
left enabled by sessions that have ended.

## The main thread is a coordinator, not a worker

> **If you are a subagent, this section applies to your coordinator, not you.**
> Do not expand your own brief, do not dispatch follow-on work you weren't asked
> for (research agents don't launch the implementation; finders don't launch the
> fix), and never fork a child that edits your own files. Delegating *within*
> your brief (e.g. parallel children on separate files you then integrate) is
> fine. Finish the brief, write your report file, return.

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

## Subagent results go through files, not return messages

A subagent's return message is unreliable — the parent frequently sees only part of
a long message, or none of it. So **whenever you spawn a subagent, the result is
handed back through a file, not the return text.**

- When you fork a subagent, give it a **report-file path** up front — a uniquely
  named markdown file in the scratchpad, named after the task/subagent so siblings
  never collide (e.g. `<scratchpad>/<agent>-<task>.md`). Tell it to write its full
  findings/report there **before returning**, and to return only that path.
- After it returns, **read the file** to learn what happened — don't act on the
  returned message alone.
- Pass the convention down every level: a subagent that nests its own children
  hands each of them a report-file path and reads those back the same way.

A `PreToolUse` hook (`~/.claude/hooks/subagent-file-handoff.py`, on `Agent`/`Task`)
reinforces this at every spawn and every nesting depth.

## Subagents must not share mutable working files

The report-file convention above scopes *reports* — it says nothing about the
*working* artifacts agents edit (source files, throwaway scratch scripts). That gap
is a real footgun: two agents with overlapping missions, or an agent and a child it
forks, will happily edit the **same file** with no awareness of each other. The
result is a lost-update race (parallel) or silent re-derivation/overwrite (serial) —
"multiple subagents wrote to the same file without realising." It is **invisible from
the coordinator**, because the collision is often a *nested* fork the parent never
dispatched.

So, alongside the report-file path, every editor agent gets an **ownership boundary**:

- **Sole-writer rule.** Tell each editor agent it is the *only* writer of the files in
  its brief, and **must not fork a child that edits those same files**. If it needs
  parallel help, the children write to *separate* files and the parent integrates.
- **Scope scratch per agent.** Throwaway experiments go in a per-agent subdir
  (`<scratchpad>/<agent>-<task>/…`), never a shared flat namespace — same discipline
  as report-file names, applied to working files.
- **Isolate parallel editors.** If two+ agents must touch the same logical
  deliverable, give each its own **git worktree** (`isolation: "worktree"` on the
  Agent tool, or a `Workflow` with per-item worktrees) and review/merge the diffs.
  Physical isolation beats a prose handoff that invites re-derivation.
- **Split by file, not by mission.** Don't run two agents both "implement X" against
  the same files in sequence. Either one agent owns that file end-to-end across
  iterations, or split ownership by module (agent A owns the impl, agent B owns the
  eval) so their writes never overlap.
- **Hand off the file, not a summary.** When work passes serially, the *code on disk*
  is the source of truth; the report should say "the code is the spec — here's only
  what's not obvious from it," not re-describe state the next agent will re-derive.

A `PreToolUse` hook (the same `subagent-file-handoff.py`) injects the sole-writer /
no-nested-same-file-fork reminder on every spawn; a `PostToolUse` detector
(`~/.claude/hooks/same-file-write-audit.py`, on `Edit`/`Write`) surfaces it when two
agent-attributed writes hit one path so a collision is never silent again.

## What the main thread does directly

- Decide *what* to do and *which* agent to route it to.
- Hold the plan and the running summary of verdicts.
- Talk to the user; make judgement calls.
- Trivial one-line edits where spinning up an agent costs more than it saves — but
  a *failing test* is never trivial.

A `PreToolUse` hook (`~/.claude/hooks/nudge-delegate.py`) reinforces this by
nudging when a gate/edit that should be delegated runs on the main thread. It is
driven by `delegate-routing.json` (project table overrides the user default).
