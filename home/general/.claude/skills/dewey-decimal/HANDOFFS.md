# Session handoffs

A **session handoff** is a document that one session writes so a later session can continue the task. Subagent handoffs are separate and never use this ledger.

`shelf.sh` owns the ledger (`<shelf>/HANDOFF.md`). Change it only through the script.

The `/handoff-write` command writes handoffs. This file covers resuming.

## Resuming (from `pending:` lines)

- If the user explicitly asked to resume (`/handoff-resume`, or "pick up the handoff"), read the newest pending document without asking.
- Otherwise, list every pending line (path, `written_at`, `written_by`) and ask which one to resume, if any. Older ones are usually replaced by the newest. Do not read a handoff until the user says yes. If they decline, do not ask again this session.
- Report any `MISSING` line to the user. Keep its ledger row.

## After reading

Run `shelf.sh read <handoff>`, where `<handoff>` is the path from the `pending:` line. This records the reader once. Rows that are already read are left unchanged.
