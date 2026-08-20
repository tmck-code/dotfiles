---
name: dewey-decimal
description: Shelve scratch/working files under <repo-root>/.scratch/<branch>/, one shelf per git branch. Use when scratch, working or subagent-handoff files are about to be written and they would otherwise pile up flat in .scratch/, or when the user refers vaguely to a past task ("the infra task from yesterday") and its shelf has to be found again.
---

# Dewey Decimal

Every branch gets a **shelf**: `<repo-root>/.scratch/<branch>/`. No timestamp in
the name — file mtimes already say "when".

## Steps

1. **Resolve the shelf** from the current branch:

   ```
   git rev-parse --show-toplevel      # shelf root: <toplevel>/.scratch/
   git rev-parse --abbrev-ref HEAD    # branch name
   ```

   Sanitise the branch name into one flat path segment: `/` → `-`, then every
   character outside `[A-Za-z0-9._-]` → `-`, collapse runs of `-`, strip leading
   and trailing `-`. Do not lowercase — `Fix-Thing` and `fix-thing` are
   different shelves.

   - Detached HEAD (`abbrev-ref` returns `HEAD`) → shelf `detached-<short-sha>`.
   - Not inside a git repo → ask the user for a shelf name; do not invent one
     and do not fall back to writing flat.

   **Confirm with the user before shelving** if HEAD is detached, or the branch
   is `master`, `main` or `develop` — shelving onto a trunk usually means a
   branch was forgotten. Otherwise resolve silently and just mention the path.

2. **Open the shelf**: create `<toplevel>/.scratch/<shelf>/` if missing. Every
   non-committed file for this task goes here, including subagent handoffs at
   `<toplevel>/.scratch/<shelf>/<agent>-<task>-<agent_id>.md`. Prune or archive
   a shelf only when asked by name.

3. **Log the visit**: append `<ISO8601 timestamp>|<shelf>|<raw branch name>` to
   `<toplevel>/.scratch/SESSION.md` (create if missing). Append-only. Both name
   forms are recorded: the shelf name is what you match against `ls .scratch/`,
   the raw branch is what you `git switch` back to, and one is not always
   recoverable from the other.

4. **Re-resolve before every scratch write.** Branches change mid-session. If
   the resolved shelf differs from the one in use, say so — "branch changed
   `foo` → `bar`, shelving to `.scratch/bar/` now" — log the new visit, and
   continue in the new shelf. Never move or merge shelves automatically; a
   rename and a switch look identical from here.

## Finding an old shelf

For a vague reference to a past task, try these in order and stop at the first
confident match:

1. Existing shelves: `ls .scratch/` plus directory mtimes.
2. `.scratch/SESSION.md` entries — they carry timestamps and raw branch names.
3. `git branch --sort=-committerdate`, or `git reflog`, for branches that have
   no shelf yet.
4. Last commit subject as a title proxy: `git log -1 --format=%s <branch>`.
   Branch names are terse, so "the infra task" often matches only here.

If nothing matches, or the match is ambiguous, ask which task they mean.
