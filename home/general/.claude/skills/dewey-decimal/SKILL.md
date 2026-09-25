---
name: dewey-decimal
description: Shelve scratch files in <repo-root>/.scratch/<branch>/ and keep that shelf's session-handoff ledger. Use before writing any scratch or subagent-handoff file, or when the user refers vaguely to a past task ("the infra task from yesterday").
---

# Dewey Decimal

Each branch has one **shelf**: `<repo-root>/.scratch/<branch>/`. `shelf.sh` (in this skill folder) resolves it, creates it, and logs the visit to `.scratch/SESSION.md`.

## Steps

1. **Session start:** run `shelf.sh start`. Act on the exit code:
   - `3`: the branch is a trunk (`master`, `main`, `develop`) or HEAD is detached. Ask the user whether to shelve there. If yes, rerun with `-y start`.
   - `2`: this is not a git repo. Ask the user for a shelf name. Do not write flat into `.scratch/`.
2. **Pending handoffs:** each `pending:` line is an unread session handoff. Follow [HANDOFFS.md](HANDOFFS.md) before starting other work.
3. **Before every scratch write:** run `shelf.sh` and write under the printed `shelf:` path. A `changed:` line means the branch changed; tell the user the old and new shelf.

## Shelf rules

- Every non-committed file for the task goes on the shelf. Subagent handoffs go to `<shelf>/<agent>-<task>-<agent_id>.md`.
- Filenames must not contain `research` or `report` (any case). A harness check blocks those writes. Use `findings`, `notes`, `summary`, `writeup` or `analysis`.
- Never move, merge, prune or archive a shelf unless the user names it.

## Finding an old shelf

A vague reference to a past task: [FINDING.md](FINDING.md).
