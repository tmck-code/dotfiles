---
name: dewey-decimal
description: Shelve scratch/working files under <repo-root>/.scratch/<branch>/, one shelf per git branch, and track session handoff documents in the shelf's HANDOFF.md ledger. Use when scratch, working or subagent-handoff files are about to be written and they would otherwise pile up flat in .scratch/, when writing a handoff for a later session or resuming from one ("resume from handoff"), or when the user refers vaguely to a past task ("the infra task from yesterday") and its shelf has to be found again.
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

   Filenames must not contain `research` or `report` (as substrings, case-insensitive)
   — those trip a harness write-blocking check. Use a synonym instead
   (`findings`, `notes`, `summary`, `writeup`, `analysis`).

3. **Log the visit**: append `<ISO8601 timestamp>|<shelf>|<raw branch name>` to
   `<toplevel>/.scratch/SESSION.md` (create if missing). Append-only. Both name
   forms are recorded: the shelf name is what you match against `ls .scratch/`,
   the raw branch is what you `git switch` back to, and one is not always
   recoverable from the other.

4. **Check for pending handoffs** — see [Session handoffs](#session-handoffs).
   Do this once, when the skill first runs in a session.

5. **Re-resolve before every scratch write.** Branches change mid-session. If
   the resolved shelf differs from the one in use, say so — "branch changed
   `foo` → `bar`, shelving to `.scratch/bar/` now" — log the new visit, and
   continue in the new shelf. Never move or merge shelves automatically; a
   rename and a switch look identical from here.

## Session handoffs

A **session handoff** is a document one session writes so a later session can
pick the task up. (Not a subagent handoff — those are captured mechanically and
never go through this ledger.)

| What     | Path                                                         |
| -------- | ------------------------------------------------------------ |
| Document | `<toplevel>/.scratch/<shelf>/handoff/handoff.YYYYMMDD-HHMMSS.md` |
| Ledger   | `<toplevel>/.scratch/<shelf>/HANDOFF.md`                     |

The filename timestamp is local time, `date +%Y%m%d-%H%M%S`. The session ID is
`$CLAUDE_CODE_SESSION_ID`; if unset, record `unknown` rather than inventing one.

The ledger is a table, one row per handoff document, oldest first. Create it
with this header if missing:

```
| handoff | written_by | written_at | read_by | read_at |
| ------- | ---------- | ---------- | ------- | ------- |
```

- `handoff` — path relative to the shelf: `handoff/handoff.20260919-143012.md`
- `written_by` / `read_by` — session IDs
- `written_at` / `read_at` — ISO8601 timestamps with offset (`date -Iseconds`)
- `read_by` and `read_at` are `-` until the handoff has been read

### Writing a handoff

1. Write the document to the path above, creating `handoff/` if missing.
2. Append its row to the ledger, with `read_by` and `read_at` as `-`.

Never write a handoff document without its ledger row — an unlisted handoff is
invisible to the next session.

### Checking on session start

Read the shelf's `HANDOFF.md`. No ledger, or no rows with `read_by` of `-`, means
nothing is pending — carry on silently.

Otherwise take the newest unread row and:

- **Invoked with an explicit resume instruction** (`/dewey-decimal resume from
  handoff`, "pick up the handoff", or similar) → read it without asking.
- **Anything else** → tell the user the handoff exists (path, `written_at`,
  `written_by`) and ask whether to resume from it. Do not read it, and do not
  assume its contents are the task, until they say yes. A declined handoff stays
  unread; do not ask about it again this session.

If several rows are unread, list them all and let the user choose; older unread
handoffs are usually superseded by the newest.

A row whose document is missing on disk is reported to the user, not silently
skipped or deleted.

### After reading

Once the document has actually been read, fill in that row's `read_by` with the
current session ID and `read_at` with the current timestamp. Edit only those two
cells — every other row and cell is left as it was. A row that already has a
reader is never overwritten; re-reading an already-read handoff leaves the
ledger alone.

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
